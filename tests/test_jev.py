from __future__ import annotations

from types import SimpleNamespace

from conftest import make_job

from clue_ai.database import save_search_run, set_jev_consent
from clue_ai.domain import CandidateProfile, SearchCriteria
from clue_ai.jev import _build_request_state, _parse_choice_answer, score_run
from clue_ai.repository import get_run_results, save_jobs, save_run_results


def test_choice_answers_are_bounded_and_unknown_is_not_a_zero_score():
    parsed = _parse_choice_answer(
        SimpleNamespace(
            choice="4",
            confidence=1.7,
            probabilities={"4": 2.0, "unknown": 0.0, "unexpected": 1.0},
        )
    )
    unknown = _parse_choice_answer(
        SimpleNamespace(choice="unknown", confidence=-1.0, probabilities={})
    )

    assert parsed["score"] == 1.0
    assert parsed["confidence"] == 1.0
    assert parsed["probabilities"] == {"4": 1.0}
    assert unknown["score"] is None
    assert unknown["confidence"] == 0.0


def test_jev_request_excludes_cv_file_metadata_and_redacts_contacts(settings):
    profile = CandidateProfile(
        summary="Senior engineer candidate@example.com +39 320 123 4567 https://me.example",
        target_roles="Software Engineer",
        skills="Python, SQL",
        experience="Built production APIs",
        profile_language="en",
        cv_filename="private-cv.docx",
        cv_path="/private/path/private-cv.docx",
        extracted_text="PRIVATE_RAW_CV_MUST_NOT_BE_SENT",
    )

    state, questions, _ = _build_request_state(
        [make_job().__dict__], profile, SearchCriteria(), settings
    )
    serialized = repr(state)

    assert "candidate@example.com" not in serialized
    assert "320 123 4567" not in serialized
    assert "https://me.example" not in serialized
    assert "PRIVATE_RAW_CV_MUST_NOT_BE_SENT" not in serialized
    assert "private-cv.docx" not in serialized
    assert len(questions) == 4


def test_no_key_leaves_results_unscored_and_never_calls_client(settings, database):
    save_search_run(database, "run-no-key", SearchCriteria())
    job = make_job()
    save_jobs(database, [job])
    # Rebuild the result with the canonical id returned from the local index.
    from clue_ai.repository import all_active_jobs

    save_run_results(database, "run-no-key", all_active_jobs(database))
    set_jev_consent(database, True)

    def forbidden_client(**_kwargs):
        raise AssertionError("No key must prevent an API client from being created")

    result = score_run(
        database,
        settings,
        "run-no-key",
        get_run_results(database, "run-no-key"),
        CandidateProfile(target_roles="Software Engineer", profile_language="en"),
        SearchCriteria(),
        client_factory=forbidden_client,
    )

    assert result.scored_count == 0
    assert get_run_results(database, "run-no-key")[0]["score_state"] == "unscored"
    assert "TypeSafe API key" in get_run_results(database, "run-no-key")[0]["score_reason"]


def test_synthetic_jev_call_uses_typed_questions_no_retries_and_records_fit(
    settings, database
):
    settings = settings.__class__(
        data_dir=settings.data_dir,
        api_key="synthetic-test-key",
        model=settings.model,
        monthly_jev_budget_usd=4.0,
    )
    save_search_run(database, "run-score", SearchCriteria())
    save_jobs(database, [make_job()])
    from clue_ai.repository import all_active_jobs

    save_run_results(database, "run-score", all_active_jobs(database))
    set_jev_consent(database, True)
    captured = {}

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def system_one(self, *, state, questions):
            captured["state"] = state
            captured["questions"] = questions
            return SimpleNamespace(
                model="jev-1.13.0",
                usage=SimpleNamespace(input_tokens=1_000),
                choices={
                    name: SimpleNamespace(
                        choice="3", probabilities={"3": 1.0}, confidence=0.9
                    )
                    for name in questions
                },
            )

    def client_factory(**kwargs):
        captured["client_kwargs"] = kwargs
        return FakeClient()

    profile = CandidateProfile(
        summary="Experienced engineer candidate@example.com",
        target_roles="Software Engineer",
        skills="Python, SQL",
        experience="Built production APIs",
        profile_language="en",
        extracted_text="RAW CV DATA IS NOT INCLUDED",
    )
    result = score_run(
        database,
        settings,
        "run-score",
        get_run_results(database, "run-score"),
        profile,
        SearchCriteria(),
        client_factory=client_factory,
    )

    scored = get_run_results(database, "run-score")[0]
    assert result.scored_count == 1
    assert scored["score_state"] == "scored"
    assert scored["combined_score"] == 0.75
    assert scored["rubric_version"] == "fit-v1.1.0"
    assert "candidate@example.com" not in repr(captured["state"])
    assert "RAW CV DATA IS NOT INCLUDED" not in repr(captured["state"])
    assert captured["client_kwargs"]["retry_max_retries"] == 0
    assert len(captured["questions"]) == 4
