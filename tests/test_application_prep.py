from __future__ import annotations

from dataclasses import replace

import pytest
from conftest import make_job
from fastapi.testclient import TestClient

from clue_ai.application_prep import (
    add_source,
    approved_claims,
    get_preparation,
    list_claims,
    list_sources,
    request_preparation,
    review_claim,
    set_source_options,
    suggest_claims,
)
from clue_ai.applications import mark_applied
from clue_ai.database import connect, save_search_run
from clue_ai.domain import SearchCriteria
from clue_ai.repository import save_jobs, save_run_results, update_run
from clue_ai.web import create_app

ORIGIN = {"Origin": "http://127.0.0.1"}


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


def _save_eligible_match(database_path, run_id="run-app-prep"):
    save_jobs(database_path, [make_job()])
    with connect(database_path) as db:
        job_id = db.execute("SELECT id FROM jobs LIMIT 1").fetchone()["id"]
    save_search_run(database_path, run_id, SearchCriteria())
    update_run(database_path, run_id, status="complete", completed=True)
    save_run_results(
        database_path,
        run_id,
        [{"id": job_id, "filter_status": "match", "eligibility_status": "eligible"}],
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


def test_preparation_request_requires_match_and_is_idempotent(settings, database):
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


@pytest.mark.parametrize("filter_status", ["review", "conflict", "unassessed"])
def test_preparation_request_rejects_nonmatch_jev_states(database, filter_status):
    job_id = _save_eligible_match(database)
    save_run_results(
        database,
        "run-app-prep",
        [{"id": job_id, "filter_status": filter_status}],
        score_state="scored",
    )

    with pytest.raises(ValueError, match="completed Jev match"):
        request_preparation(database, job_id, "run-app-prep")


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
    assert "Owner selected this listing" in detail.text
    assert "No external action is performed by Clue" in detail.text
    assert "Prepare application" in client.get("/searches/run-app-prep").text


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
