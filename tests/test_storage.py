from __future__ import annotations

from shutil import copytree

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
    list_companies,
    list_sources,
    monthly_jev_usage,
    prune_expired_data,
    record_source_state,
    reserve_jev_budget,
    save_jobs,
    save_jobs_with_report,
    save_run_results,
    saved_jobs,
    set_company_tracked,
    set_job_user_state,
    settle_jev_usage,
    sources_due,
)


def test_default_source_registry_has_five_feeds_and_manual_x_marker(database):
    sources = list_sources(database)
    connectors = [item for item in sources if item["kind"] != "manual_x"]
    manual_x = next(item for item in sources if item["kind"] == "manual_x")

    assert {item["kind"] for item in connectors} == {
        "jobicy_api",
        "remotejobs_api",
        "remoteok_json",
        "remote_first_rss",
        "startup_rss",
    }
    assert all(item["state"] == "approved" and item["enabled"] for item in connectors)
    assert all(
        item["attribution"] and item["endpoint"].startswith("https://") for item in connectors
    )
    assert manual_x["state"] == "approved"
    assert manual_x["enabled"] == 0
    assert "never" in manual_x["policy_note"].casefold()
    remotejobs = next(item for item in sources if item["id"] == "remotejobs")
    assert remotejobs["attribution"] == "Powered by RemoteJobs.org"
    assert remotejobs["interval_seconds"] == 86_400
    assert remotejobs["retention_days"] == 14


def test_delete_personal_data_resets_company_tracking(settings, database):
    from clue_ai.database import delete_personal_data

    assert set_company_tracked(database, "aindo", True)

    delete_personal_data(database, None, settings.data_dir)

    aindo = next(company for company in list_companies(database) if company["id"] == "aindo")
    assert aindo["tracked"] == 0
    assert aindo["board_state"] == "candidate"


def test_distinct_manual_x_urls_are_not_fuzzy_merged_by_role_and_company(database):
    first = make_job(
        source_id="x_manual",
        url="https://careers.example.com/jobs/first",
        title="Product Designer",
        company="Example Studio",
        location="Remote in Italy",
    )
    second = make_job(
        source_id="x_manual",
        url="https://jobs.example.org/openings/second",
        title="Product Designer",
        company="Example Studio",
        location="Remote in Italy",
    )
    first.external_id = "x-post-1"
    second.external_id = "x-post-2"
    first.posted_at = ""
    second.posted_at = ""

    assert save_jobs(database, [first, second]) == 2
    assert len(all_active_jobs(database)) == 2


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


def test_remotejobs_source_is_considered_for_new_daily_role_queries(database):
    record_source_state(database, "remotejobs", "ok")

    due_source_ids = {source["id"] for source in sources_due(database)}

    assert "remotejobs" in due_source_ids


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
    assert result["sources"][0]["state"] == "approved"
    assert result["sources"][0]["last_state"] == "never"
    assert result["sources"][0]["last_seen_at"]


def test_job_index_reports_duplicate_records_and_keeps_one_canonical_job(database):
    job = make_job()

    report = save_jobs_with_report(database, [job, job])

    assert report.saved == 2
    assert report.deduplicated == 1
    assert len(all_active_jobs(database)) == 1


def test_expired_posting_is_removed_from_active_results(database):
    job = make_job()
    job.valid_through = "2020-01-01T00:00:00+00:00"
    save_jobs(database, [job])

    prune_expired_data(database)

    assert all_active_jobs(database) == []


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
    usage_id, _ = reserve_jev_budget(database, "run-delete", "jev-1.13.0", 80_000, 0.042, 4.0)
    assert usage_id is not None
    set_jev_consent(database, True)

    delete_personal_data(database, cv_path, settings.data_dir)

    assert not cv_path.exists()
    assert get_profile(database) == CandidateProfile()
    assert get_run(database, "run-delete") is None
    assert all_active_jobs(database) == []
    assert len(list_sources(database)) == 6
    assert get_source(database, "x_manual")["enabled"] == 0
    assert monthly_jev_usage(database, 4.0)["requests"] == 0
    assert get_source(database, "jobicy")["state"] == "approved"
    from clue_ai.database import get_settings

    assert get_settings(database)["jev_consent_at"] == ""


def test_stopped_app_data_copy_can_restore_synthetic_profile_and_cv(settings, database):
    profile = CandidateProfile(
        summary="Synthetic profile for a local backup check",
        target_roles="Data Analyst",
        profile_language="en",
        cv_filename="synthetic.docx",
    )
    save_profile(database, profile)
    saved_profile = get_profile(database)
    cv_path = settings.cv_dir / "synthetic.docx"
    cv_path.parent.mkdir(parents=True, exist_ok=True)
    cv_path.write_bytes(b"synthetic CV bytes")

    backup_dir = settings.data_dir.parent / "offline-backup"
    restored_dir = settings.data_dir.parent / "restored-data"
    copytree(settings.data_dir, backup_dir)
    copytree(backup_dir, restored_dir)

    assert get_profile(restored_dir / "clue.sqlite3") == saved_profile
    assert (restored_dir / "cv" / "synthetic.docx").read_bytes() == b"synthetic CV bytes"
    assert not (backup_dir / ".env").exists()
