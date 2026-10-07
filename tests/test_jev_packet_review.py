import sys
from dataclasses import replace
from types import ModuleType, SimpleNamespace

import pytest
from conftest import make_job

from clue_ai.database import save_search_run, set_jev_consent
from clue_ai.domain import SearchCriteria
from clue_ai.jev_packet_review import (
    REVIEW_RUBRIC_VERSION,
    JevPacketReviewError,
    check_tailored_resume_fit,
)
from clue_ai.repository import connect, save_jobs, save_run_results, update_run


@pytest.fixture(autouse=True)
def install_typesafe_choice_stub(monkeypatch):
    sdk = ModuleType("typesafe_sdk")

    class Choice:
        def __init__(self, *, instructions, criteria):
            self.instructions = instructions
            self.criteria = criteria

    sdk.Choice = Choice
    monkeypatch.setitem(sys.modules, "typesafe_sdk", sdk)


class FakeTypeSafeClient:
    def __init__(self, decision="approved", confidence=0.92, reason="no_material_issue"):
        self.decision = decision
        self.confidence = confidence
        self.reason = reason
        self.state = None
        self.questions = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def system_one(self, *, state, questions):
        self.state = state
        self.questions = questions
        return SimpleNamespace(
            model="jev-test",
            usage=SimpleNamespace(input_tokens=123),
            choices={
                "tailored_resume_decision": SimpleNamespace(
                    choice=self.decision,
                    confidence=self.confidence,
                ),
                "tailored_resume_reason": SimpleNamespace(
                    choice=self.reason,
                    confidence=0.9,
                ),
            },
        )


def _save_match(database):
    save_jobs(database, [make_job(url="https://jobs.example.org/tailored-fit")])
    with connect(database) as db:
        job_id = db.execute("SELECT id FROM jobs LIMIT 1").fetchone()["id"]
    save_search_run(database, "saved-match", SearchCriteria())
    update_run(database, "saved-match", status="complete", completed=True)
    save_run_results(
        database,
        "saved-match",
        [{"id": job_id, "filter_status": "match", "eligibility_status": "eligible"}],
        score_state="scored",
    )
    with connect(database) as db:
        return dict(db.execute("SELECT * FROM search_results WHERE run_id = 'saved-match'").fetchone())


def _check(
    database,
    settings,
    client,
    *,
    structure_policy="preserve",
    recruiter_requirements=None,
):
    return check_tailored_resume_fit(
        database,
        replace(settings, api_key="synthetic-typesafe-key"),
        "synthetic-request",
        job={
            "title": "Applied AI Engineer",
            "company": "Example Labs",
            "description": "Build and evaluate reliable Python services for retrieval systems.",
            "canonical_url": "https://jobs.example.org/tailored-fit",
        },
        saved_jev_match={"filter_status": "match", "combined_score": 0.91},
        source_resume="Experience\nBuilt Python services for Example Labs.",
        tailored_resume="Experience\nBuilt reliable Python retrieval services for Example Labs.",
        supported_edits=[
            {
                "line_id": "L0002",
                "original_text": "Built Python services for Example Labs.",
                "revised_text": "Built reliable Python retrieval services for Example Labs.",
                "evidence": [{"source_type": "approved_claim", "text": "Built Python services."}],
            }
        ],
        structure_policy=structure_policy,
        recruiter_requirements=recruiter_requirements,
        client_factory=lambda **_kwargs: client,
    )


def test_jev_approves_tailored_resume_without_mutating_saved_match(settings, database):
    set_jev_consent(database, True)
    before = _save_match(database)
    client = FakeTypeSafeClient()

    result = _check(database, settings, client)

    assert result["status"] == "approved"
    assert result["rubric_version"] == REVIEW_RUBRIC_VERSION
    assert result["model"] == "jev-test"
    assert result["actual_input_tokens"] == 123
    assert client.state["tailored_resume"].endswith("retrieval services for Example Labs.")
    assert client.state["source_resume"].endswith("Python services for Example Labs.")
    assert client.state["structure_policy"] == "preserve"
    assert client.state["recruiter_document_coverage"] == []
    assert "Do not estimate hiring probability" in client.questions["tailored_resume_decision"].instructions
    assert set(client.questions) == {"tailored_resume_decision", "tailored_resume_reason"}
    assert set(client.questions["tailored_resume_decision"].criteria) == {
        "approved", "revise", "unresolved"
    }
    assert result["diagnostic_reason_code"] == "no_material_issue"
    with connect(database) as db:
        usage = db.execute("SELECT status FROM jev_usage ORDER BY id DESC LIMIT 1").fetchone()
        after = dict(db.execute("SELECT * FROM search_results WHERE run_id = 'saved-match'").fetchone())
    assert usage["status"] == "completed"
    assert after == before


def test_jev_revise_decision_does_not_approve_packet_resume(settings, database):
    set_jev_consent(database, True)
    client = FakeTypeSafeClient(decision="revise")

    result = _check(database, settings, client)

    assert result["status"] == "revise"
    assert "did not approve" in result["reason"]


def test_jev_revise_response_carries_a_structured_diagnostic_reason(settings, database):
    set_jev_consent(database, True)
    client = FakeTypeSafeClient(
        decision="revise",
        reason="role_relevant_evidence_obscured",
    )

    result = _check(database, settings, client)

    assert result["status"] == "revise"
    assert result["diagnostic_reason_code"] == "role_relevant_evidence_obscured"
    assert "materially difficult to find" in result["reason"]


def test_jev_review_receives_the_selected_structure_policy_and_recruiter_map(settings, database):
    set_jev_consent(database, True)
    client = FakeTypeSafeClient()
    requirements = [{
        "requirement": "Python services",
        "document_coverage": "covered",
        "cv_line_ids": ["L0002"],
        "claim_ids": ["claim-1"],
    }]

    _check(
        database,
        settings,
        client,
        structure_policy="improve",
        recruiter_requirements=requirements,
    )

    assert client.state["structure_policy"] == "improve"
    assert client.state["recruiter_document_coverage"] == requirements


def test_low_confidence_does_not_override_jev_approval(settings, database):
    set_jev_consent(database, True)
    client = FakeTypeSafeClient(confidence=0.49)

    result = _check(database, settings, client)

    assert result["model_status"] == "approved"
    assert result["status"] == "approved"
    assert result["confidence"] == 0.49


def test_jev_resume_review_requires_consent(settings, database):
    with pytest.raises(JevPacketReviewError, match="Enable Jev consent"):
        _check(database, settings, FakeTypeSafeClient())
