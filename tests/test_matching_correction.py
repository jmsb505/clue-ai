from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import make_job
from fastapi.testclient import TestClient

from clue_ai.database import connect, save_search_run
from clue_ai.domain import SearchCriteria
from clue_ai.geography import POLICY_VERSION, explicit_work_region
from clue_ai.jev import (
    FILTER_CHECK_INSTRUCTIONS,
    _combine_filter_checks,
    _parse_filter_answer,
    apply_location_constraint,
)
from clue_ai.jobs import classify_location
from clue_ai.repair_matching import repair_saved_matching
from clue_ai.repository import (
    all_active_jobs,
    get_run_results,
    get_source,
    save_jobs,
    save_run_results,
    update_run,
    update_score,
)
from clue_ai.sources import _parse_json_feed
from clue_ai.web import create_app


@pytest.mark.parametrize(
    ("location", "target", "expected"),
    [
        ("LATAM", "Italy", "not_eligible"),
        ("Latin America", "Milan, Italy", "not_eligible"),
        ("LATAM", "Brazil", "eligible"),
        ("Europe / LATAM", "Italy", "eligible"),
        ("LATAM, Italy", "Italy", "eligible"),
        ("LATAM, USA", "USA", "eligible"),
        ("Europe", "Brazil", "not_eligible"),
        ("APAC", "Italy", "not_eligible"),
        ("North America", "Italy", "not_eligible"),
        ("EMEA", "Italy", "needs_verification"),
        ("EU", "UK", "not_eligible"),
        ("EEA", "Norway", "eligible"),
        ("Worldwide except Italy", "Italy", "not_eligible"),
        ("LATAM", "unmapped city", "needs_verification"),
    ],
)
def test_work_regions_respect_membership_and_alternatives(location, target, expected):
    assert classify_location(location, "Remote role", target)[0] == expected


@pytest.mark.parametrize(
    ("description", "target", "expected"),
    [
        ("Responsibilities. " * 400 + "Remote from LATAM", "Italy", "not_eligible"),
        ("Worldwide company; US-only", "Italy", "not_eligible"),
        ("US-only", "USA", "eligible"),
        ("Remote in Europe or LATAM or APAC", "India", "eligible"),
        ("Our clients are in LATAM and our offices are in Europe", "Italy", ""),
        ("Not remote in LATAM", "Italy", ""),
        ("Remote in LATAM preferred", "Italy", ""),
    ],
)
def test_full_description_only_enforces_explicit_restrictions(description, target, expected):
    assert explicit_work_region("Remote", description, target)[0] == expected


def test_low_confidence_is_not_an_extra_categorical_filter():
    for decision in ("match", "review", "conflict"):
        assert (
            _parse_filter_answer(SimpleNamespace(choice=decision, confidence=0.31))["status"]
            == decision
        )
    assert (
        _parse_filter_answer(SimpleNamespace(choice="match", confidence=float("nan")))["status"]
        == "review"
    )
    assert (
        _parse_filter_answer(SimpleNamespace(choice="match", confidence=-1))["status"] == "review"
    )
    assert _parse_filter_answer(SimpleNamespace(choice="unsupported", confidence=0.99)) is None


def test_region_override_preserves_model_and_missing_answers():
    checks = {
        k: _parse_filter_answer(SimpleNamespace(choice="match", confidence=0.31))
        for k in FILTER_CHECK_INSTRUCTIONS
    }
    apply_location_constraint(checks, {"location_raw": "LATAM"}, SearchCriteria())
    assert checks["location"]["model_status"] == "match"
    assert checks["location"]["constraint_evidence"] == "LATAM"
    assert _combine_filter_checks(checks) == "conflict"
    del checks["pay"]
    assert _combine_filter_checks(checks) == "unassessed"


def test_jobicy_remote_feed_retains_workplace_fact(settings, database):
    jobs = _parse_json_feed(
        "jobicy_api",
        get_source(database, "jobicy"),
        {
            "jobs": [
                {
                    "id": "example",
                    "jobTitle": "AI Automation Engineer",
                    "companyName": "Example",
                    "jobGeo": "LATAM",
                    "jobDescription": "Build AI workflows.",
                    "url": "https://jobicy.com/jobs/example",
                }
            ]
        },
        settings,
    )
    assert jobs[0].workplace_type == "remote"


def seed_repair(database):
    save_search_run(database, "saved", SearchCriteria())
    save_jobs(
        database,
        [
            replace(
                make_job(location="LATAM", description="Build AI workflows."),
                workplace_type="unknown",
            ),
            replace(
                make_job(url="https://jobs.example.org/graduate", title="Graduate AI Engineer"),
                external_id="graduate",
            ),
        ],
    )
    save_run_results(database, "saved", all_active_jobs(database))
    for job in get_run_results(database, "saved"):
        dimensions = {"role": {"score": 0.8, "confidence": 0.5}}
        dimensions.update(
            {
                f"filter_{k}": {
                    "status": "review",
                    "model_status": "match",
                    "confidence": 0.31,
                    "score": None,
                }
                for k in FILTER_CHECK_INSTRUCTIONS
            }
        )
        update_score(
            database,
            "saved",
            job["id"],
            score_state="scored",
            combined_score=0.8,
            dimensions=dimensions,
            filter_status="review",
            rubric_version="fit-v1.4.0",
        )
    update_run(database, "saved", status="complete", matched_count=0, scored_count=2)


def test_repair_retains_scores_raw_answers_and_backup_and_is_idempotent(database, settings):
    seed_repair(database)
    count, backup = repair_saved_matching(database)
    assert count == 2
    with sqlite3.connect(backup) as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM search_results WHERE filter_status='review'"
            ).fetchone()[0]
            == 2
        )
    jobs = get_run_results(database, "saved")
    latam = next(j for j in jobs if j["location_raw"] == "LATAM")
    assert latam["filter_status"] == "conflict"
    assert latam["workplace_type"] == "remote"
    assert latam["eligibility_status"] == "not_eligible"
    assert latam["combined_score"] == 0.8
    assert latam["dimensions"]["filter_location"]["model_status"] == "match"
    assert latam["dimensions"]["filter_location"]["previous_status"] == "review"
    assert latam["dimensions"]["filter_location"]["decision_policy"] == POLICY_VERSION
    assert next(j for j in jobs if j["location_raw"] == "Europe")["filter_status"] == "match"
    with TestClient(create_app(settings)) as client:
        response = client.get("/searches/saved?view=conflict")
    assert response.status_code == 200
    assert "explicit listing restriction: LATAM" in response.text
    assert "Jev originally: match" in response.text
    with connect(database) as db:
        before = [tuple(r) for r in db.execute("SELECT * FROM search_results ORDER BY job_id")]
    assert repair_saved_matching(database)[0] == 0
    with connect(database) as db:
        assert [
            tuple(r) for r in db.execute("SELECT * FROM search_results ORDER BY job_id")
        ] == before


def test_repair_refuses_active_run(database):
    seed_repair(database)
    update_run(database, "saved", status="scoring")
    with pytest.raises(ValueError, match="Stop Clue"):
        repair_saved_matching(database)


def test_repair_does_not_invent_paid_status_or_missing_answers(database):
    seed_repair(database)
    with connect(database) as db:
        row = db.execute(
            "SELECT r.job_id,r.dimensions_json FROM search_results r JOIN jobs j ON j.id=r.job_id WHERE j.location_raw='Europe'"
        ).fetchone()
        dimensions = json.loads(row["dimensions_json"])
        dimensions["filter_pay"]["model_status"] = "review"
        db.execute(
            "UPDATE search_results SET dimensions_json=? WHERE job_id=?",
            (json.dumps(dimensions), row["job_id"]),
        )
    repair_saved_matching(database)
    job = next(j for j in get_run_results(database, "saved") if j["location_raw"] == "Europe")
    assert job["filter_status"] == "review"
    assert job["filter_checks"]["pay"]["status"] == "review"
    with connect(database) as db:
        dimensions.pop("filter_pay")
        db.execute(
            "UPDATE search_results SET dimensions_json=? WHERE job_id=?",
            (json.dumps(dimensions), job["id"]),
        )
    repair_saved_matching(database)
    job = next(j for j in get_run_results(database, "saved") if j["location_raw"] == "Europe")
    assert job["filter_status"] == "unassessed"
    assert "pay" not in job["filter_checks"]


def test_repair_rolls_back_all_changes_on_invalid_retained_answer(database):
    seed_repair(database)
    with connect(database) as db:
        row = db.execute(
            "SELECT job_id,dimensions_json FROM search_results ORDER BY job_id DESC LIMIT 1"
        ).fetchone()
        dimensions = json.loads(row["dimensions_json"])
        dimensions["filter_pay"]["model_status"] = "unsupported"
        db.execute(
            "UPDATE search_results SET dimensions_json=? WHERE job_id=?",
            (json.dumps(dimensions), row["job_id"]),
        )
    with pytest.raises(ValueError, match="valid original"):
        repair_saved_matching(database)
    with connect(database) as db:
        assert (
            db.execute(
                "SELECT COUNT(*) FROM search_results WHERE filter_status='review'"
            ).fetchone()[0]
            == 2
        )
