from __future__ import annotations

import json
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
from clue_ai.application_prompts import CRAWL_TOOL
from clue_ai.application_workflow import (
    OpenAIProviderError,
    StalePreparationError,
    _get_bound_inputs,
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
    INPUT_TOKEN_OVERHEAD_RESERVE,
    MODEL_ID,
    REASONING_EFFORT,
    OpenAIBudgetError,
    OpenAIConfigurationError,
    reserve_usage,
    settle_usage,
)
from clue_ai.repository import save_jobs, save_run_results, update_run
from clue_ai.reset import reset_search_data
from clue_ai.scrapling_research import BoundedResearchCrawler, ResearchCrawlError
from clue_ai.web import create_app

ORIGIN = {"Origin": "http://127.0.0.1"}
JOB_URL = "https://jobs.example.org/openings/software-engineer"


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
    claim = list_claims(database_path, source_id)[0]
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


def _create_preparation(settings: Settings, database_path: Path, *, structure_policy="preserve"):
    technical = add_source(
        database_path,
        settings,
        "synthetic-technical.md",
        "technical_profile",
        b"Implemented reliable Python services and a typed local workflow.\n",
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
        b"I prefer direct, modest writing and collaborative technical teams.\n",
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

    def create(self, payload):
        self.calls.append(payload)
        assert payload["model"] == MODEL_ID
        assert payload["reasoning"]["effort"] == REASONING_EFFORT
        assert payload["store"] is False
        stage = payload["text"]["format"]["name"].removeprefix("clue_").removesuffix("_v1")
        prompt_input = payload["input"]
        if stage == "researcher" and payload.get("tools"):
            assert payload["tools"] == [CRAWL_TOOL]
            if not any(item.get("type") == "function_call_output" for item in prompt_input):
                return {
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
    source, claims, preferences, writing = _get_bound_inputs(database, settings, record)
    assert source["id"] == cv["id"]
    assert [claim["id"] for claim in claims] == [claim_id]
    assert claims[0]["source_type"] == "technical_profile"
    assert preferences == ""
    assert [item["source_type"] for item in writing] == ["descriptive_profile"]
    assert writing[0]["filename"] == "synthetic-descriptive.md"
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
    assert packet["output"]["model"] == MODEL_ID
    assert packet["output"]["reasoning_effort"] == "max"
    assert packet["output"]["research"]["contacts"][0]["public_email"] == "alex@example.org"
    assert Path(cv["file_path"]).read_text(encoding="utf-8") == original_resume
    resume_artifact = next(item for item in packet["artifacts"] if item["artifact_type"] == "resume")
    paragraphs = [paragraph.text for paragraph in Document(resume_artifact["file_path"]).paragraphs]
    assert paragraphs[:2] == ["Experience", "Built reliable Python services for Example Labs."]
    assert paragraphs.index("Education") > paragraphs.index("Experience")

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
        if call["text"]["format"]["name"] == "clue_hiring_manager_v1"
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
        max_output_tokens=100,
    )
    with connect(database) as db:
        row = db.execute("SELECT * FROM openai_usage WHERE id = ?", (usage_id,)).fetchone()
    payload_bytes = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode())
    assert row["estimated_input_bytes"] == payload_bytes
    assert row["reserved_input_tokens"] == payload_bytes + INPUT_TOKEN_OVERHEAD_RESERVE
    assert row["model"] == MODEL_ID
    settled = settle_usage(database, usage_id, input_tokens=payload_bytes + 5, output_tokens=50)
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
            max_output_tokens=100,
        )


def test_payloads_fix_model_storage_and_limit_crawler_to_researcher():
    plain = _payload("rewriter", {"test": "synthetic"})
    researcher = _payload("researcher", {"test": "synthetic"}, tools=[CRAWL_TOOL])
    assert plain["model"] == researcher["model"] == "gpt-6-luna"
    assert plain["reasoning"] == researcher["reasoning"] == {"effort": "max"}
    assert plain["store"] is researcher["store"] is False
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
