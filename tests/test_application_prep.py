from __future__ import annotations

import json
from dataclasses import replace

import pytest
from conftest import make_job
from fastapi.testclient import TestClient

from clue_ai.application_prep import (
    add_source,
    application_email_instruction_for_description,
    approved_claims,
    get_preparation,
    heartbeat_preparation,
    list_claims,
    list_sources,
    request_preparation,
    retry_preparation,
    review_claim,
    set_source_options,
    suggest_claims,
)
from clue_ai.application_prompts import MAX_OUTPUT_TOKENS, OUTPUT_SCHEMA_VERSION
from clue_ai.applications import mark_applied
from clue_ai.database import connect, initialize, save_search_run
from clue_ai.domain import SearchCriteria
from clue_ai.lifecycle import mark_interrupted_preparations
from clue_ai.repository import save_jobs, save_run_results, update_run
from clue_ai.web import create_app

ORIGIN = {"Origin": "http://127.0.0.1"}
OFFICIAL_SOURCE_URL = "https://careers.example.org/jobs/software-engineer-intern"


@pytest.mark.parametrize(
    "description",
    [
        "To apply, email your CV and cover letter to recruitment@example.org.",
        "Applications must be sent by email to recruitment@example.org.",
        "Send your resume to hiring@example.org before the deadline.",
    ],
)
def test_application_email_instruction_requires_an_explicit_application_channel(description):
    assert application_email_instruction_for_description(description)


@pytest.mark.parametrize(
    "description",
    [
        "Contact our team by email if you have questions about the company.",
        "Email our recruiter to learn more about the team; apply through the website.",
        "Our recruiting team can be reached at recruitment@example.org.",
        "Submit your application through the online form.",
    ],
)
def test_ordinary_contact_or_online_application_does_not_request_an_application_email(description):
    assert not application_email_instruction_for_description(description)


def test_private_sources_generate_only_unreviewed_claim_suggestions(settings, database):
    source = add_source(
        database,
        settings,
        "technical-profile.md",
        "technical_profile",
        b"Implemented a typed local workflow with recoverable state and versioned records.\n"
        b"Measured evaluation latency across three hardware configurations.",
    )

    added = suggest_claims(database, source["id"])

    claims = list_claims(database, source["id"])
    assert added == 2
    assert all(claim["status"] == "unreviewed" for claim in claims)
    assert approved_claims(database) == []
    assert source["permitted"] == 0
    assert source["file_path"].startswith(str(settings.cv_dir.resolve()))
    assert suggest_claims(database, source["id"]) == 0
    assert approved_claims(database) == []
    assert set_source_options(
        database,
        source["id"],
        permitted=True,
        default_cv=False,
        structure_policy="preserve",
    )

    assert review_claim(
        database,
        claims[0]["id"],
        status="approved",
        evidence_level="implemented",
        category="systems",
        role_family="applied_ai_llm",
        owner_note="Synthetic test evidence.",
    )
    approved = approved_claims(database, "applied_ai_llm")
    assert len(approved) == 1
    assert approved[0]["source_type"] == "technical_profile"
    assert approved[0]["evidence_level"] == "implemented"


def test_cv_reference_defaults_and_structure_policy_are_owner_selected(settings, database):
    profile = add_source(
        database,
        settings,
        "profile.md",
        "technical_profile",
        b"A compact profile source with enough readable text for the local store.",
    )
    cv = add_source(
        database,
        settings,
        "resume.md",
        "resume",
        b"A longer synthetic resume source with multiple sections and enough readable text.",
    )

    with pytest.raises(ValueError, match="Only an uploaded resume"):
        set_source_options(
            database,
            profile["id"],
            permitted=True,
            default_cv=True,
            structure_policy="preserve",
        )
    assert set_source_options(
        database,
        cv["id"],
        permitted=True,
        default_cv=True,
        structure_policy="allow_improvements",
    )
    selected = next(
        item for item in list_sources(database) if item["id"] == cv["id"]
    )
    assert selected["permitted"] == 1
    assert selected["is_default_cv"] == 1
    assert selected["structure_policy"] == "allow_improvements"


def _save_eligible_match(database_path, run_id="run-app-prep", *, filter_status="match", eligibility_status="eligible"):
    save_jobs(database_path, [make_job()])
    with connect(database_path) as db:
        job_id = db.execute("SELECT id FROM jobs LIMIT 1").fetchone()["id"]
    save_search_run(database_path, run_id, SearchCriteria())
    update_run(database_path, run_id, status="complete", completed=True)
    save_run_results(
        database_path,
        run_id,
        [{"id": job_id, "filter_status": filter_status, "eligibility_status": eligibility_status}],
        score_state="scored",
    )
    return job_id


def _configure_preparation_inputs(settings, database):
    technical = add_source(
        database,
        settings,
        "synthetic-technical-profile.md",
        "technical_profile",
        b"Implemented a typed local workflow with recoverable state and versioned records.\n",
    )
    set_source_options(
        database,
        technical["id"],
        permitted=True,
        default_cv=False,
        structure_policy="preserve",
    )
    suggest_claims(database, technical["id"])
    claim = list_claims(database, technical["id"])[0]
    review_claim(
        database,
        claim["id"],
        status="approved",
        evidence_level="implemented",
        category="systems",
        role_family="applied_ai_llm",
        owner_note="Synthetic fixture approved by the test owner.",
    )
    cv = add_source(
        database,
        settings,
        "synthetic-resume.md",
        "resume",
        b"Synthetic Candidate\nExperience\nBuilt reliable Python services for Example Labs.\n",
    )
    set_source_options(
        database,
        cv["id"],
        permitted=True,
        default_cv=True,
        structure_policy="preserve",
    )
    return cv["id"]


def test_preparation_request_requires_eligible_jev_result_and_is_idempotent(settings, database):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(database)

    first, created = request_preparation(database, job_id, "run-app-prep")
    repeated, created_again = request_preparation(database, job_id, "run-app-prep")

    assert created is True
    assert created_again is False
    assert first["id"] == repeated["id"]
    assert first["state"] == "requested"
    record = get_preparation(database, first["id"])
    assert record["snapshot"]["filter_status"] == "match"
    assert record["snapshot"]["canonical_url"] == "https://jobs.example.org/openings/software-engineer"


def test_new_generation_policy_gets_a_new_manual_request_for_same_listing(settings, database, monkeypatch):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(database)

    first, created = request_preparation(database, job_id, "run-app-prep")
    monkeypatch.setattr("clue_ai.application_prep.PROMPT_VERSION", "synthetic-prompt-next")
    monkeypatch.setitem(MAX_OUTPUT_TOKENS, "recruiter", 9_100)
    second, created_after_revision = request_preparation(database, job_id, "run-app-prep")
    first_record = get_preparation(database, first["id"])
    second_record = get_preparation(database, second["id"])

    assert created is True
    assert created_after_revision is True
    assert second["id"] != first["id"]
    assert first_record["snapshot"]["inputs"]["generation_policy"]["prompt_version"] != second_record[
        "snapshot"
    ]["inputs"]["generation_policy"]["prompt_version"]
    assert first_record["snapshot"]["inputs"]["generation_policy"]["output_token_limits"]["recruiter"] == 9_000
    assert second_record["snapshot"]["inputs"]["generation_policy"] == {
        "model": "gpt-6-luna",
        "reasoning_effort": "high",
        "prompt_version": "synthetic-prompt-next",
        "output_schema_version": OUTPUT_SCHEMA_VERSION,
        "output_token_limits": dict(sorted(MAX_OUTPUT_TOKENS.items())),
    }


def test_owner_trigger_can_use_permitted_technical_profile_without_preapproving_each_claim(settings, database):
    technical = add_source(
        database,
        settings,
        "synthetic-technical-profile.md",
        "technical_profile",
        b"Implemented a typed local workflow and measured evaluation latency across three configurations.\n",
    )
    set_source_options(
        database,
        technical["id"],
        permitted=True,
        default_cv=False,
        structure_policy="preserve",
    )
    suggest_claims(database, technical["id"])
    cv = add_source(
        database,
        settings,
        "synthetic-resume.md",
        "resume",
        b"Synthetic Candidate\nExperience\nBuilt a typed local workflow.\n",
    )
    set_source_options(
        database,
        cv["id"],
        permitted=True,
        default_cv=True,
        structure_policy="preserve",
    )
    job_id = _save_eligible_match(database)

    request_row, created = request_preparation(database, job_id, "run-app-prep", cv["id"])
    request = get_preparation(database, request_row["id"])

    assert created is True
    assert request["snapshot"]["inputs"]["approved_claim_ids"] == []
    assert request["snapshot"]["inputs"]["technical_profile_sources"] == [
        {
            "id": technical["id"],
            "filename": technical["filename"],
            "source_type": "technical_profile",
            "content_sha256": technical["content_sha256"],
            "authorship_label": "unknown",
        }
    ]


@pytest.mark.parametrize(
    ("filter_status", "eligibility_status"),
    [("unassessed", "eligible")],
)
def test_preparation_request_still_rejects_unassessed_jev_even_with_override_flags(
    database, filter_status, eligibility_status
):
    job_id = _save_eligible_match(database)
    save_run_results(
        database,
        "run-app-prep",
        [{"id": job_id, "filter_status": filter_status, "eligibility_status": eligibility_status}],
        score_state="scored",
    )

    with pytest.raises(ValueError, match="Unassessed listings must be scored"):
        request_preparation(
            database,
            job_id,
            "run-app-prep",
            confirm_jev_conflict=True,
            confirm_location_eligibility=True,
        )


@pytest.mark.parametrize(
    ("filter_status", "eligibility_status", "confirm_conflict", "confirm_location"),
    [
        ("conflict", "eligible", True, False),
        ("review", "needs_verification", False, True),
        ("conflict", "not_eligible", True, True),
    ],
)
def test_owner_acknowledgements_allow_scored_blockers_without_changing_jev(
    settings, database, filter_status, eligibility_status, confirm_conflict, confirm_location
):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(
        database,
        filter_status=filter_status,
        eligibility_status=eligibility_status,
    )

    request, created = request_preparation(
        database,
        job_id,
        "run-app-prep",
        confirm_jev_conflict=confirm_conflict,
        confirm_location_eligibility=confirm_location,
    )
    record = get_preparation(database, request["id"])

    assert created is True
    assert record["snapshot"]["filter_status"] == filter_status
    assert record["snapshot"]["eligibility_status"] == eligibility_status
    assert record["snapshot"]["owner_preparation_overrides"] == {
        "jev_conflict_acknowledged": filter_status == "conflict",
        "location_eligibility_acknowledged": eligibility_status != "eligible",
    }
    repeated, was_created = request_preparation(
        database,
        job_id,
        "run-app-prep",
        confirm_jev_conflict=confirm_conflict,
        confirm_location_eligibility=confirm_location,
    )
    assert was_created is False
    assert repeated["id"] == request["id"]
    with connect(database) as db:
        saved = db.execute(
            "SELECT filter_status, eligibility_status FROM search_results WHERE run_id = ? AND job_id = ?",
            ("run-app-prep", job_id),
        ).fetchone()
    assert saved["filter_status"] == filter_status
    assert saved["eligibility_status"] == eligibility_status


@pytest.mark.parametrize(
    ("filter_status", "eligibility_status", "expected_message"),
    [
        ("conflict", "eligible", "reviewed the conflict"),
        ("review", "needs_verification", "reviewed the location"),
    ],
)
def test_scored_blocker_requires_its_own_owner_acknowledgement(
    database, filter_status, eligibility_status, expected_message
):
    job_id = _save_eligible_match(
        database,
        filter_status=filter_status,
        eligibility_status=eligibility_status,
    )

    with pytest.raises(ValueError, match=expected_message):
        request_preparation(database, job_id, "run-app-prep")


def test_owner_override_is_retained_when_a_failed_request_is_retried(settings, database):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(
        database,
        filter_status="conflict",
        eligibility_status="needs_verification",
    )
    request, _created = request_preparation(
        database,
        job_id,
        "run-app-prep",
        confirm_jev_conflict=True,
        confirm_location_eligibility=True,
    )
    with connect(database) as db:
        db.execute(
            "UPDATE preparation_requests SET state = 'failed' WHERE id = ?",
            (request["id"],),
        )

    retried, created = retry_preparation(database, request["id"])
    snapshot = get_preparation(database, retried["id"])["snapshot"]

    assert created is True
    assert snapshot["filter_status"] == "conflict"
    assert snapshot["eligibility_status"] == "needs_verification"
    assert snapshot["owner_preparation_overrides"] == {
        "jev_conflict_acknowledged": True,
        "location_eligibility_acknowledged": True,
    }


def test_interrupted_preparation_can_be_manually_retried(settings, database):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(database)
    request, created = request_preparation(database, job_id, "run-app-prep")
    assert created is True
    with connect(database) as db:
        db.execute(
            "UPDATE preparation_requests SET state = 'generating' WHERE id = ?",
            (request["id"],),
        )

    assert mark_interrupted_preparations(database) == 1
    failed = get_preparation(database, request["id"])
    assert failed["state"] == "failed"
    assert "manually retrying" in failed["status_message"]

    retried, was_created = retry_preparation(database, request["id"])
    assert was_created is True
    assert retried["attempt_no"] == 2
    assert retried["state"] == "requested"


def test_scored_blocker_controls_are_visible_on_search_results_history_and_saved_roles(
    settings, monkeypatch
):
    monkeypatch.setattr("clue_ai.web.run_preparation", lambda *_args: None)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    _configure_preparation_inputs(settings, settings.database_path)
    job_id = _save_eligible_match(
        settings.database_path,
        filter_status="conflict",
        eligibility_status="needs_verification",
    )

    for url in ("/searches", "/searches/run-app-prep?view=all"):
        response = client.get(url)
        assert response.status_code == 200
        assert 'name="confirm_jev_conflict"' in response.text
        assert 'name="confirm_location_eligibility"' in response.text
        assert "Generate packet for review" in response.text
        assert "Jev’s saved match decision stays unchanged" in response.text

    client.post(
        f"/jobs/{job_id}/save",
        data={"return_to": "/saved"},
        headers=ORIGIN,
    )
    saved = client.get("/saved")
    assert 'name="confirm_jev_conflict"' in saved.text
    assert 'name="confirm_location_eligibility"' in saved.text

    missing_ack = client.post(
        f"/jobs/{job_id}/prepare",
        data={"run_id": "run-app-prep"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert "reviewed+the+conflict" in missing_ack.headers["location"]

    accepted = client.post(
        f"/jobs/{job_id}/prepare",
        data={
            "run_id": "run-app-prep",
            "confirm_jev_conflict": "on",
            "confirm_location_eligibility": "on",
        },
        headers=ORIGIN,
        follow_redirects=False,
    )
    request_id = accepted.headers["location"].split("/preparations/", 1)[1].split("?", 1)[0]
    dossier = client.get(f"/preparations/{request_id}")
    assert accepted.status_code == 303
    assert "You chose to prepare this listing with a Jev warning" in dossier.text
    assert "Saved Jev filter status:" in dossier.text
    assert "Saved Jev location eligibility:" in dossier.text
    with connect(settings.database_path) as db:
        saved_jev = db.execute(
            "SELECT filter_status, eligibility_status FROM search_results WHERE run_id = ? AND job_id = ?",
            ("run-app-prep", job_id),
        ).fetchone()
    assert saved_jev["filter_status"] == "conflict"
    assert saved_jev["eligibility_status"] == "needs_verification"


def test_permitted_technical_profile_alone_exposes_the_prepare_action(settings, monkeypatch):
    monkeypatch.setattr("clue_ai.web.run_preparation", lambda *_args: None)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    _configure_preparation_inputs(settings, settings.database_path)
    job_id = _save_eligible_match(settings.database_path)
    with connect(settings.database_path) as db:
        db.execute(
            "UPDATE candidate_claims SET status = 'rejected' WHERE source_id IN "
            "(SELECT id FROM preparation_sources WHERE source_type = 'technical_profile')"
        )

    history = client.get("/searches")
    assert "Generate packet" in history.text
    response = client.post(
        f"/jobs/{job_id}/prepare",
        data={"run_id": "run-app-prep"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert response.status_code == 303
    assert response.headers["location"].startswith("/preparations/")


def test_review_result_can_be_prepared_only_with_verified_location_and_stays_a_review(settings, database):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(database, filter_status="review")
    with connect(database) as db:
        db.execute(
            "UPDATE search_results SET dimensions_json = ? WHERE run_id = ? AND job_id = ?",
            (
                json.dumps(
                    {
                        "filter_pay": {
                            "label": "Paid compensation", "status": "review",
                            "model_status": "review", "confidence": 0.85,
                        },
                        "filter_language": {
                            "label": "Language requirements", "status": "review",
                            "model_status": "review", "confidence": 0.85,
                        },
                    }
                ),
                "run-app-prep",
                job_id,
            ),
        )

    request_row, created = request_preparation(
        database,
        job_id,
        "run-app-prep",
        additional_source_url=OFFICIAL_SOURCE_URL,
    )
    record = get_preparation(database, request_row["id"])

    assert created is True
    assert record["snapshot"]["filter_status"] == "review"
    assert record["snapshot"]["eligibility_status"] == "eligible"
    assert OFFICIAL_SOURCE_URL in record["snapshot"]["source_urls"]
    assert record["snapshot"]["inputs"]["additional_source_url"] == OFFICIAL_SOURCE_URL
    assert record["snapshot"]["dimensions_json"] == json.dumps(
        {
            "filter_pay": {
                "label": "Paid compensation", "status": "review",
                "model_status": "review", "confidence": 0.85,
            },
            "filter_language": {
                "label": "Language requirements", "status": "review",
                "model_status": "review", "confidence": 0.85,
            },
        }
    )


def test_preparation_rejects_nonpublic_or_non_https_employer_sources(database):
    job_id = _save_eligible_match(database)

    with pytest.raises(ValueError, match="direct public HTTPS job or application page URL"):
        request_preparation(
            database,
            job_id,
            "run-app-prep",
            additional_source_url="https://127.0.0.1/apply",
        )


def test_retry_preserves_owner_supplied_employer_source(settings, database):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(database, filter_status="review")
    initial, created = request_preparation(
        database,
        job_id,
        "run-app-prep",
        additional_source_url=OFFICIAL_SOURCE_URL,
    )
    assert created is True
    with connect(database) as db:
        db.execute(
            "UPDATE preparation_requests SET state = 'failed' WHERE id = ?",
            (initial["id"],),
        )

    retried, created = retry_preparation(database, initial["id"])

    assert created is True
    assert retried["attempt_no"] == 2
    assert retried["snapshot_json"] == initial["snapshot_json"]
    retried_snapshot = json.loads(retried["snapshot_json"])
    assert retried_snapshot["inputs"]["additional_source_url"] == OFFICIAL_SOURCE_URL


def test_initialize_migrates_legacy_preparation_retry_constraint_and_preserves_children(tmp_path):
    database_path = tmp_path / "legacy-preparation.sqlite3"
    with connect(database_path) as db:
        db.executescript(
            """CREATE TABLE preparation_requests (
                 id TEXT PRIMARY KEY,
                 job_id TEXT NOT NULL,
                 run_id TEXT NOT NULL,
                 snapshot_json TEXT NOT NULL,
                 snapshot_sha256 TEXT NOT NULL,
                 state TEXT NOT NULL DEFAULT 'requested',
                 status_message TEXT NOT NULL DEFAULT '',
                 created_at TEXT NOT NULL,
                 updated_at TEXT NOT NULL,
                 UNIQUE (job_id, snapshot_sha256)
               );
               CREATE TABLE migration_child (
                 id TEXT PRIMARY KEY,
                 request_id TEXT NOT NULL REFERENCES preparation_requests(id)
               );
               INSERT INTO preparation_requests
                 (id, job_id, run_id, snapshot_json, snapshot_sha256, state, created_at, updated_at)
               VALUES ('old-request', 'same-job', 'same-run', '{}', 'same-snapshot',
                       'failed', '2026-10-07', '2026-10-07');
               INSERT INTO migration_child (id, request_id) VALUES ('child-row', 'old-request');"""
        )

    initialize(database_path)

    with connect(database_path) as db:
        request = db.execute(
            "SELECT id, attempt_no, state, worker_heartbeat_at FROM preparation_requests WHERE id = 'old-request'"
        ).fetchone()
        child_count = db.execute("SELECT COUNT(*) FROM migration_child").fetchone()[0]
        indexes = db.execute("PRAGMA index_list(preparation_requests)").fetchall()
        unique_columns = []
        for index in indexes:
            if index["unique"]:
                index_name = str(index["name"]).replace('"', '""')
                unique_columns.append(
                    [
                        column["name"]
                        for column in db.execute(
                            f'PRAGMA index_info("{index_name}")'
                        ).fetchall()
                    ]
                )
        assert ["job_id", "snapshot_sha256", "attempt_no"] in unique_columns
        assert ["job_id", "snapshot_sha256"] not in unique_columns
        assert request["attempt_no"] == 1 and request["state"] == "failed"
        assert request["worker_heartbeat_at"] == ""
        assert child_count == 1
        db.execute(
            """INSERT INTO preparation_requests
               (id, job_id, run_id, snapshot_json, snapshot_sha256, attempt_no,
                state, created_at, updated_at)
               VALUES ('retry-request', 'same-job', 'same-run', '{}', 'same-snapshot', 2,
                       'requested', '2026-10-08', '2026-10-08')"""
        )
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


def test_applied_listing_cannot_be_prepared(database):
    job_id = _save_eligible_match(database)
    assert mark_applied(database, job_id)

    with pytest.raises(ValueError, match="unapplied listing"):
        request_preparation(database, job_id, "run-app-prep")


def test_manual_listing_button_creates_only_a_bound_request(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    _configure_preparation_inputs(settings, settings.database_path)
    job_id = _save_eligible_match(settings.database_path)

    response = client.post(
        f"/jobs/{job_id}/prepare",
        data={"run_id": "run-app-prep"},
        headers=ORIGIN,
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/preparations/")
    request_id = response.headers["location"].split("/preparations/", 1)[1].split("?", 1)[0]
    detail = client.get(f"/preparations/{request_id}")
    assert detail.status_code == 200
    assert "Request queued" in detail.text
    assert "No application is submitted and no outreach is sent" in detail.text
    assert "Generate packet" in client.get("/searches/run-app-prep").text


def test_preparation_progress_endpoint_is_live_private_and_marks_stale_worker(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    _configure_preparation_inputs(settings, settings.database_path)
    job_id = _save_eligible_match(settings.database_path)
    record, created = request_preparation(settings.database_path, job_id, "run-app-prep")
    assert created

    detail = client.get(f"/applications/{record['id']}")
    assert detail.status_code == 200
    progress_panel = detail.text.split('<details id="preparation-progress"', 1)[1].split("</details>", 1)[0]
    assert 'data-progress-url="/applications/' + record["id"] + '/status"' in progress_panel
    assert 'aria-busy="true"' in progress_panel
    assert 'role="progressbar"' in progress_panel
    assert "aria-valuenow" not in progress_panel
    assert "Research role and public application pages" in progress_panel
    assert "Jev checks supported claims and the tailored CV" in progress_panel

    response = client.get(f"/applications/{record['id']}/status")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    status = response.json()
    assert status["state"] == "requested"
    assert status["active"] is True
    assert status["step_index"] == 0
    assert status["stale"] is False
    assert set(status) == {
        "state", "status_message", "created_at", "updated_at", "worker_heartbeat_at",
        "active", "stale", "heartbeat_age_seconds", "stale_after_seconds",
        "poll_interval_ms", "step_index",
    }
    assert "snapshot" not in status and "cv" not in status and "research" not in status

    with connect(settings.database_path) as db:
        db.execute(
            "UPDATE preparation_requests SET state = 'generating', worker_heartbeat_at = ? WHERE id = ?",
            ("2020-01-01T00:00:00+00:00", record["id"]),
        )
    stale = client.get(f"/preparations/{record['id']}/status").json()
    assert stale["active"] is True
    assert stale["stale"] is True
    assert stale["step_index"] == 2


def test_worker_heartbeat_does_not_change_folder_sort_timestamp(settings, database):
    _configure_preparation_inputs(settings, database)
    job_id = _save_eligible_match(database)
    record, _ = request_preparation(database, job_id, "run-app-prep")
    before = get_preparation(database, record["id"])

    assert heartbeat_preparation(database, record["id"])

    after = get_preparation(database, record["id"])
    assert after["updated_at"] == before["updated_at"]
    assert after["worker_heartbeat_at"]


def test_review_listing_button_and_dossier_keep_jev_uncertainty_visible(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    _configure_preparation_inputs(settings, settings.database_path)
    job_id = _save_eligible_match(settings.database_path, filter_status="review")
    with connect(settings.database_path) as db:
        db.execute(
            "UPDATE search_results SET dimensions_json = ? WHERE run_id = ? AND job_id = ?",
            (
                json.dumps(
                    {
                        "filter_pay": {
                            "label": "Paid compensation", "status": "review",
                            "model_status": "review", "confidence": 0.85,
                        },
                        "filter_language": {
                            "label": "Language requirements", "status": "review",
                            "model_status": "review", "confidence": 0.85,
                        },
                    }
                ),
                "run-app-prep",
                job_id,
            ),
        )

    search_page = client.get("/searches/run-app-prep")
    assert "Generate packet" in search_page.text
    assert "Jev marked this listing for review, not as a match" in search_page.text
    assert "Paid compensation" in search_page.text
    assert "Language requirements" in search_page.text
    assert "Add a public employer application page" in search_page.text
    assert "It will not sign in, fill fields, or submit anything." in search_page.text

    response = client.post(
        f"/jobs/{job_id}/prepare",
        data={"run_id": "run-app-prep", "additional_source_url": OFFICIAL_SOURCE_URL},
        headers=ORIGIN,
        follow_redirects=False,
    )
    request_id = response.headers["location"].split("/preparations/", 1)[1].split("?", 1)[0]
    dossier = client.get(f"/preparations/{request_id}")
    assert response.status_code == 303
    assert "Jev review" in dossier.text
    assert "Jev did not confirm a match" in dossier.text
    assert "Not stated" in dossier.text
    assert "Paid compensation" in dossier.text
    assert "Language requirements" in dossier.text
    assert OFFICIAL_SOURCE_URL in dossier.text
    with connect(settings.database_path) as db:
        status = db.execute(
            "SELECT filter_status FROM search_results WHERE run_id = ? AND job_id = ?",
            ("run-app-prep", job_id),
        ).fetchone()["filter_status"]
    assert status == "review"


def test_only_the_manually_selected_listing_starts_preparation(settings, monkeypatch):
    started_request_ids = []
    monkeypatch.setattr(
        "clue_ai.web.run_preparation",
        lambda _database_path, _settings, request_id: started_request_ids.append(request_id),
    )
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    _configure_preparation_inputs(settings, settings.database_path)
    selected_job = replace(
        make_job(
            url="https://jobs.example.org/openings/selected-role",
            title="Selected Role",
        ),
        external_id="selected-role",
    )
    untouched_job = replace(
        make_job(
            url="https://jobs.example.org/openings/untouched-role",
            title="Untouched Role",
        ),
        external_id="untouched-role",
    )
    save_jobs(settings.database_path, [selected_job, untouched_job])
    with connect(settings.database_path) as db:
        job_ids = {
            row["canonical_url"]: row["id"]
            for row in db.execute(
                "SELECT id, canonical_url FROM jobs WHERE canonical_url IN (?, ?)",
                (selected_job.canonical_url, untouched_job.canonical_url),
            ).fetchall()
        }
    run_id = "run-manual-trigger"
    save_search_run(settings.database_path, run_id, SearchCriteria())
    update_run(settings.database_path, run_id, status="complete", completed=True)
    save_run_results(
        settings.database_path,
        run_id,
        [
            {
                "id": job_ids[selected_job.canonical_url],
                "filter_status": "match",
                "eligibility_status": "eligible",
            },
            {
                "id": job_ids[untouched_job.canonical_url],
                "filter_status": "match",
                "eligibility_status": "eligible",
            },
        ],
        score_state="scored",
    )

    results = client.get(f"/searches/{run_id}")
    assert results.status_code == 200
    assert started_request_ids == []
    with connect(settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM preparation_requests").fetchone()[0] == 0

    response = client.post(
        f"/jobs/{job_ids[selected_job.canonical_url]}/prepare",
        data={"run_id": run_id},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert response.status_code == 303
    request_id = response.headers["location"].split("/preparations/", 1)[1].split("?", 1)[0]
    assert started_request_ids == [request_id]
    with connect(settings.database_path) as db:
        rows = db.execute(
            "SELECT id, job_id FROM preparation_requests ORDER BY created_at"
        ).fetchall()
    assert len(rows) == 1
    assert rows[0]["id"] == request_id
    assert rows[0]["job_id"] == job_ids[selected_job.canonical_url]

    repeated = client.post(
        f"/jobs/{job_ids[selected_job.canonical_url]}/prepare",
        data={"run_id": run_id},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert repeated.status_code == 303
    assert started_request_ids == [request_id]
    with connect(settings.database_path) as db:
        assert db.execute("SELECT COUNT(*) FROM preparation_requests").fetchone()[0] == 1
