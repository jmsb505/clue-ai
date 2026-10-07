from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import make_job

from clue_ai.claim_support import ClaimSupportError, check_generated_claim_support
from clue_ai.database import save_search_run, set_jev_consent
from clue_ai.domain import SearchCriteria
from clue_ai.repository import connect, save_jobs, save_run_results, update_run


class FakeTypeSafeClient:
    def __init__(self, choices=None, confidences=None):
        self.choices = choices or {}
        self.confidences = confidences or {}
        self.states = []
        self.questions = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def system_one(self, *, state, questions):
        self.states.append(state)
        self.questions.append(questions)
        return SimpleNamespace(
            model="jev-test",
            usage=SimpleNamespace(input_tokens=123),
            choices={
                name: SimpleNamespace(
                    choice=value,
                    confidence=self.confidences.get(name, 0.92),
                )
                for name, value in self.choices.items()
                if name in questions
            },
        )


def _enable_jev(database):
    set_jev_consent(database, True)


def test_support_check_labels_evidence_without_changing_matching_state(settings, database):
    _enable_jev(database)
    settings = replace(settings, api_key="synthetic-typesafe-key")
    client = FakeTypeSafeClient({"bullet-1": "supported"})
    save_jobs(database, [make_job(url="https://jobs.example.org/grounding-match")])
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
        match_before = dict(
            db.execute("SELECT * FROM search_results WHERE run_id = 'saved-match'").fetchone()
        )

    result = check_generated_claim_support(
        database,
        settings,
        "synthetic-request",
        [
            {
                "id": "bullet-1",
                "output_type": "resume_bullet_edit",
                "text": "Reduced query latency to 120 ms.",
                "evidence": [
                    {
                        "source_type": "approved_claim",
                        "source_id": "claim-1",
                        "text": "Reduced query latency to 120 milliseconds in load tests.",
                    }
                ],
            }
        ],
        client_factory=lambda **_kwargs: client,
    )

    assert result["status"] == "complete"
    assert result["model"] == "jev-test"
    assert result["results"][0]["status"] == "supported"
    assert result["actual_input_tokens"] == 123
    assert result["actual_cost_usd"] > 0
    assert client.questions[0]["bullet-1"].criteria.keys() == {
        "supported", "contradicted", "unresolved"
    }
    with connect(database) as db:
        usage = db.execute("SELECT run_id, status FROM jev_usage ORDER BY id DESC LIMIT 1").fetchone()
        match_after = dict(
            db.execute("SELECT * FROM search_results WHERE run_id = 'saved-match'").fetchone()
        )
    assert usage["run_id"] is None
    assert usage["status"] == "completed"
    assert match_after == match_before


def test_supported_answer_cannot_override_a_new_numeric_value(settings, database):
    _enable_jev(database)
    settings = replace(settings, api_key="synthetic-typesafe-key")
    client = FakeTypeSafeClient({"metric": "supported"})

    result = check_generated_claim_support(
        database,
        settings,
        "synthetic-request",
        [
            {
                "id": "metric",
                "text": "Increased annual revenue by 300%.",
                "evidence": [
                    {"source_type": "approved_claim", "text": "Built a Python service."}
                ],
            }
        ],
        client_factory=lambda **_kwargs: client,
    )

    assert result["results"][0]["model_status"] == "supported"
    assert result["results"][0]["status"] == "unresolved"
    assert result["results"][0]["unsupported_numbers"] == ["300%"]


def test_jev_limits_descriptive_profile_evidence_to_owner_preferences(settings, database):
    _enable_jev(database)
    settings = replace(settings, api_key="synthetic-typesafe-key")
    client = FakeTypeSafeClient({"preference": "supported"})

    check_generated_claim_support(
        database,
        settings,
        "synthetic-request",
        [
            {
                "id": "preference",
                "output_type": "cover_letter_paragraph",
                "text": "I prefer direct, modest writing.",
                "evidence": [
                    {
                        "source_type": "owner_stated_preference",
                        "source_id": "descriptive-profile-1",
                        "text": "Owner-stated preference; not career evidence: I prefer direct, modest writing.",
                    }
                ],
            }
        ],
        client_factory=lambda **_kwargs: client,
    )

    question = client.questions[0]["preference"]
    assert "must never be used to support career history" in question.instructions
    assert "never supports career facts, skills, qualifications" in question.criteria["supported"]


def test_low_confidence_jev_support_verdict_remains_authoritative(settings, database):
    _enable_jev(database)
    settings = replace(settings, api_key="synthetic-typesafe-key")
    client = FakeTypeSafeClient(
        {"bullet": "supported"},
        {"bullet": 0.49},
    )

    result = check_generated_claim_support(
        database,
        settings,
        "synthetic-request",
        [{"id": "bullet", "text": "Built a Python API.", "evidence": [{"text": "Built a Python API."}]}],
        client_factory=lambda **_kwargs: client,
    )

    assert result["results"][0]["model_status"] == "supported"
    assert result["results"][0]["status"] == "supported"
    assert result["results"][0]["confidence"] == 0.49


def test_missing_evidence_is_unresolved_and_is_not_sent_to_jev(settings, database):
    _enable_jev(database)
    settings = replace(settings, api_key="synthetic-typesafe-key")

    def must_not_create_client(**_kwargs):
        pytest.fail("No evidence means there must be no provider request.")

    result = check_generated_claim_support(
        database,
        settings,
        "synthetic-request",
        [{"id": "none", "text": "Led a large team.", "evidence": []}],
        client_factory=must_not_create_client,
    )

    assert result["results"][0]["status"] == "unresolved"
    assert result["results"][0]["model_status"] == "not_sent_no_evidence"
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM jev_usage").fetchone()[0] == 0


def test_missing_jev_consent_blocks_evidence_transmission(settings, database):
    settings = replace(settings, api_key="synthetic-typesafe-key")
    with pytest.raises(ClaimSupportError, match="Enable Jev consent"):
        check_generated_claim_support(
            database,
            settings,
            "synthetic-request",
            [{"id": "bullet", "text": "Built an API.", "evidence": [{"text": "Built an API."}]}],
            client_factory=lambda **_kwargs: pytest.fail("Consent must gate the request."),
        )


def test_incomplete_jev_response_is_unresolved(settings, database):
    _enable_jev(database)
    settings = replace(settings, api_key="synthetic-typesafe-key")
    client = FakeTypeSafeClient()

    result = check_generated_claim_support(
        database,
        settings,
        "synthetic-request",
        [{"id": "bullet", "text": "Built an API.", "evidence": [{"text": "Built an API."}]}],
        client_factory=lambda **_kwargs: client,
    )

    assert result["results"][0]["status"] == "unresolved"
    assert result["results"][0]["model_status"] == "invalid_or_missing"


def test_provider_timeout_keeps_the_jev_reservation_held(settings, database):
    _enable_jev(database)
    settings = replace(settings, api_key="synthetic-typesafe-key")

    class TimeoutClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def system_one(self, **_kwargs):
            raise TimeoutError("synthetic timeout")

    with pytest.raises(ClaimSupportError, match="could not complete"):
        check_generated_claim_support(
            database,
            settings,
            "synthetic-request",
            [{"id": "bullet", "text": "Built a Python API.", "evidence": [{"text": "Built a Python API."}]}],
            client_factory=lambda **_kwargs: TimeoutClient(),
        )

    with connect(database) as db:
        usage = db.execute("SELECT status, reserved_usd FROM jev_usage").fetchone()
    assert usage["status"] == "reserved"
    assert usage["reserved_usd"] > 0


def test_jev_budget_exhaustion_blocks_support_request_before_client_creation(settings, database):
    _enable_jev(database)
    settings = replace(
        settings,
        api_key="synthetic-typesafe-key",
        monthly_jev_budget_usd=0.0,
    )

    with pytest.raises(ClaimSupportError, match="stopped before the request"):
        check_generated_claim_support(
            database,
            settings,
            "synthetic-request",
            [{"id": "bullet", "text": "Built a Python API.", "evidence": [{"text": "Built a Python API."}]}],
            client_factory=lambda **_kwargs: pytest.fail("Budget exhaustion must stop before client creation."),
        )

    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM jev_usage").fetchone()[0] == 0
