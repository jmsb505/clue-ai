from __future__ import annotations

from conftest import make_job

from clue_ai.database import (
    delete_personal_data,
    get_profile,
    save_profile,
    save_search_run,
    set_jev_consent,
)
from clue_ai.domain import CandidateProfile, SearchCriteria
from clue_ai.repository import (
    add_source,
    all_active_jobs,
    get_run,
    get_run_results,
    get_source,
    list_sources,
    monthly_jev_usage,
    reserve_jev_budget,
    save_jobs,
    save_run_results,
    saved_jobs,
    set_job_user_state,
    settle_jev_usage,
)


def test_default_source_registry_has_only_the_four_approved_free_feeds(database):
    sources = list_sources(database)

    assert {item["kind"] for item in sources} == {
        "jobicy_api",
        "remoteok_json",
        "remote_first_rss",
        "startup_rss",
    }
    assert all(item["state"] == "approved" and item["enabled"] for item in sources)
    assert all(item["attribution"] and item["endpoint"].startswith("https://") for item in sources)


def test_owner_added_source_starts_disabled_in_review(database):
    source_id = add_source(
        database,
        name="Example employer",
        kind="scrapling",
        endpoint="https://jobs.example.org/careers",
        config={"career_url": "https://jobs.example.org/careers"},
        attribution="Example employer",
    )

    source = get_source(database, source_id)
    assert source["state"] == "review"
    assert source["enabled"] == 0
    assert source["config"]["career_url"].startswith("https://")


def test_search_result_keeps_per_run_location_and_freshness_evidence(database):
    save_search_run(database, "run-1", SearchCriteria())
    job = make_job()
    assert save_jobs(database, [job]) == 1
    active = all_active_jobs(database)
    active[0].update(
        eligibility_status="eligible",
        eligibility_evidence="Open to candidates in Italy",
        freshness_status="recent",
        freshness_age_days=0,
    )
    save_run_results(database, "run-1", active)

    result = get_run_results(database, "run-1")[0]
    assert result["eligibility_status"] == "eligible"
    assert result["eligibility_evidence"] == "Open to candidates in Italy"
    assert result["freshness_status"] == "recent"
    assert result["freshness_age_days"] == 0
    assert result["score_state"] == "unscored"


def test_saved_state_is_local_and_listed(database):
    assert save_jobs(database, [make_job()]) == 1
    job_id = all_active_jobs(database)[0]["id"]

    set_job_user_state(database, job_id, "saved")

    assert [item["id"] for item in saved_jobs(database)] == [job_id]


def test_jev_budget_reservation_settlement_and_hard_stop(database):
    save_search_run(database, "run-1", SearchCriteria())
    reserved, remaining = reserve_jev_budget(
        database, "run-1", "jev-1.13.0", 80_000, 0.042, 0.00336
    )
    assert reserved is not None
    assert remaining == 0
    blocked, remaining_after = reserve_jev_budget(
        database, "run-1", "jev-1.13.0", 80_000, 0.042, 0.00336
    )
    assert blocked is None
    assert remaining_after == 0

    settle_jev_usage(database, reserved, 1_000, 0.042)
    usage = monthly_jev_usage(database, 0.00336)
    assert usage["requests"] == 1
    assert usage["used_usd"] == 0.000042


def test_delete_personal_data_removes_cv_history_and_user_sources_but_keeps_seed_sources(
    settings, database
):
    save_profile(
        database,
        CandidateProfile(
            target_roles="Software Engineer",
            skills="Python",
            extracted_text="Synthetic CV content",
            cv_filename="synthetic.docx",
        ),
    )
    cv_path = settings.cv_dir / "synthetic.docx"
    cv_path.parent.mkdir(parents=True, exist_ok=True)
    cv_path.write_bytes(b"synthetic")
    add_source(
        database,
        name="Example source",
        kind="greenhouse",
        endpoint="https://boards-api.greenhouse.io/v1/boards/example/jobs",
        config={"board_token": "example"},
        attribution="Example source",
    )
    save_search_run(database, "run-delete", SearchCriteria())
    assert save_jobs(database, [make_job()]) == 1
    usage_id, _ = reserve_jev_budget(
        database, "run-delete", "jev-1.13.0", 80_000, 0.042, 4.0
    )
    assert usage_id is not None
    set_jev_consent(database, True)

    delete_personal_data(database, cv_path, settings.data_dir)

    assert not cv_path.exists()
    assert get_profile(database) == CandidateProfile()
    assert get_run(database, "run-delete") is None
    assert all_active_jobs(database) == []
    assert len(list_sources(database)) == 4
    assert monthly_jev_usage(database, 4.0)["requests"] == 0
    assert get_source(database, "jobicy")["state"] == "approved"
    from clue_ai.database import get_settings

    assert get_settings(database)["jev_consent_at"] == ""
