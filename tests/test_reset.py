from __future__ import annotations

import sqlite3
from contextlib import closing

import pytest
from conftest import make_job

from clue_ai.database import get_profile, save_profile, save_search_run, set_jev_consent
from clue_ai.domain import CandidateProfile, SearchCriteria
from clue_ai.repository import (
    all_active_jobs,
    connect,
    reserve_jev_budget,
    save_jobs,
    save_run_results,
    set_job_user_state,
    sources_due,
    update_run,
)
from clue_ai.reset import SEARCH_TABLES, reset_search_data


def seed_completed_search(database):
    save_search_run(database, "before-reset", SearchCriteria())
    save_jobs(database, [make_job()])
    jobs = all_active_jobs(database)
    save_run_results(database, "before-reset", jobs)
    set_job_user_state(database, jobs[0]["id"], "saved")
    reserve_jev_budget(database, "before-reset", "synthetic", 1000, 0.042, 4.0)
    update_run(database, "before-reset", status="complete", completed=True)
    with connect(database) as db:
        db.execute(
            "INSERT INTO source_query_checks VALUES ('jobicy', 'query', '2099-01-01', 'ok')"
        )
        db.execute(
            "UPDATE sources SET last_checked_at='2099-01-01', last_state='ok', last_error='old'"
        )
        db.execute(
            "UPDATE companies SET last_checked_at='2099-01-01', last_state='error', "
            "last_error='old', listing_count=5"
        )


def test_reset_clears_searches_and_cooldowns_preserving_profile_and_spend(database, settings):
    cv = settings.cv_dir / "cv.pdf"
    cv.parent.mkdir()
    cv.write_bytes(b"synthetic CV bytes")
    profile = CandidateProfile(target_roles="AI Engineer", skills="Python", cv_path=str(cv))
    save_profile(database, profile)
    set_jev_consent(database, True)
    seed_completed_search(database)
    with connect(database) as db:
        source_choices = [tuple(r) for r in db.execute("SELECT id,state,enabled FROM sources")]
        company_choices = [tuple(r) for r in db.execute("SELECT id,tracked FROM companies")]
        consent = db.execute("SELECT jev_consent_at FROM app_settings").fetchone()[0]

    result = reset_search_data(database)

    assert result.removed["search_runs"] == 1
    assert result.removed["jobs"] == 1
    assert result.backup_path.is_file()
    assert get_profile(database).target_roles == profile.target_roles
    assert get_profile(database).skills == profile.skills
    assert cv.read_bytes() == b"synthetic CV bytes"
    with connect(database) as db:
        assert all(db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 0 for t in SEARCH_TABLES)
        assert db.execute("SELECT run_id,reserved_tokens FROM jev_usage").fetchone()[:] == (None, 1000)
        assert [tuple(r) for r in db.execute("SELECT id,state,enabled FROM sources")] == source_choices
        assert [tuple(r) for r in db.execute("SELECT id,tracked FROM companies")] == company_choices
        assert db.execute("SELECT jev_consent_at FROM app_settings").fetchone()[0] == consent
        assert db.execute("SELECT COUNT(*) FROM companies WHERE last_checked_at != ''").fetchone()[0] == 0
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert any(s["id"] == "jobicy" for s in sources_due(database))
    with closing(sqlite3.connect(result.backup_path)) as snapshot:
        assert snapshot.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
        assert snapshot.execute("SELECT run_id FROM jev_usage").fetchone()[0] == "before-reset"
    second = reset_search_data(database)
    assert second.removed["jobs"] == 0
    assert second.backup_path != result.backup_path


@pytest.mark.parametrize("status", ["queued", "running", "scoring"])
def test_reset_refuses_active_runs_without_deleting_data(database, status):
    seed_completed_search(database)
    update_run(database, "before-reset", status=status)
    with pytest.raises(ValueError, match="Stop Clue"):
        reset_search_data(database)
    with connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM search_runs").fetchone()[0] == 1
    assert list((database.parent / "backups").glob("*.sqlite3")) == []


def test_failed_reset_rolls_back_all_deletions_and_retains_recovery_backup(database):
    seed_completed_search(database)
    with connect(database) as db:
        db.execute(
            "CREATE TRIGGER refuse_job_deletion BEFORE DELETE ON jobs "
            "BEGIN SELECT RAISE(ABORT, 'synthetic failure'); END"
        )
    with pytest.raises(sqlite3.IntegrityError, match="synthetic failure"):
        reset_search_data(database)
    with connect(database) as db:
        assert all(db.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] == 1 for t in SEARCH_TABLES)
        assert db.execute("SELECT run_id FROM jev_usage").fetchone()[0] == "before-reset"
        assert db.execute("SELECT last_state FROM sources WHERE id='jobicy'").fetchone()[0] == "ok"
    assert len(list((database.parent / "backups").glob("*.sqlite3"))) == 1
