from __future__ import annotations

import io
import json
import urllib.error
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from email import policy
from email.parser import BytesParser
from hashlib import sha256
from pathlib import Path
from typing import ClassVar

import pytest
from conftest import make_job
from docx import Document
from fastapi.testclient import TestClient

from clue_ai.application_followups import list_followups, schedule_followup
from clue_ai.application_prep import (
    add_source,
    get_preparation,
    list_claims,
    request_preparation,
    retry_preparation,
    review_claim,
    set_source_options,
    suggest_claims,
)
from clue_ai.application_prompts import (
    CRAWL_TOOL,
    OUTPUT_SCHEMA_VERSION,
    PROMPT_VERSION,
    ROLE_PROMPTS,
)
from clue_ai.application_workflow import (
    MAX_OUTPUT_TOKENS,
    OpenAIProviderError,
    StalePreparationError,
    _api_call,
    _assert_packet_quality_gates,
    _cover_letter_quality,
    _filter_diagnoser_references,
    _get_bound_inputs,
    _grounding_assertions,
    _parse_stage_result,
    _payload,
    _research_context,
    _validate_research,
    _validate_rewrite,
    create_practice_session,
    get_packet,
    queue_practice_answers,
    run_interview_practice_assessment,
    run_interview_practice_questions,
    run_preparation,
    verify_packet_approval,
)
from clue_ai.config import Settings
from clue_ai.database import (
    connect,
    delete_personal_data,
    get_settings,
    recover_interrupted_gmail_drafts,
    save_openai_controls,
    save_search_run,
    set_gmail_connection,
)
from clue_ai.domain import SearchCriteria
from clue_ai.gmail_drafts import (
    GMAIL_DRAFTS_URL,
    GmailDraftError,
    create_approved_packet_draft,
    create_unsent_draft,
)
from clue_ai.openai_provider import (
    DEFAULT_GENERATION_TIMEOUT_SECONDS,
    INPUT_TOKEN_COUNT_TIMEOUT_SECONDS,
    LONG_CONTEXT_INPUT_RATE_MULTIPLIER,
    LONG_CONTEXT_OUTPUT_RATE_MULTIPLIER,
    LONG_CONTEXT_SURCHARGE_THRESHOLD_TOKENS,
    MODEL_CONTEXT_WINDOW_TOKENS,
    MODEL_ID,
    REASONING_EFFORT,
    OpenAIBudgetError,
    OpenAIConfigurationError,
    ResponsesClient,
    ensure_context_fits,
    reserve_usage,
    settle_usage,
)
from clue_ai.repository import save_jobs, save_run_results, update_run
from clue_ai.reset import reset_search_data
from clue_ai.scrapling_research import BoundedResearchCrawler, ResearchCrawlError
from clue_ai.web import create_app

ORIGIN = {"Origin": "http://127.0.0.1"}
JOB_URL = "https://jobs.example.org/openings/software-engineer"


def _approve_synthetic_tailored_resume(*_args, **_kwargs):
    return {
        "rubric_version": "tailored-resume-fit-v2",
        "status": "approved",
        "model_status": "approved",
        "confidence": 0.92,
        "confidence_policy": "diagnostic only",
        "reason": "Synthetic Jev reviewer approved the role fit.",
        "diagnostic_reason_code": "no_material_issue",
        "diagnostic_reason": "No concrete material issue prevents owner review.",
        "model": "jev-test",
        "actual_input_tokens": 0,
        "actual_cost_usd": 0.0,
    }


@pytest.fixture(autouse=True)
def synthetic_claim_support(monkeypatch):
    """Keep workflow tests provider-free; claim_support has its own SDK contract tests."""
    def accept_synthetic_assertions(_database_path, _settings, _request_id, assertions):
        return {
            "status": "complete",
            "model": "jev-test",
            "actual_cost_usd": 0.0,
            "results": [
                {"id": item["id"], "status": "supported", "confidence": 0.9}
                for item in assertions
            ],
        }

    monkeypatch.setattr(
        "clue_ai.application_workflow.check_generated_claim_support",
        accept_synthetic_assertions,
    )


def _save_match(database_path: Path) -> str:
    save_jobs(database_path, [make_job(url=JOB_URL)])
    with connect(database_path) as db:
        job_id = db.execute("SELECT id FROM jobs LIMIT 1").fetchone()["id"]
    save_search_run(database_path, "run-workflow", SearchCriteria())
    update_run(database_path, "run-workflow", status="complete", completed=True)
    save_run_results(
        database_path,
        "run-workflow",
        [{"id": job_id, "filter_status": "match", "eligibility_status": "eligible"}],
        score_state="scored",
    )
    return job_id


def _approved_claim(database_path: Path, source_id: str) -> str:
    suggest_claims(database_path, source_id)
    # Multiple suggestions can share a creation timestamp; UUID ordering is random.
    # Pick by source text so multi-line profile fixtures stay deterministic.
    claim = min(
        list_claims(database_path, source_id),
        key=lambda item: (item["claim_text"].casefold(), item["claim_text"]),
    )
    review_claim(
        database_path,
        claim["id"],
        status="approved",
        evidence_level="implemented",
        category="systems",
        role_family="applied_ai_llm",
        owner_note="Synthetic owner-approved test evidence.",
    )
    return claim["id"]


def _create_preparation(
    settings: Settings,
    database_path: Path,
    *,
    structure_policy="preserve",
    technical_text="Implemented reliable Python services and a typed local workflow.\n",
    descriptive_text="I prefer direct, modest writing and collaborative technical teams.\n",
    descriptive_authorship="owner_written",
):
    technical = add_source(
        database_path,
        settings,
        "synthetic-technical.md",
        "technical_profile",
        technical_text.encode(),
    )
    set_source_options(
        database_path,
        technical["id"],
        permitted=True,
        default_cv=False,
        structure_policy="preserve",
    )
    claim_id = _approved_claim(database_path, technical["id"])
    resume_text = (
        "Education\nMSc Computer Science\nExperience\n"
        "- Built Python services for Example Labs.\n"
    )
    cv = add_source(
        database_path,
        settings,
        "synthetic-resume.md",
        "resume",
        resume_text.encode(),
    )
    set_source_options(
        database_path,
        cv["id"],
        permitted=True,
        default_cv=True,
        structure_policy=structure_policy,
    )
    descriptive = add_source(
        database_path,
        settings,
        "synthetic-descriptive.md",
        "descriptive_profile",
        descriptive_text.encode(),
        authorship_label=descriptive_authorship,
    )
    set_source_options(
        database_path,
        descriptive["id"],
        permitted=True,
        default_cv=False,
        structure_policy="preserve",
    )
    sample = add_source(
        database_path,
        settings,
        "synthetic-writing-sample.md",
        "writing_sample",
        b"This synthetic sample is not selected and must stay out of prompts.\n",
        authorship_label="owner_written",
    )
    job_id = _save_match(database_path)
    record, created = request_preparation(database_path, job_id, "run-workflow", cv["id"])
    assert created
    return get_preparation(database_path, record["id"]), cv, technical, descriptive, sample, claim_id, resume_text


def _enable_synthetic_openai(settings: Settings, database_path: Path) -> Settings:
    save_openai_controls(
        database_path,
        consent=True,
        monthly_cap_usd=5.0,
        opportunity_cap_usd=2.0,
        input_usd_per_million=0.1,
        output_usd_per_million=0.5,
        rate_card_revision=datetime.now(timezone.utc).date().isoformat(),
    )
    return replace(settings, openai_api_key="synthetic-openai-key")


class FakeCrawler:
    def __init__(self, _settings, allowed_urls):
        self.allowed_urls = set(allowed_urls)
        self.pages = {}

    def crawl(self, url, research_question):
        page = {
            "url": url,
            "title": "Example Labs Team",
            "text": (
                "Example Labs builds Python services for software teams. "
                "Alex Rivera, Engineering Manager at Example Labs, can be contacted at alex@example.org."
            ),
            "links": [],
            "observed_at": "2026-10-06T10:00:00+00:00",
            "research_question": research_question,
        }
        self.pages[url] = page
        return page


def _message_result(value):
    return {
        "model": MODEL_ID,
        "status": "completed",
        "output": [
            {"type": "message", "content": [{"type": "output_text", "text": json.dumps(value)}]}
        ],
        "usage": {"input_tokens": 150, "output_tokens": 80},
    }


class FakePreparationClient:
    instances: ClassVar[list[FakePreparationClient]] = []

    def __init__(self, _key):
        self.calls = []
        self.instances.append(self)

    def count_input_tokens(self, payload):
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        return max(200, len(encoded) // 4)

    def create(self, payload):
        self.calls.append(payload)
        assert payload["model"] == MODEL_ID
        assert payload["reasoning"]["effort"] == REASONING_EFFORT
        assert payload["store"] is False
        stage = payload["text"]["format"]["name"].removeprefix("clue_").removesuffix("_v2")
        prompt_input = payload["input"]
        if stage == "researcher" and payload.get("tools"):
            assert payload["tools"] == [CRAWL_TOOL]
            if not any(item.get("type") == "function_call_output" for item in prompt_input):
                return {
                    "model": MODEL_ID,
                    "status": "completed",
                    "output": [
                        {
                            "type": "function_call",
                            "name": "crawl_public_page",
                            "arguments": json.dumps(
                                {"url": JOB_URL, "research_question": "Find public team contacts"}
                            ),
                            "call_id": "synthetic-call-1",
                        }
                    ],
                    "usage": {"input_tokens": 100, "output_tokens": 30},
                }
            return _message_result(
                {
                    "company_summary": "Example Labs builds Python services.",
                    "findings": [
                        {
                            "topic": "engineering team",
                            "fact": "The team builds Python services.",
                            "source_url": JOB_URL,
                            "quote": "Example Labs builds Python services",
                            "confidence": "high",
                        }
                    ],
                    "contacts": [
                        {
                            "name": "Alex Rivera",
                            "role": "Engineering Manager",
                            "organization": "Example Labs",
                            "contact_type": "likely_team_lead",
                            "source_url": JOB_URL,
                            "quote": "Alex Rivera, Engineering Manager at Example Labs",
                            "public_email": "alex@example.org",
                            "confidence": "high",
                            "function_match": "high",
                        }
                    ],
                    "no_contact_found_reason": "",
                    "unresolved_questions": [],
                }
            )
        assert "tools" not in payload
        context = json.loads(prompt_input[0]["content"])
        if stage == "diagnoser":
            cv = context["cv"]
            return _message_result(
                {
                    "diagnostics": [
                        {
                            "source_id": cv["source_id"],
                            "line_id": cv["lines"][0]["id"],
                            "issue": "A section heading could be clearer.",
                            "severity": "low",
                            "suggested_fix": "Use a standard section name.",
                        }
                    ],
                    "overall_note": "These are visible text-parseability observations.",
                }
            )
        if stage == "recruiter":
            claim_id = context["approved_claims"][0]["id"]
            return _message_result(
                {
                    "selected_cv_id": context["permitted_cv_id"],
                    "requirements": [
                        {
                            "requirement": "Python service experience",
                            "priority": "required",
                            "document_coverage": "covered",
                            "claim_ids": [claim_id],
                            "cv_line_ids": ["L0004"],
                            "notes": "Supported by owner-approved evidence.",
                        }
                    ],
                    "coverage_note": "Document evidence only; Jev remains the match authority.",
                    "owner_questions": [],
                }
            )
        if stage == "rewriter":
            claim_id = context["approved_claims"][0]["id"]
            lines = context["cv"]["lines"]
            contact_context = context["research"]["contacts"]
            assert isinstance(contact_context, list)
            assert "public_email" not in json.dumps(contact_context)
            assert "alex@example.org" not in json.dumps(contact_context)
            assert context["owner_writing_context"][0]["source_type"] == "descriptive_profile"
            assert "synthetic-writing-sample" not in json.dumps(context)
            order = [line["id"] for line in lines]
            if context["cv"]["structure_policy"] == "allow_improvements":
                order = ["L0003", "L0004", "L0001", "L0002"]
            return _message_result(
                {
                    "selected_cv_id": context["cv"]["source_id"],
                    "resume_line_order": order,
                    "resume_bullet_edits": [
                        {
                            "line_id": "L0004",
                            "original_text": lines[3]["text"],
                            "revised_text": "Built reliable Python services for Example Labs.",
                            "claim_ids": [claim_id],
                            "edit_reason": "Clarifies the supported contribution without inventing a metric.",
                        }
                    ],
                    "cover_letter_title": "Application for Software Engineer",
                    "cover_letter_paragraphs": [
                        {
                            "text": "I am interested in the role's Python service work and can bring experience building reliable local workflows.",
                            "claim_ids": [claim_id],
                            "source_urls": [JOB_URL],
                            "preference_source_ids": [],
                        },
                        {
                            "text": "I have also built small local services with clear evidence and careful test boundaries, which fits the role's focus on dependable Python systems.",
                            "claim_ids": [claim_id],
                            "source_urls": [JOB_URL],
                            "preference_source_ids": [],
                        }
                    ],
                    "application_answers": [],
                    "outreach_drafts": ([
                        {
                            "contact_source_url": JOB_URL,
                            "recipient_name": "Alex Rivera",
                            "subject": "Question about the Software Engineer role",
                            "body": "Hello Alex, I am interested in the Python service work and would value one brief pointer to the team.",
                            "claim_ids": [claim_id],
                            "source_urls": [JOB_URL],
                        }
                    ] if contact_context else []),
                    "unresolved_questions": [],
                    "change_summary": "Reordered existing sections and clarified one supported bullet.",
                }
            )
        if stage == "hiring_manager":
            questions = context.get("questions") or [
                "How would you measure reliability in a Python service?",
                "Describe a difficult technical tradeoff you made.",
                "How would you investigate a production regression?",
            ]
            answers = context.get("answers") or []
            return _message_result(
                {
                    "questions": questions,
                    "answer_assessments": [
                        {
                            "question": answer["question"],
                            "answer": answer["answer"],
                            "technical_evidence": "The answer names a concrete implementation detail.",
                            "reasoning": "The reasoning follows a clear sequence.",
                            "clarity": "The explanation is concise.",
                            "suggested_practice": "Add the outcome and what you learned.",
                        }
                        for answer in answers
                    ],
                    "practice_note": "Practice feedback only; this is not a hiring prediction.",
                }
            )
        raise AssertionError(f"Unexpected synthetic workflow stage: {stage}")


def test_research_and_writing_only_run_after_click_and_bind_all_selected_inputs(settings, database):
    record, cv, _technical, _descriptive, sample, claim_id, _resume_text = _create_preparation(
        settings, database
    )
    source, claims, preferences, writing, technical_profiles = _get_bound_inputs(database, settings, record)
    assert source["id"] == cv["id"]
    assert [claim["id"] for claim in claims] == [claim_id]
    assert claims[0]["source_type"] == "technical_profile"
    assert preferences == ""
    assert [item["source_type"] for item in writing] == ["descriptive_profile"]
    assert writing[0]["filename"] == "synthetic-descriptive.md"
    assert len(technical_profiles) == 1
    assert technical_profiles[0]["source_id"] == _technical["id"]
    assert technical_profiles[0]["text"] == _technical["extracted_text"]
    assert sample["permitted"] == 0

    settings_without_key = settings

    def must_not_create_client(_key):
        raise AssertionError("OpenAI client must not be created while the key is blank.")

    run_preparation(database, settings_without_key, record["id"], client_factory=must_not_create_client)
    blocked = get_preparation(database, record["id"])
    assert blocked["state"] == "blocked"
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM openai_usage").fetchone()[0] == 0

    set_source_options(
        database,
        sample["id"],
        permitted=True,
        default_cv=False,
        structure_policy="preserve",
    )
    with pytest.raises(StalePreparationError, match="writing references changed"):
        _get_bound_inputs(database, settings, record)
    assert get_settings(database)["openai_consent_at"] == ""


def test_technical_profile_claim_changes_stale_the_listing_trigger(settings, database):
    record, _cv, technical, _descriptive, _sample, _claim_id, _resume = _create_preparation(
        settings,
        database,
        technical_text=(
            "Implemented a typed local workflow.\n"
            "Measured regression evaluation across three synthetic runs.\n"
        ),
    )
    pending = next(
        item for item in list_claims(database, technical["id"])
        if item["status"] == "unreviewed"
    )
    review_claim(
        database,
        pending["id"],
        status="rejected",
        evidence_level="unknown",
        category="systems",
        role_family="applied_ai_llm",
        owner_note="Synthetic test rejection.",
    )

    with pytest.raises(StalePreparationError, match="Technical profile evidence changed"):
        _get_bound_inputs(database, settings, record)


def test_owner_trigger_routes_full_descriptive_context_and_approved_claims_to_rewriter_only(settings, database):
    profile_tail = "PROFILE_TAIL_MARKER: use concise, direct language."
    descriptive_text = (
        "Descriptive profile opening.\n"
        + ("A long locally stored profile paragraph with general personal detail.\n" * 250)
        + profile_tail
    )
    claim_marker = "APPROVED_TECHNICAL_CLAIM_MARKER"
    technical_tail = "UNREVIEWED_PROFILE_MARKER: implemented a typed agent evaluation harness."
    record, _cv, _technical, _descriptive, _sample, _claim_id, _resume = _create_preparation(
        settings,
        database,
        technical_text=f"Implemented a typed local workflow. {claim_marker}\n{technical_tail}\n",
        descriptive_text=descriptive_text,
    )
    enabled = _enable_synthetic_openai(settings, database)
    FakePreparationClient.instances.clear()

    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )

    completed = get_preparation(database, record["id"])
    assert completed["state"] == "review"
    calls = FakePreparationClient.instances[-1].calls
    stage_inputs = {}
    profile_prompt_contexts = {}
    for payload in calls:
        stage = payload["text"]["format"]["name"].removeprefix("clue_").removesuffix("_v2")
        stage_inputs.setdefault(stage, []).append(json.dumps(payload["input"], ensure_ascii=False))
        if stage in {"recruiter", "rewriter"}:
            profile_prompt_contexts[stage] = json.loads(payload["input"][0]["content"])[
                "technical_profile_sources"
            ]

    assert {"researcher", "diagnoser", "recruiter", "rewriter"} <= set(stage_inputs)
    for isolated_stage in ("researcher", "diagnoser"):
        assert all(profile_tail not in value for value in stage_inputs[isolated_stage])
        assert all(claim_marker not in value for value in stage_inputs[isolated_stage])
        assert all(technical_tail not in value for value in stage_inputs[isolated_stage])
    assert all(profile_tail not in value for value in stage_inputs["recruiter"])
    assert all(claim_marker in value for value in stage_inputs["recruiter"])
    assert all(technical_tail in value for value in stage_inputs["recruiter"])
    assert all(profile_tail in value for value in stage_inputs["rewriter"])
    assert all(claim_marker in value for value in stage_inputs["rewriter"])
    assert all(technical_tail in value for value in stage_inputs["rewriter"])
    for sources in profile_prompt_contexts.values():
        evidence = [claim for source in sources for claim in source["evidence"]]
        assert evidence
        assert all(
            set(claim) == {"id", "evidence_excerpt", "review_status"}
            for claim in evidence
        )
        assert any(claim["evidence_excerpt"] == technical_tail for claim in evidence)


def test_unreviewed_profile_excerpt_can_be_used_only_with_jev_source_evidence():
    source_id = "technical-profile-1"
    evidence_id = "profile-claim-1"
    excerpt = "Built AgentDock with immutable run versions and allowlisted tool calls."
    profile_sources = [
        {
            "source_id": source_id,
            "filename": "technical-profile.md",
            "text": f"Project notes\n{excerpt}\n",
            "evidence": [
                {
                    "id": evidence_id,
                    "claim_text": excerpt,
                    "evidence_excerpt": excerpt,
                    "review_status": "unreviewed",
                }
            ],
        }
    ]
    rewrite = {
        "selected_cv_id": "cv-synthetic",
        "resume_line_order": ["L0001"],
        "resume_bullet_edits": [
            {
                "line_id": "L0001",
                "original_text": "Project experience",
                "revised_text": "Built AgentDock with immutable run versions and allowlisted tool calls.",
                "claim_ids": [evidence_id],
            }
        ],
        "cover_letter_paragraphs": [],
        "application_answers": [],
        "outreach_drafts": [],
    }
    _validate_rewrite(
        rewrite,
        "cv-synthetic",
        {"L0001": "Project experience"},
        set(),
        {"findings": [], "contacts": []},
        [],
        "preserve",
        permitted_profile_claim_ids={evidence_id},
    )
    assertions = _grounding_assertions(
        rewrite,
        [],
        {"findings": [], "contacts": []},
        technical_profile_sources=profile_sources,
    )
    assert assertions[0]["evidence"] == [
        {
            "source_type": "owner_provided_technical_profile",
            "source_id": source_id,
            "text": f"Technical profile excerpt (reference {evidence_id}; review status: unreviewed): {excerpt}",
        }
    ]

    unsupported = {
        **rewrite,
        "resume_bullet_edits": [{
            **rewrite["resume_bullet_edits"][0],
            "claim_ids": ["not-bound-to-this-profile"],
        }],
    }
    with pytest.raises(OpenAIProviderError, match="approved evidence"):
        _validate_rewrite(
            unsupported,
            "cv-synthetic",
            {"L0001": "Project experience"},
            set(),
            {"findings": [], "contacts": []},
            [],
            "preserve",
            permitted_profile_claim_ids={evidence_id},
        )


def test_long_selected_profiles_are_passed_in_full_when_the_model_context_fits(settings, database):
    technical_text = "TECHNICAL_PROFILE_START\n" + ("Project detail with implementation evidence.\n" * 1_100)
    descriptive_text = "DESCRIPTIVE_PROFILE_START\n" + ("Direct, modest writing preference.\n" * 1_000)
    record, _cv, _technical, _descriptive, *_ = _create_preparation(
        settings,
        database,
        technical_text=technical_text,
        descriptive_text=descriptive_text,
    )
    enabled = _enable_synthetic_openai(settings, database)
    FakePreparationClient.instances.clear()
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )

    completed = get_preparation(database, record["id"])
    assert completed["state"] == "review"
    calls = FakePreparationClient.instances[-1].calls
    recruiter = next(
        payload for payload in calls
        if payload["text"]["format"]["name"] == "clue_recruiter_v2"
    )
    rewriter = next(
        payload for payload in calls
        if payload["text"]["format"]["name"] == "clue_rewriter_v2"
    )
    recruiter_context = json.loads(recruiter["input"][0]["content"])
    rewriter_context = json.loads(rewriter["input"][0]["content"])
    assert recruiter_context["technical_profile_sources"][0]["text"] == technical_text
    assert rewriter_context["technical_profile_sources"][0]["text"] == technical_text
    assert rewriter_context["owner_writing_context"][0]["text"] == descriptive_text
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM openai_usage WHERE status = 'settled'").fetchone()[0] == 5


def test_fake_full_packet_review_gmail_draft_and_no_automatic_application(settings, database):
    record, cv, _technical, _descriptive, _sample, _claim_id, original_resume = _create_preparation(
        settings, database, structure_policy="allow_improvements"
    )
    enabled = _enable_synthetic_openai(settings, database)
    FakePreparationClient.instances.clear()
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )

    completed = get_preparation(database, record["id"])
    assert completed["state"] == "review"
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM application_events").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM jev_usage").fetchone()[0] == 0
        usages = db.execute("SELECT stage, status FROM openai_usage ORDER BY rowid").fetchall()
    assert len(usages) == 5  # one crawl request, one research synthesis, then three writer roles
    assert all(row["status"] == "settled" for row in usages)
    assert [row["stage"] for row in usages].count("researcher") == 2

    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]
    packet = get_packet(database, packet_id)
    assert packet["output"]["jev_tailored_resume_review"]["status"] == "approved"
    assert packet["output"]["quality_check"]["status"] == "passed"
    assert packet["output"]["quality_check"]["body_paragraph_count"] == 2
    assert packet["output"]["model"] == MODEL_ID
    assert packet["output"]["reasoning_effort"] == "high"
    assert packet["output"]["prompt_version"] == PROMPT_VERSION
    assert packet["output"]["output_schema_version"] == OUTPUT_SCHEMA_VERSION
    assert packet["output"]["research"]["contacts"][0]["public_email"] == "alex@example.org"
    assert Path(cv["file_path"]).read_text(encoding="utf-8") == original_resume
    resume_artifact = next(item for item in packet["artifacts"] if item["artifact_type"] == "resume")
    paragraphs = [paragraph.text for paragraph in Document(resume_artifact["file_path"]).paragraphs]
    assert paragraphs[:2] == ["Experience", "Built reliable Python services for Example Labs."]
    assert paragraphs.index("Education") > paragraphs.index("Experience")
    cover_letter_artifact = next(
        item for item in packet["artifacts"] if item["artifact_type"] == "cover_letter"
    )
    cover_letter_doc = Document(cover_letter_artifact["file_path"])
    cover_letter_paragraphs = [paragraph.text for paragraph in cover_letter_doc.paragraphs]
    assert cover_letter_paragraphs[0] == "Application for Software Engineer"
    assert cover_letter_doc.paragraphs[0].style.name == "Heading 1"
    assert "Python service work" in cover_letter_paragraphs[1]
    outreach_artifact = next(
        item for item in packet["artifacts"] if item["artifact_type"] == "outreach_draft"
    )
    outreach_text = Path(outreach_artifact["file_path"]).read_text(encoding="utf-8")
    assert "To: Alex Rivera" in outreach_text
    assert "Subject: Question about the Software Engineer role" in outreach_text
    assert "Source: " + JOB_URL in outreach_text
    assert all(
        Path(item["file_path"]).resolve().is_relative_to(settings.data_dir.resolve())
        for item in packet["artifacts"]
    )

    client = TestClient(create_app(enabled), base_url="http://127.0.0.1")
    missing_confirmation = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/approve",
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert "Confirm+that+you+reviewed" in missing_confirmation.headers["location"]
    assert get_packet(database, packet_id)["status"] == "review"
    approved = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/approve",
        data={"confirm_review": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert approved.status_code == 303
    assert get_packet(database, packet_id)["status"] == "approved"
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 0

    with pytest.raises(GmailDraftError, match="Confirm the exact recipient"):
        create_approved_packet_draft(
            database,
            enabled,
            record["id"],
            packet_id,
            0,
            confirmed=False,
            create_draft=lambda *_args: pytest.fail("No Gmail call without confirmation"),
        )
    calls = []
    row_id, gmail_id = create_approved_packet_draft(
        database,
        enabled,
        record["id"],
        packet_id,
        0,
        confirmed=True,
        create_draft=lambda *args: calls.append(args) or "synthetic-gmail-draft-id",
    )
    assert gmail_id == "synthetic-gmail-draft-id"
    assert calls[0][1:] == (
        "alex@example.org",
        "Question about the Software Engineer role",
        "Hello Alex, I am interested in the Python service work and would value one brief pointer to the team.",
    )
    with connect(database) as db:
        draft = db.execute("SELECT state FROM gmail_drafts WHERE id = ?", (row_id,)).fetchone()
    assert draft["state"] == "created"
    with pytest.raises(GmailDraftError, match="already created or unresolved"):
        create_approved_packet_draft(
            database,
            enabled,
            record["id"],
            packet_id,
            0,
            confirmed=True,
            create_draft=lambda *_args: pytest.fail("Duplicate Gmail call is blocked"),
        )
    with Path(resume_artifact["file_path"]).open("ab") as output:
        output.write(b"tampered")
    with pytest.raises(ValueError, match="changed after approval"):
        verify_packet_approval(database, enabled, packet_id)


def test_unsupported_or_unresolved_blocks_are_omitted_before_documents(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim_id, _resume = _create_preparation(
        settings, database
    )
    enabled = _enable_synthetic_openai(settings, database)

    def reject_generated_text(_database, _settings, _request_id, assertions):
        assert assertions
        assert all(item["evidence"] for item in assertions)
        return {
            "status": "complete",
            "model": "jev-test",
            "actual_cost_usd": 0.0,
            "results": [
                {
                    "id": item["id"],
                    "status": "contradicted" if item["output_type"] == "resume_bullet_edit" else "unresolved",
                    "confidence": 0.9,
                }
                for item in assertions
            ],
        }

    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        claim_support_checker=reject_generated_text,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )

    completed = get_preparation(database, record["id"])
    assert completed["state"] == "failed"
    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]
    packet = get_packet(database, packet_id)
    assert packet["status"] == "obsolete"
    grounding = packet["output"]["grounding"]
    assert grounding["total_assertions"] == 4
    assert grounding["supported_count"] == 0
    assert grounding["omitted_count"] == 4
    assert all(not item["included_in_artifact"] for item in grounding["results"])
    assert packet["output"]["rewriter"]["resume_bullet_edits"] == []
    assert packet["output"]["rewriter"]["cover_letter_paragraphs"] == []
    assert packet["output"]["rewriter"]["outreach_drafts"] == []

    assert packet["artifacts"] == []
    assert packet["output"]["quality_check"]["status"] == "failed"
    assert "at least two" in " ".join(packet["output"]["quality_check"]["issues"])
    assert all(item["artifact_type"] != "outreach_draft" for item in packet["artifacts"])


def test_jev_resume_rejection_persists_report_without_reviewable_artifacts(settings, database):
    record, *_ = _create_preparation(settings, database)
    enabled = _enable_synthetic_openai(settings, database)

    def reject_resume(*_args, **_kwargs):
        return {
            "rubric_version": "tailored-resume-fit-v1",
            "status": "revise",
            "model_status": "revise",
            "confidence": 0.88,
            "confidence_policy": "diagnostic only",
            "reason": "Jev did not approve the tailored resume; revise its role relevance.",
            "model": "jev-test",
            "actual_input_tokens": 0,
            "actual_cost_usd": 0.0,
        }

    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=reject_resume,
    )

    completed = get_preparation(database, record["id"])
    assert completed["state"] == "failed"
    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]
    packet = get_packet(database, packet_id)
    assert packet["status"] == "obsolete"
    assert packet["output"]["jev_tailored_resume_review"]["status"] == "revise"
    assert packet["output"]["quality_check"]["status"] == "failed"
    assert packet["artifacts"] == []


def test_packet_quality_gate_rejects_legacy_packet_without_jev_resume_approval():
    with pytest.raises(ValueError, match="Jev must explicitly approve"):
        _assert_packet_quality_gates({"output": {}, "artifacts": []})


def test_saved_job_listing_is_grounding_for_role_facts_only(settings):
    rewrite = {
        "selected_cv_id": "cv-synthetic",
        "resume_line_order": ["L0001"],
        "resume_bullet_edits": [],
        "cover_letter_paragraphs": [
            {
                "text": "The role asks for Python and PyTorch experience.",
                "claim_ids": [],
                "source_urls": [JOB_URL],
            }
        ],
        "application_answers": [],
        "outreach_drafts": [],
    }
    research = {"findings": [], "contacts": []}
    _validate_rewrite(
        rewrite,
        "cv-synthetic",
        {"L0001": "Experience"},
        set(),
        research,
        [],
        "preserve",
        job_source_url=JOB_URL,
    )
    assertions = _grounding_assertions(
        rewrite,
        [],
        research,
        job_context={
            "canonical_url": JOB_URL,
            "title": "Software Engineer",
            "company": "Example Labs",
            "description": "Build typed Python and PyTorch services; contact jobs@example.org.",
        },
    )
    assert assertions[0]["evidence"] == [
        {
            "source_type": "saved_job_listing",
            "source_id": "selected_job",
            "source_url": JOB_URL,
            "text": (
                "Saved job listing facts:\ntitle: Software Engineer\ncompany: Example Labs\n"
                "description: Build typed Python and PyTorch services; contact [redacted email]."
            ),
        }
    ]

    unsupported = {**rewrite, "cover_letter_paragraphs": [{
        "text": "The role asks for Python and PyTorch experience.",
        "claim_ids": [],
        "source_urls": ["https://unverified.example/role"],
    }]}
    with pytest.raises(OpenAIProviderError, match="unverified research source"):
        _validate_rewrite(
            unsupported,
            "cv-synthetic",
            {"L0001": "Experience"},
            set(),
            research,
            [],
            "preserve",
            job_source_url=JOB_URL,
        )


def test_rewriter_missing_role_source_is_bound_to_selected_listing():
    paragraph = {
        "text": "My supported Python service experience is relevant to the role's retrieval work.",
        "claim_ids": ["claim-1"],
        "source_urls": [],
        "preference_source_ids": [],
    }
    rewrite = {
        "selected_cv_id": "cv-synthetic",
        "resume_line_order": ["L0001"],
        "resume_bullet_edits": [],
        "cover_letter_paragraphs": [paragraph],
        "application_answers": [],
        "outreach_drafts": [],
    }

    _validate_rewrite(
        rewrite,
        "cv-synthetic",
        {"L0001": "Experience"},
        {"claim-1"},
        {"findings": [], "contacts": []},
        [],
        "preserve",
        job_source_url=JOB_URL,
    )

    assert paragraph["source_urls"] == [JOB_URL]
    assert paragraph["clue_source_url_binding"] == "selected_listing_fallback"

    second_paragraph = {
        **paragraph,
        "text": "The listing's Python and PyTorch responsibilities connect to this supported project work.",
        "source_urls": [JOB_URL],
        "clue_source_url_binding": None,
    }
    rewrite["cover_letter_paragraphs"].append(second_paragraph)
    quality = _cover_letter_quality(
        rewrite,
        {
            "results": [
                {"output_type": "cover_letter_paragraph", "status": "supported"},
                {"output_type": "cover_letter_paragraph", "status": "supported"},
            ]
        },
    )
    assert quality["status"] == "passed"


def test_descriptive_profile_supports_only_close_cover_letter_preferences():
    source_id = "descriptive-profile-1"
    profile = {
        "source_id": source_id,
        "source_type": "descriptive_profile",
        "authorship_label": "owner_written",
        "text": "I prefer direct, modest writing and collaborative technical teams.",
    }
    rewrite = {
        "selected_cv_id": "cv-synthetic",
        "resume_line_order": ["L0001"],
        "resume_bullet_edits": [
            {
                "line_id": "L0001",
                "original_text": "Experience",
                "revised_text": "Built reliable Python services.",
                "claim_ids": ["claim-1"],
            }
        ],
        "cover_letter_paragraphs": [
            {
                "text": "I prefer direct, modest writing and collaborative technical teams.",
                "claim_ids": [],
                "source_urls": [],
                "preference_source_ids": [source_id],
            },
            {
                "text": "I value careful evaluation, useful documentation, and collaborative technical work.",
                "claim_ids": [],
                "source_urls": [],
                "preference_source_ids": [source_id],
            },
        ],
        "application_answers": [],
        "outreach_drafts": [],
    }
    _validate_rewrite(
        rewrite,
        "cv-synthetic",
        {"L0001": "Experience"},
        {"claim-1"},
        {"findings": [], "contacts": []},
        [],
        "preserve",
        permitted_preference_source_ids={source_id},
    )

    assertions = _grounding_assertions(
        rewrite,
        [{"id": "claim-1", "claim_text": "Built a Python service", "evidence_excerpt": "Service implementation."}],
        {"findings": [], "contacts": []},
        descriptive_profiles=[profile],
    )

    assert [item["source_type"] for item in assertions[0]["evidence"]] == ["approved_claim"]
    assert assertions[1]["evidence"] == [
        {
            "source_type": "owner_stated_preference",
            "source_id": source_id,
            "text": "Owner-stated preference; not career evidence: " + profile["text"],
        }
    ]
    assert assertions[2]["evidence"] == []  # Loose topic overlap cannot support extra preferences.

    inferred_profile = {**profile, "authorship_label": "ai_assisted"}
    inferred_assertions = _grounding_assertions(
        rewrite,
        [{"id": "claim-1", "claim_text": "Built a Python service", "evidence_excerpt": "Service implementation."}],
        {"findings": [], "contacts": []},
        descriptive_profiles=[inferred_profile],
    )
    assert inferred_assertions[1]["evidence"] == []
    with pytest.raises(OpenAIProviderError, match="unapproved writing preference source"):
        _validate_rewrite(
            rewrite,
            "cv-synthetic",
            {"L0001": "Experience"},
            {"claim-1"},
            {"findings": [], "contacts": []},
            [],
            "preserve",
            permitted_preference_source_ids=set(),
        )

    unapproved = {**rewrite, "cover_letter_paragraphs": [{
        **rewrite["cover_letter_paragraphs"][0],
        "preference_source_ids": ["writing-sample-1"],
    }]}
    with pytest.raises(OpenAIProviderError, match="unapproved writing preference source"):
        _validate_rewrite(
            unapproved,
            "cv-synthetic",
            {"L0001": "Experience"},
            {"claim-1"},
            {"findings": [], "contacts": []},
            [],
            "preserve",
            permitted_preference_source_ids={source_id},
        )


def test_researcher_prompt_requires_useful_facts_even_without_public_contacts():
    prompt = " ".join(ROLE_PROMPTS["researcher"].split())

    assert "return concise atomic findings with an exact supporting quote" in prompt
    assert "A lack of contact details does not make useful company or role facts irrelevant" in prompt
    assert "Never guess a contact, email address, or relationship" in prompt


def test_rewriter_cover_letter_prompt_requires_supported_specific_paragraphs():
    prompt = ROLE_PROMPTS["rewriter"]
    normalized_prompt = " ".join(prompt.split())
    assert "two or three short paragraphs" in prompt
    assert "saved job listing's canonical URL" in prompt
    assert "omit that paragraph rather than adding generic filler" in prompt
    assert "Do not invent the owner's feelings" in prompt
    assert "unknown or AI-assisted authorship is only an optional style guide" in normalized_prompt
    assert "owner-authored source" in normalized_prompt
    assert 'Avoid meta lead-ins such as "Those preferences align with..."' in normalized_prompt
    assert "Connect a preference to a concrete sourced responsibility" in normalized_prompt
    assert "use distinct projects as proof points" in normalized_prompt
    assert "Name each project exactly as its source states" in normalized_prompt


def test_diagnoser_prompt_requires_verbatim_source_and_line_ids():
    prompt = " ".join(ROLE_PROMPTS["diagnoser"].split())

    assert "Copy the exact source ID and line ID" in prompt
    assert "never invent, infer, or combine IDs" in prompt


def test_recruiter_prompt_is_concise_and_stage_budget_covers_measured_incomplete_response():
    prompt = " ".join(ROLE_PROMPTS["recruiter"].split())

    assert "one short evidence note per criterion" in prompt
    assert MAX_OUTPUT_TOKENS["recruiter"] == 5_000


def test_diagnoser_filter_drops_unknown_or_mismatched_line_references():
    filtered = _filter_diagnoser_references(
        {
            "overall_note": "One visible heading issue.",
            "diagnostics": [
                {"source_id": "cv-1", "line_id": "L0001", "issue": "Heading is split."},
                {"source_id": "invented", "line_id": "L0001", "issue": "Wrong source."},
                {"source_id": "cv-1", "line_id": "L0099", "issue": "Unknown line."},
                "malformed",
            ],
        },
        source_id="cv-1",
        valid_line_ids={"L0001", "L0002"},
    )

    assert filtered["diagnostics"] == [
        {"source_id": "cv-1", "line_id": "L0001", "issue": "Heading is split."}
    ]
    assert filtered["rejected_invalid_references"] == 3


def test_hiring_manager_prompt_requires_verbatim_question_and_answer_copy():
    prompt = " ".join(ROLE_PROMPTS["hiring_manager"].split())

    assert "copy the supplied question list in its exact order" in prompt
    assert "copy each matching question and answer verbatim" in prompt
    assert "Return one assessment per supplied answer" in prompt


def test_hiring_manager_practice_is_separate_and_has_no_tools(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim_id, _text = _create_preparation(
        settings, database
    )
    enabled = _enable_synthetic_openai(settings, database)
    FakePreparationClient.instances.clear()
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    session = create_practice_session(database, record["id"])
    run_interview_practice_questions(
        database, enabled, session["id"], client_factory=FakePreparationClient
    )
    with connect(database) as db:
        question_row = db.execute(
            "SELECT * FROM practice_sessions WHERE id = ?", (session["id"],)
        ).fetchone()
    questions = json.loads(question_row["output_json"])["questions"]
    assert question_row["state"] == "questions"
    queue_practice_answers(
        database,
        session["id"],
        json.dumps(
            [{"question": question, "answer": "I would measure latency and error rates."} for question in questions]
        ),
    )
    run_interview_practice_assessment(
        database, enabled, session["id"], client_factory=FakePreparationClient
    )
    with connect(database) as db:
        assessed = db.execute(
            "SELECT * FROM practice_sessions WHERE id = ?", (session["id"],)
        ).fetchone()
    assert assessed["state"] == "complete"
    assert len(json.loads(assessed["output_json"])["answer_assessments"]) == 3
    practice_calls = [
        call
        for instance in FakePreparationClient.instances
        for call in instance.calls
        if call["text"]["format"]["name"] == "clue_hiring_manager_v2"
    ]
    assert len(practice_calls) == 2
    assert all("tools" not in call for call in practice_calls)


def test_owner_reported_outcomes_and_receipts_remain_distinct(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim_id, _text = _create_preparation(
        settings, database
    )
    enabled = _enable_synthetic_openai(settings, database)
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]

    client = TestClient(create_app(enabled), base_url="http://127.0.0.1")
    approved = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/approve",
        data={"confirm_review": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert approved.status_code == 303
    submitted = client.post(
        f"/preparations/{record['id']}/record-stage",
        data={"stage": "submitted", "owner_attestation": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert submitted.status_code == 303
    with connect(database) as db:
        owner_event = db.execute(
            "SELECT * FROM application_events WHERE event_type = 'owner_submission_attestation'"
        ).fetchone()
        assert owner_event["evidence_level"] == "owner_reported"
        assert db.execute("SELECT COUNT(*) FROM applications").fetchone()[0] == 1

    feedback = client.post(
        f"/preparations/{record['id']}/interview-feedback",
        data={
            "stage": "technical",
            "self_assessment": "I explained the retry behavior clearly.",
            "employer_feedback": "Strong debugging example.",
            "gap_tags": "system design, tradeoffs",
        },
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert feedback.status_code == 303
    receipt = client.post(
        f"/preparations/{record['id']}/receipt",
        files={"receipt_file": ("confirmation.txt", b"Synthetic receipt", "text/plain")},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert receipt.status_code == 303
    with connect(database) as db:
        receipt_event = db.execute(
            "SELECT * FROM application_events WHERE event_type = 'receipt_imported'"
        ).fetchone()
        interview = db.execute("SELECT * FROM interview_feedback").fetchone()
    assert receipt_event["evidence_level"] == "receipt_imported"
    assert interview["self_assessment"] == "I explained the retry behavior clearly."
    assert interview["employer_feedback"] == "Strong debugging example."
    outcomes = client.get("/outcomes")
    assert outcomes.status_code == 200
    assert "Owner Reported" in outcomes.text
    assert "Receipt Imported" in outcomes.text


def test_owner_followup_reminders_are_visible_and_cancel_on_reply_or_outcome(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim_id, _text = _create_preparation(
        settings, database
    )
    enabled = _enable_synthetic_openai(settings, database)
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]
    client = TestClient(create_app(enabled), base_url="http://127.0.0.1")
    approved = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/approve",
        data={"confirm_review": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert approved.status_code == 303

    current_day = datetime.now().astimezone().date()
    due_on = (current_day + timedelta(days=1)).isoformat()
    scheduled = client.post(
        f"/preparations/{record['id']}/follow-up",
        data={"kind": "outreach", "due_on": due_on, "note": "Check for a reply"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert scheduled.status_code == 303
    listing = client.get("/preparations")
    assert "Next actions" in listing.text
    assert "Check for a reply" in listing.text
    assert "This is an in-app reminder only" in listing.text
    assert list_followups(database, today=current_day + timedelta(days=1))[0]["due"]

    replied = client.post(
        f"/preparations/{record['id']}/follow-up/finish",
        data={"outcome": "reply"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert replied.status_code == 303
    with connect(database) as db:
        reminder = db.execute(
            "SELECT state, resolution FROM application_followups WHERE request_id = ?",
            (record["id"],),
        ).fetchone()
    assert reminder["state"] == "cancelled"
    assert "reply" in reminder["resolution"]

    schedule_followup(
        database, record["id"], kind="application", due_on=due_on, today=current_day
    )
    submitted = client.post(
        f"/preparations/{record['id']}/record-stage",
        data={"stage": "submitted", "owner_attestation": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert submitted.status_code == 303
    with connect(database) as db:
        assert db.execute(
            "SELECT state FROM application_followups WHERE request_id = ? AND state = 'scheduled'",
            (record["id"],),
        ).fetchone()
    response = client.post(
        f"/preparations/{record['id']}/record-stage",
        data={"stage": "screen"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert response.status_code == 303
    with connect(database) as db:
        assert db.execute(
            "SELECT state FROM application_followups WHERE request_id = ? ORDER BY updated_at DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["state"] == "cancelled"

    schedule_followup(
        database, record["id"], kind="outreach", due_on=due_on, today=current_day
    )
    with connect(database) as db:
        db.execute("UPDATE jobs SET is_active = 0 WHERE id = ?", (record["job_id"],))
    client.get("/preparations")
    with connect(database) as db:
        assert db.execute(
            "SELECT state FROM application_followups WHERE request_id = ? ORDER BY updated_at DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["state"] == "cancelled"


def test_outcomes_exclude_pending_from_resolved_denominator_and_report_packet_effort(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim_id, _text = _create_preparation(
        settings, database
    )
    enabled = _enable_synthetic_openai(settings, database)
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]
    client = TestClient(create_app(enabled), base_url="http://127.0.0.1")
    approved = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/approve",
        data={"confirm_review": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert approved.status_code == 303
    submitted = client.post(
        f"/preparations/{record['id']}/record-stage",
        data={"stage": "submitted", "owner_attestation": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert submitted.status_code == 303
    pending_summary = client.get("/outcomes")
    assert "PENDING · EXCLUDED" in pending_summary.text
    assert "No tracked application has an explicitly resolved owner-reported outcome yet." in pending_summary.text

    feedback_response = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/feedback",
        data={
            "owner_minutes": "27",
            "quality_rating": "4",
            "factual_corrections": "2",
            "owner_note": "Two dates needed owner correction.",
        },
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert feedback_response.status_code == 303
    assert "feedback+saved" in feedback_response.headers["location"]
    rejected = client.post(
        f"/preparations/{record['id']}/record-stage",
        data={"stage": "rejected", "details": "Synthetic outcome"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert rejected.status_code == 303
    outcomes = client.get("/outcomes")
    assert "Resolved application outcomes" in outcomes.text
    assert "1 of 1 resolved applications" in outcomes.text
    assert "100.0% of resolved owner-reported outcomes" in outcomes.text
    assert "27 min" in outcomes.text
    assert "4/5" in outcomes.text
    assert "2 factual corrections" in outcomes.text

def test_contact_suppression_invalidates_packet_and_survives_manual_retry(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim, _text = _create_preparation(
        settings, database
    )
    enabled = _enable_synthetic_openai(settings, database)
    FakePreparationClient.instances.clear()
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    with connect(database) as db:
        contact = db.execute(
            "SELECT id FROM researched_contacts WHERE request_id = ? LIMIT 1", (record["id"],)
        ).fetchone()
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]
    client = TestClient(create_app(enabled), base_url="http://127.0.0.1")
    response = client.post(
        f"/preparations/{record['id']}/contacts/{contact['id']}/suppress",
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert get_packet(database, packet_id)["status"] == "obsolete"
    with connect(database) as db:
        saved = db.execute(
            "SELECT suppressed FROM researched_contacts WHERE id = ?", (contact["id"],)
        ).fetchone()
        assert db.execute("SELECT COUNT(*) FROM contact_suppressions").fetchone()[0] == 1
        assert db.execute(
            "SELECT state FROM preparation_requests WHERE id = ?", (record["id"],)
        ).fetchone()["state"] == "blocked"
    assert saved["suppressed"] == 1
    with pytest.raises(ValueError, match="Approve the complete packet"):
        create_approved_packet_draft(
            database,
            enabled,
            record["id"],
            packet_id,
            0,
            confirmed=True,
            create_draft=lambda *_args: pytest.fail("Suppressed contact cannot be staged"),
        )

    retry, created = retry_preparation(database, record["id"])
    assert created is True
    run_preparation(
        database,
        enabled,
        retry["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    refreshed = get_preparation(database, retry["id"])
    assert refreshed["state"] == "review"
    with connect(database) as db:
        new_contact = db.execute(
            "SELECT suppressed FROM researched_contacts WHERE request_id = ?", (retry["id"],)
        ).fetchone()
        new_packet = db.execute(
            "SELECT output_json FROM preparation_packets WHERE request_id = ?", (retry["id"],)
        ).fetchone()
    assert new_contact["suppressed"] == 1
    output = json.loads(new_packet["output_json"])
    assert output["rewriter"]["outreach_drafts"] == []
    assert output["research"]["contacts"][0]["suppressed"] is True


def test_crawler_can_follow_exact_external_source_links_but_not_unlinked_domains(settings, monkeypatch):
    from clue_ai import scrapling_research

    fetched = []

    def fake_fetch(url, host, _settings):
        fetched.append((url, host))
        if host == "jobs.example.org":
            links = [
                {"label": "Company team", "url": "https://company.example.org/team"},
                {"label": "Unrelated", "url": "https://unrelated.example.net/profile"},
            ]
        else:
            links = [
                {"label": "More team info", "url": "https://company.example.org/about"},
                {"label": "Next host", "url": "https://third.example.net/next"},
            ]
        return {"url": url, "title": "Synthetic", "text": "Synthetic page", "links": links, "observed_at": "2026-10-06"}

    monkeypatch.setattr(scrapling_research, "_scrapling_fetch", fake_fetch)
    monkeypatch.setattr(scrapling_research, "_require_public_resolution", lambda _host: None)
    crawler = BoundedResearchCrawler(settings, [JOB_URL])
    crawler.crawl(JOB_URL, "research team")
    external = crawler.crawl("https://company.example.org/team", "find a public team lead")
    assert external["url"] == "https://company.example.org/team"
    assert crawler.crawl("https://company.example.org/about", "more team details")["url"].endswith("/about")
    with pytest.raises(ResearchCrawlError, match="not supplied or linked"):
        crawler.crawl("https://third.example.net/next", "follow a second external domain")
    with pytest.raises(ResearchCrawlError, match="not supplied or linked"):
        crawler.crawl("https://unlinked.example.net/person", "guess a contact")
    assert len(fetched) == 3


def test_crawler_rejects_private_dns_and_research_requires_source_supported_contact(settings, monkeypatch):
    from clue_ai import scrapling_research

    monkeypatch.setattr(
        scrapling_research.socket,
        "getaddrinfo",
        lambda *_args, **_kwargs: [(None, None, None, None, ("127.0.0.1", 443))],
    )
    with pytest.raises(ResearchCrawlError, match="Private and local"):
        scrapling_research._require_public_resolution("jobs.example.org")

    page = {
        "url": JOB_URL,
        "text": "Example Labs builds Python services. Alex Rivera, Engineering Manager at Example Labs, alex@example.org.",
        "observed_at": "2026-10-06T10:00:00Z",
    }
    research = {
        "findings": [],
        "contacts": [
            {
                "name": "Alex Rivera",
                "role": "Engineering Manager",
                "organization": "Example Labs",
                "contact_type": "likely_team_lead",
                "source_url": JOB_URL,
                "quote": "Alex Rivera, Engineering Manager at Example Labs",
                "public_email": "alex@example.org",
                "confidence": "high",
                "function_match": "high",
            },
            {
                "name": "Fake Contact",
                "role": "Chief Engineer",
                "organization": "Example Labs",
                "contact_type": "unknown",
                "source_url": JOB_URL,
                "quote": "Example Labs builds Python services",
                "public_email": "guessed@example.org",
                "confidence": "high",
                "function_match": "high",
            },
        ],
        "no_contact_found_reason": "",
    }
    checked = _validate_research(research, {JOB_URL: page})
    assert len(checked["contacts"]) == 1
    assert checked["contacts"][0]["name"] == "Alex Rivera"
    writer_context = _research_context(checked)
    assert "public_email" not in json.dumps(writer_context)
    assert "alex@example.org" not in json.dumps(writer_context)


def test_openai_reservation_is_separate_and_requires_fresh_consent(settings, database):
    gated = replace(settings, openai_api_key="synthetic-openai-key")
    with pytest.raises(OpenAIConfigurationError, match="disabled"):
        reserve_usage(
            database,
            gated,
            get_settings(database),
            request_id="synthetic-request",
            job_id="synthetic-job",
            stage="rewriter",
            payload={"input": "synthetic"},
            input_token_count=200,
            max_output_tokens=100,
        )
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM openai_usage").fetchone()[0] == 0

    _enable_synthetic_openai(settings, database)
    payload = {"input": "Synthetic request with bounded local context."}
    usage_id = reserve_usage(
        database,
        gated,
        get_settings(database),
        request_id="synthetic-request",
        job_id="synthetic-job",
        stage="rewriter",
        payload=payload,
        input_token_count=400,
        max_output_tokens=100,
    )
    with connect(database) as db:
        row = db.execute("SELECT * FROM openai_usage WHERE id = ?", (usage_id,)).fetchone()
    payload_bytes = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    assert row["estimated_input_bytes"] == payload_bytes
    assert row["reserved_input_tokens"] == 400
    assert row["model"] == MODEL_ID
    settled = settle_usage(database, usage_id, input_tokens=390, output_tokens=50)
    assert settled > 0

    save_openai_controls(
        database,
        consent=True,
        monthly_cap_usd=0.00001,
        opportunity_cap_usd=0.00001,
        input_usd_per_million=0.1,
        output_usd_per_million=0.5,
        rate_card_revision=datetime.now(timezone.utc).date().isoformat(),
    )
    with pytest.raises(OpenAIBudgetError, match="exceed"):
        reserve_usage(
            database,
            gated,
            get_settings(database),
            request_id="synthetic-request-2",
            job_id="synthetic-job-2",
            stage="rewriter",
            payload=payload,
            input_token_count=400,
            max_output_tokens=100,
        )


def test_openai_long_context_reservation_uses_current_model_surcharge(settings, database):
    gated = _enable_synthetic_openai(settings, database)
    token_count = LONG_CONTEXT_SURCHARGE_THRESHOLD_TOKENS + 1
    usage_id = reserve_usage(
        database,
        gated,
        get_settings(database),
        request_id="synthetic-long-context",
        job_id="synthetic-long-context-job",
        stage="rewriter",
        payload={"input": "Synthetic long-context pricing boundary."},
        input_token_count=token_count,
        max_output_tokens=100,
    )
    with connect(database) as db:
        row = db.execute("SELECT * FROM openai_usage WHERE id = ?", (usage_id,)).fetchone()
    assert row["input_usd_per_million"] == 0.1 * LONG_CONTEXT_INPUT_RATE_MULTIPLIER
    assert row["output_usd_per_million"] == 0.5 * LONG_CONTEXT_OUTPUT_RATE_MULTIPLIER
    expected = (
        token_count * row["input_usd_per_million"] / 1_000_000
        + 100 * row["output_usd_per_million"] / 1_000_000
    )
    assert row["reserved_usd"] == pytest.approx(expected)
    settled = settle_usage(database, usage_id, input_tokens=token_count, output_tokens=100)
    assert settled == pytest.approx(expected)


def test_responses_client_retains_only_safe_http_error_diagnostics():
    from email.parser import BytesParser

    client = ResponsesClient("synthetic-key")
    headers = BytesParser(policy=policy.default).parsebytes(
        b"X-Request-ID: req_synthetic123\r\n\r\n"
    )
    body = json.dumps(
        {
            "error": {
                "type": "invalid_request_error",
                "code": "unsupported_parameter",
                "message": "PRIVATE_PROMPT_SENTINEL",
            }
        }
    ).encode()

    class FailingOpener:
        def open(self, _request, timeout):
            assert timeout == DEFAULT_GENERATION_TIMEOUT_SECONDS
            raise urllib.error.HTTPError(
                "https://api.openai.com/v1/responses",
                400,
                "Bad Request",
                headers,
                io.BytesIO(body),
            )

    client._opener = FailingOpener()
    payload = {
        "model": MODEL_ID,
        "reasoning": {"effort": REASONING_EFFORT},
        "store": False,
        "input": "Synthetic diagnostic only.",
    }
    with pytest.raises(OpenAIProviderError) as captured:
        client.create(payload)

    assert captured.value.status_code == 400
    assert captured.value.error_type == "invalid_request_error"
    assert captured.value.error_code == "unsupported_parameter"
    assert captured.value.request_id == "req_synthetic123"
    assert "HTTP 400" in str(captured.value)
    assert "PRIVATE_PROMPT_SENTINEL" not in str(captured.value)


def test_responses_client_counts_the_same_model_input_and_preserves_schema_and_tools():
    client = ResponsesClient("synthetic-key")
    payload = {
        "model": MODEL_ID,
        "reasoning": {"effort": REASONING_EFFORT},
        "instructions": "Synthetic instructions",
        "input": [{"role": "user", "content": "Synthetic request"}],
        "max_output_tokens": 300,
        "store": False,
        "text": {"format": {"type": "json_schema", "name": "synthetic", "schema": {"type": "object"}}},
        "tools": [CRAWL_TOOL],
        "tool_choice": "auto",
        "parallel_tool_calls": False,
    }

    class CountingOpener:
        request = None

        def open(self, request, timeout):
            self.request = request
            assert timeout == INPUT_TOKEN_COUNT_TIMEOUT_SECONDS
            return io.BytesIO(b'{"object":"response.input_tokens","input_tokens":321}')

    opener = CountingOpener()
    client._opener = opener
    assert client.count_input_tokens(payload) == 321
    assert opener.request.full_url == "https://api.openai.com/v1/responses/input_tokens"
    body = json.loads(opener.request.data)
    assert body == {
        "model": MODEL_ID,
        "input": payload["input"],
        "instructions": payload["instructions"],
        "tools": [CRAWL_TOOL],
        "text": payload["text"],
        "reasoning": payload["reasoning"],
        "tool_choice": "auto",
        "parallel_tool_calls": False,
    }
    assert "max_output_tokens" not in body
    assert "store" not in body


@pytest.mark.parametrize(
    "count_response",
    [
        {"object": "response.input_tokens", "input_tokens": True},
        {"object": "response.input_tokens", "input_tokens": -1},
        {"object": "response.input_tokens", "input_tokens": "321"},
        {"object": "response.input_tokens"},
    ],
)
def test_responses_client_rejects_invalid_input_token_counts(count_response):
    client = ResponsesClient("synthetic-key")

    class CountingOpener:
        def open(self, _request, timeout):
            assert timeout == INPUT_TOKEN_COUNT_TIMEOUT_SECONDS
            return io.BytesIO(json.dumps(count_response).encode())

    client._opener = CountingOpener()
    payload = {
        "model": MODEL_ID,
        "reasoning": {"effort": REASONING_EFFORT},
        "store": False,
        "input": "Synthetic token-count response.",
    }
    with pytest.raises(OpenAIProviderError, match="invalid input-token count"):
        client.count_input_tokens(payload)


def test_responses_client_uses_long_generation_timeout_and_preserves_response_id_on_read_timeout():
    client = ResponsesClient("synthetic-key")
    headers = BytesParser(policy=policy.default).parsebytes(
        b"X-Request-ID: req_synthetic_timeout\r\n\r\n"
    )

    class SlowResponse:
        def __init__(self):
            self.headers = headers

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            raise TimeoutError("synthetic timeout")

    class SlowOpener:
        def open(self, _request, timeout):
            assert timeout == DEFAULT_GENERATION_TIMEOUT_SECONDS
            return SlowResponse()

    client._opener = SlowOpener()
    payload = {
        "model": MODEL_ID,
        "reasoning": {"effort": REASONING_EFFORT},
        "store": False,
        "input": "Synthetic slow response.",
    }
    with pytest.raises(OpenAIProviderError, match="usage is unresolved") as captured:
        client.create(payload)

    assert captured.value.failure_kind == "timeout"
    assert captured.value.request_id == "req_synthetic_timeout"


def test_context_budget_uses_counted_input_plus_configured_output_allowance():
    ensure_context_fits(MODEL_CONTEXT_WINDOW_TOKENS - 300, 300)
    with pytest.raises(OpenAIProviderError, match="above GPT-6 Luna's 1,050,000-token context window"):
        ensure_context_fits(MODEL_CONTEXT_WINDOW_TOKENS - 299, 300)


def test_context_overflow_stops_before_usage_reservation_or_generation(settings, database):
    enabled = _enable_synthetic_openai(settings, database)

    class OversizedRequestClient:
        def count_input_tokens(self, _payload):
            return MODEL_CONTEXT_WINDOW_TOKENS

        def create(self, _payload):
            raise AssertionError("An over-context request must not reach generation.")

    with pytest.raises(OpenAIProviderError, match="above GPT-6 Luna's 1,050,000-token context window"):
        _api_call(
            database,
            enabled,
            {"id": "synthetic-request-context", "job_id": "synthetic-job-context"},
            "rewriter",
            [{"role": "user", "content": "Synthetic context boundary."}],
            OversizedRequestClient(),
            usage_ids=[],
        )
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM openai_usage").fetchone()[0] == 0


def test_token_count_failure_stops_before_usage_reservation_or_generation(settings, database):
    enabled = _enable_synthetic_openai(settings, database)

    class CountFailureClient:
        def count_input_tokens(self, _payload):
            raise OpenAIProviderError("Synthetic token-count failure.", status_code=503)

        def create(self, _payload):
            raise AssertionError("A failed input-token count must stop generation.")

    with pytest.raises(OpenAIProviderError, match="Synthetic token-count failure"):
        _api_call(
            database,
            enabled,
            {"id": "synthetic-request-count-failure", "job_id": "synthetic-job-count-failure"},
            "rewriter",
            [{"role": "user", "content": "Synthetic count failure."}],
            CountFailureClient(),
            usage_ids=[],
        )
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM openai_usage").fetchone()[0] == 0


def test_counted_input_reservation_still_enforces_local_spend_limit(settings, database):
    enabled = _enable_synthetic_openai(settings, database)
    save_openai_controls(
        database,
        consent=True,
        monthly_cap_usd=0.00001,
        opportunity_cap_usd=0.00001,
        input_usd_per_million=0.1,
        output_usd_per_million=0.5,
        rate_card_revision=datetime.now(timezone.utc).date().isoformat(),
    )

    class OverBudgetClient:
        def count_input_tokens(self, _payload):
            return 100

        def create(self, _payload):
            raise AssertionError("An over-budget generation must not reach the provider.")

    with pytest.raises(OpenAIBudgetError, match="exceed"):
        _api_call(
            database,
            enabled,
            {"id": "synthetic-request-budget", "job_id": "synthetic-job-budget"},
            "rewriter",
            [{"role": "user", "content": "Synthetic spend test."}],
            OverBudgetClient(),
            usage_ids=[],
        )
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM openai_usage").fetchone()[0] == 0


def test_openai_http_diagnostic_reaches_workflow_and_marks_usage_unknown(settings, database):
    enabled = _enable_synthetic_openai(settings, database)

    class RejectedClient:
        def count_input_tokens(self, _payload):
            return 100

        def create(self, _payload):
            raise OpenAIProviderError(
                "OpenAI rejected the request; the provider error body was omitted.",
                status_code=503,
                error_type="server_error",
                error_code="server_error",
                request_id="req_synthetic123",
            )

    with pytest.raises(OpenAIProviderError, match="HTTP 503.*server_error"):
        _api_call(
            database,
            enabled,
            {"id": "synthetic-request-diagnostics", "job_id": "synthetic-job-diagnostics"},
            "rewriter",
            [{"role": "user", "content": "Synthetic diagnostic only."}],
            RejectedClient(),
            usage_ids=[],
        )

    with connect(database) as db:
        row = db.execute(
            "SELECT status, error_summary FROM openai_usage WHERE request_id = ?",
            ("synthetic-request-diagnostics",),
        ).fetchone()
    assert row["status"] == "unknown"
    assert "HTTP 503" in row["error_summary"]
    assert "server_error" in row["error_summary"]


def test_openai_response_model_mismatch_is_rejected_after_settling_usage(settings, database):
    enabled = _enable_synthetic_openai(settings, database)

    class MismatchedClient:
        def count_input_tokens(self, _payload):
            return 100

        def create(self, _payload):
            return {
                "model": "gpt-6-astra",
                "status": "completed",
                "output": [],
                "usage": {"input_tokens": 40, "output_tokens": 10},
            }

    with pytest.raises(OpenAIProviderError, match="did not use the configured model"):
        _api_call(
            database,
            enabled,
            {"id": "synthetic-request-model-mismatch", "job_id": "synthetic-job-model-mismatch"},
            "rewriter",
            [{"role": "user", "content": "Synthetic diagnostic only."}],
            MismatchedClient(),
            usage_ids=[],
        )

    with connect(database) as db:
        row = db.execute(
            "SELECT status, actual_usd, reserved_usd FROM openai_usage WHERE request_id = ?",
            ("synthetic-request-model-mismatch",),
        ).fetchone()
    assert row["status"] == "settled"
    assert row["actual_usd"] > 0
    assert row["reserved_usd"] > 0


@pytest.mark.parametrize(
    ("response", "message"),
    [
        (
            {
                "status": "incomplete",
                "output_text": "{}",
            },
            "did not complete",
        ),
        (
            {
                "status": "completed",
                "output": [
                    {"type": "message", "content": [{"type": "refusal", "refusal": "Synthetic"}]}
                ],
            },
            "returned a refusal",
        ),
        (
            {"status": "completed", "output_text": "not-json"},
            "invalid structured output",
        ),
        (
            {"status": "completed", "output_text": "[]"},
            "invalid output object",
        ),
    ],
)
def test_openai_stage_parser_rejects_incomplete_refusal_and_malformed_outputs(response, message):
    with pytest.raises(OpenAIProviderError, match=message):
        _parse_stage_result(response, "rewriter")


def test_openai_missing_usage_receipt_is_unknown_and_blocks_retry(settings, database):
    record = _create_preparation(settings, database)[0]
    enabled = _enable_synthetic_openai(settings, database)

    class MissingUsageClient:
        def count_input_tokens(self, _payload):
            return 100

        def create(self, _payload):
            return {"model": MODEL_ID, "status": "completed", "output": [], "usage": None}

    with pytest.raises(OpenAIProviderError, match="usage receipt; retry is blocked"):
        _api_call(
            database,
            enabled,
            {"id": record["id"], "job_id": record["job_id"]},
            "rewriter",
            [{"role": "user", "content": "Synthetic diagnostic only."}],
            MissingUsageClient(),
            usage_ids=[],
        )

    with connect(database) as db:
        row = db.execute(
            "SELECT status, reserved_usd FROM openai_usage WHERE request_id = ?",
            (record["id"],),
        ).fetchone()
    assert row["status"] == "unknown"
    assert row["reserved_usd"] > 0

    with connect(database) as db:
        db.execute(
            "UPDATE preparation_requests SET state = 'failed' WHERE id = ?",
            (record["id"],),
        )
    with pytest.raises(ValueError, match="previous API charge.*unresolved"):
        retry_preparation(database, record["id"])
    with pytest.raises(ValueError, match="previous API charge.*unresolved"):
        request_preparation(
            database,
            record["job_id"],
            record["run_id"],
            record["snapshot"]["inputs"]["selected_cv_id"],
        )


def test_openai_auth_rejection_releases_reservation_as_not_sent(settings, database):
    enabled = _enable_synthetic_openai(settings, database)

    class RejectedClient:
        def count_input_tokens(self, _payload):
            return 100

        def create(self, _payload):
            raise OpenAIProviderError(
                "OpenAI rejected the request; the provider error body was omitted.",
                status_code=401,
                error_type="invalid_request_error",
                error_code="invalid_api_key",
                request_id="req_synthetic123",
            )

    with pytest.raises(OpenAIProviderError, match="HTTP 401.*invalid_api_key"):
        _api_call(
            database,
            enabled,
            {"id": "synthetic-request-auth", "job_id": "synthetic-job-auth"},
            "rewriter",
            [{"role": "user", "content": "Synthetic diagnostic only."}],
            RejectedClient(),
            usage_ids=[],
        )

    with connect(database) as db:
        row = db.execute(
            "SELECT status, reserved_usd, actual_usd, error_summary FROM openai_usage WHERE request_id = ?",
            ("synthetic-request-auth",),
        ).fetchone()
    assert row["status"] == "released"
    assert row["reserved_usd"] == 0
    assert row["actual_usd"] == 0
    assert "invalid_api_key" in row["error_summary"]


def test_openai_local_preflight_releases_reservation_without_claiming_api_usage(settings, database):
    enabled = _enable_synthetic_openai(settings, database)

    class LocallyRejectedClient:
        def count_input_tokens(self, _payload):
            return 100

        def create(self, _payload):
            raise OpenAIConfigurationError("Synthetic local request validation failed.")

    with pytest.raises(OpenAIConfigurationError, match="local request validation"):
        _api_call(
            database,
            enabled,
            {"id": "synthetic-request-preflight", "job_id": "synthetic-job-preflight"},
            "rewriter",
            [{"role": "user", "content": "Synthetic diagnostic only."}],
            LocallyRejectedClient(),
            usage_ids=[],
        )

    with connect(database) as db:
        row = db.execute(
            "SELECT status, reserved_usd, actual_usd FROM openai_usage WHERE request_id = ?",
            ("synthetic-request-preflight",),
        ).fetchone()
    assert row["status"] == "released"
    assert row["reserved_usd"] == 0
    assert row["actual_usd"] == 0


def test_payloads_fix_model_storage_and_limit_crawler_to_researcher():
    plain = _payload("rewriter", {"test": "synthetic"})
    researcher = _payload("researcher", {"test": "synthetic"}, tools=[CRAWL_TOOL])
    assert plain["model"] == researcher["model"] == "gpt-6-luna"
    assert plain["reasoning"] == researcher["reasoning"] == {"effort": "high"}
    assert plain["store"] is researcher["store"] is False
    assert plain["text"]["format"]["name"] == "clue_rewriter_v2"
    assert researcher["text"]["format"]["name"] == "clue_researcher_v2"
    assert "tools" not in plain
    assert researcher["tools"] == [CRAWL_TOOL]
    assert researcher["parallel_tool_calls"] is False
    with pytest.raises(OpenAIProviderError, match="must preserve every original CV line"):
        _validate_rewrite(
            {
                "selected_cv_id": "cv1",
                "resume_line_order": ["L0001"],
                "resume_bullet_edits": [],
                "cover_letter_paragraphs": [],
                "application_answers": [],
                "outreach_drafts": [],
            },
            "cv1",
            {"L0001": "Experience", "L0002": "Built a Python service."},
            {"claim1"},
            {"findings": [], "contacts": []},
            [],
            "allow_improvements",
        )
    with pytest.raises(OpenAIProviderError, match="reordered a CV"):
        _validate_rewrite(
            {
                "selected_cv_id": "cv1",
                "resume_line_order": ["L0002", "L0001"],
                "resume_bullet_edits": [],
                "cover_letter_paragraphs": [],
                "application_answers": [],
                "outreach_drafts": [],
            },
            "cv1",
            {"L0001": "Experience", "L0002": "Built a Python service."},
            {"claim1"},
            {"findings": [], "contacts": []},
            [],
            "preserve",
        )


def test_gmail_adapter_builds_only_a_create_draft_request(settings, monkeypatch):
    from clue_ai import gmail_drafts

    class TokenStore:
        def __init__(self, _data_dir):
            pass

        def load(self):
            return "synthetic-refresh-token"

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _limit):
            return json.dumps({"id": "synthetic-draft-id"}).encode()

    class FakeOpener:
        def open(self, request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return FakeResponse()

    captured = {}
    monkeypatch.setattr(gmail_drafts, "WindowsDPAPITokenStore", TokenStore)
    monkeypatch.setattr(gmail_drafts, "_refresh_access_token", lambda *_args: "synthetic-access-token")
    monkeypatch.setattr(gmail_drafts.urllib.request, "build_opener", lambda *_args: FakeOpener())
    configured = replace(settings, gmail_oauth_client_id="synthetic-google-client")
    result = create_unsent_draft(
        configured,
        "alex@example.org",
        "Question about the role",
        "Hello Alex, thank you for sharing the opening.",
    )
    assert result == "synthetic-draft-id"
    request = captured["request"]
    assert request.full_url == GMAIL_DRAFTS_URL
    assert request.get_method() == "POST"
    body = json.loads(request.data)
    mime_bytes = __import__("base64").urlsafe_b64decode(body["message"]["raw"] + "==")
    mime = BytesParser(policy=policy.default).parsebytes(mime_bytes)
    assert mime["To"] == "alex@example.org"
    assert mime["Subject"] == "Question about the role"
    assert "thank you for sharing" in mime.get_body(preferencelist=("plain",)).get_content()
    with pytest.raises(GmailDraftError, match="public recipient"):
        create_unsent_draft(configured, "person@@example.org", "Role", "Hello")


def test_gmail_disconnect_removes_local_token_and_stale_create_is_reconciled(settings, database):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    token_path = settings.data_dir / "gmail" / "refresh-token.bin"
    token_path.parent.mkdir(parents=True)
    token_path.write_bytes(b"synthetic-encrypted-token")
    set_gmail_connection(database, True)
    response = client.post("/settings/gmail/disconnect", headers=ORIGIN, follow_redirects=False)
    assert response.status_code == 303
    assert not token_path.exists()
    assert get_settings(database)["gmail_oauth_connected_at"] == ""

    record, _cv, _technical, _descriptive, _sample, _claim, _text = _create_preparation(
        settings, database
    )
    with connect(database) as db:
        db.execute(
            """INSERT INTO preparation_packets
               (id, request_id, revision, input_revision_sha256, output_json, status, created_at)
               VALUES ('packet-recovery', ?, 1, 'synthetic', '{}', 'review', '2026-10-06')""",
            (record["id"],),
        )
        db.execute(
            """INSERT INTO gmail_drafts
               (id, request_id, packet_id, recipient, subject, body, approved_sha256,
                state, created_at, updated_at)
               VALUES ('draft-recovery', ?, 'packet-recovery', 'alex@example.org', 'Role',
                       'Synthetic message', 'synthetic-hash', 'creating', '2026-10-06', '2026-10-06')""",
            (record["id"],),
        )
    assert recover_interrupted_gmail_drafts(database) == 1
    with connect(database) as db:
        draft = db.execute("SELECT state, error_summary FROM gmail_drafts WHERE id = 'draft-recovery'").fetchone()
    assert draft["state"] == "unknown"
    assert "Check Gmail Drafts before retrying" in draft["error_summary"]


def test_search_reset_retains_application_packets_and_provider_spend(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim, _text = _create_preparation(
        settings, database
    )
    _enable_synthetic_openai(settings, database)
    reserve_usage(
        database,
        replace(settings, openai_api_key="synthetic-openai-key"),
        get_settings(database),
        request_id=record["id"],
        job_id=record["job_id"],
        stage="researcher",
        payload={"input": "synthetic"},
        input_token_count=20,
        max_output_tokens=10,
    )
    result = reset_search_data(database)
    assert result.backup_path.is_file()
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM search_runs").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM preparation_requests").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM openai_usage").fetchone()[0] == 1
    assert Path(record["snapshot"]["inputs"]["selected_cv_filename"])


def test_full_personal_data_deletion_removes_preparation_and_provider_records(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim, _text = _create_preparation(
        settings, database
    )
    _enable_synthetic_openai(settings, database)
    set_gmail_connection(database, True)
    with connect(database) as db:
        db.execute(
            """INSERT INTO preparation_packets
               (id, request_id, revision, input_revision_sha256, output_json, status, created_at)
               VALUES ('synthetic-packet', ?, 1, 'synthetic-revision', '{}', 'approved', '2026-10-06T00:00:00Z')""",
            (record["id"],),
        )
        db.execute(
            """INSERT INTO application_followups
               (id, request_id, kind, due_on, state, created_at, updated_at)
               VALUES ('synthetic-followup', ?, 'outreach', '2026-10-07', 'scheduled',
                       '2026-10-06T00:00:00Z', '2026-10-06T00:00:00Z')""",
            (record["id"],),
        )
        db.execute(
            """INSERT INTO packet_feedback
               (id, packet_id, owner_minutes, quality_rating, factual_corrections, created_at, updated_at)
               VALUES ('synthetic-feedback', 'synthetic-packet', 10, 4, 0,
                       '2026-10-06T00:00:00Z', '2026-10-06T00:00:00Z')"""
        )
    for dirname in ("cv", "application-packets", "gmail"):
        path = settings.data_dir / dirname / "synthetic"
        path.mkdir(parents=True, exist_ok=True)
        (path / "synthetic.txt").write_text("synthetic private data", encoding="utf-8")
    delete_personal_data(database, None, settings.data_dir)
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM preparation_sources").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM candidate_claims").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM preparation_requests").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM preparation_packets").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM application_followups").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM packet_feedback").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM gmail_drafts").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM openai_usage").fetchone()[0] == 0
        setting = db.execute(
            "SELECT openai_consent_at, gmail_consent_at, gmail_oauth_connected_at FROM app_settings WHERE id = 1"
        ).fetchone()
    assert setting["openai_consent_at"] == ""
    assert setting["gmail_consent_at"] == ""
    assert setting["gmail_oauth_connected_at"] == ""
    assert not (settings.data_dir / "cv").exists()
    assert not (settings.data_dir / "application-packets").exists()
    assert not (settings.data_dir / "gmail").exists()
    assert record["id"]


def test_repository_template_keeps_openai_key_blank():
    template = Path(".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=" in template
    assert not any(line.strip().startswith("OPENAI_API_KEY=") and line.partition("=")[2].strip() for line in template.splitlines())


def test_application_workspace_groups_packet_versions_and_submission_receipts(settings, database):
    record, _cv, _technical, _descriptive, _sample, _claim_id, _resume = _create_preparation(settings, database)
    enabled = _enable_synthetic_openai(settings, database)
    run_preparation(
        database,
        enabled,
        record["id"],
        client_factory=FakePreparationClient,
        crawler_factory=FakeCrawler,
        tailored_resume_reviewer=_approve_synthetic_tailored_resume,
    )
    with connect(database) as db:
        packet_id = db.execute(
            "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
            (record["id"],),
        ).fetchone()["id"]

    client = TestClient(create_app(enabled), base_url="http://127.0.0.1")
    approved = client.post(
        f"/preparations/{record['id']}/packets/{packet_id}/approve",
        data={"confirm_review": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert approved.status_code == 303
    submitted = client.post(
        f"/preparations/{record['id']}/record-stage",
        data={"stage": "submitted", "owner_attestation": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert submitted.status_code == 303
    uploaded = client.post(
        f"/preparations/{record['id']}/receipt",
        files={"receipt_file": ("confirmation.txt", b"Synthetic receipt", "text/plain")},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert uploaded.status_code == 303

    older_bytes = b"Older synthetic application file"
    older_path = settings.data_dir / "application-packets" / record["id"] / "v0" / "older-resume.txt"
    older_path.parent.mkdir(parents=True, exist_ok=True)
    older_path.write_bytes(older_bytes)
    with connect(database) as db:
        db.execute(
            """INSERT INTO preparation_packets
               (id, request_id, revision, input_revision_sha256, output_json, status, created_at)
               VALUES ('historical-packet', ?, 0, 'older-input-revision', ?, 'obsolete', '2026-10-05T00:00:00Z')""",
            (record["id"], json.dumps({"research": {}, "diagnoser": {}, "recruiter": {}, "rewriter": {}})),
        )
        db.execute(
            """INSERT INTO packet_artifacts
               (id, packet_id, artifact_type, filename, file_path, content_sha256, created_at)
               VALUES ('historical-artifact', 'historical-packet', 'resume', 'older-resume.txt', ?, ?, '2026-10-05T00:00:00Z')""",
            (str(older_path), sha256(older_bytes).hexdigest()),
        )

    index = client.get("/applications")
    assert index.status_code == 200
    assert "Applications" in index.text
    assert f"/applications/{record['id']}" in index.text
    assert "Application stage · Submitted" in index.text

    detail = client.get(f"/applications/{record['id']}")
    assert detail.status_code == 200
    assert "Files for this application" in detail.text
    assert "Current packet · version 1 · Approved" in detail.text
    assert "Older packet · version 0 · Obsolete · 1 file" in detail.text
    assert "confirmation.txt" in detail.text
    assert "alex@example.org" in detail.text
    assert "/outcomes/receipts/" in detail.text
    historical_download = client.get("/packets/historical-packet/artifacts/historical-artifact")
    assert historical_download.status_code == 200
    assert historical_download.content == older_bytes
    assert client.get(f"/preparations/{record['id']}").status_code == 200
    assert client.get("/applications/not-a-request").status_code == 404
