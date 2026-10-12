from __future__ import annotations

from clue_ai.database import connect
from clue_ai.lifecycle import mark_interrupted_preparations


def test_interrupted_preparations_become_retryable_without_changing_terminal_requests(database):
    active_states = ("requested", "researching", "generating")
    terminal_states = ("review", "completed", "blocked", "failed", "cancelled")
    states = active_states + terminal_states
    with connect(database) as db:
        for index, state in enumerate(states):
            db.execute(
                """INSERT INTO preparation_requests
                   (id, job_id, run_id, snapshot_json, snapshot_sha256, attempt_no,
                    state, status_message, created_at, updated_at, worker_heartbeat_at)
                   VALUES (?, ?, ?, '{}', ?, 1, ?, 'old status', '2026-10-01T00:00:00+00:00',
                           '2026-10-01T00:00:00+00:00', '2026-10-01T00:00:00+00:00')""",
                (f"request-{index}", f"job-{index}", "run-1", f"hash-{index}", state),
            )

    assert mark_interrupted_preparations(database) == len(active_states)

    with connect(database) as db:
        rows = db.execute(
            "SELECT id, state, status_message, updated_at, worker_heartbeat_at "
            "FROM preparation_requests ORDER BY id"
        ).fetchall()

    for index, row in enumerate(rows):
        original_state = states[index]
        if original_state in active_states:
            assert row["state"] == "failed"
            assert "manually retrying" in row["status_message"]
            assert row["updated_at"] != "2026-10-01T00:00:00+00:00"
            # Keep the last heartbeat as useful history for diagnosing the interruption.
            assert row["worker_heartbeat_at"] == "2026-10-01T00:00:00+00:00"
        else:
            assert row["state"] == original_state
            assert row["status_message"] == "old status"

    assert mark_interrupted_preparations(database) == 0


def test_interrupted_preparation_recovery_handles_preparation_table_not_yet_created(tmp_path):
    database = tmp_path / "pre-application-preparation.sqlite3"

    assert mark_interrupted_preparations(database) == 0
