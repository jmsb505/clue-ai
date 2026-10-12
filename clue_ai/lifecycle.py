"""Recovery for work interrupted when the local Clue process stops."""

from __future__ import annotations

from pathlib import Path

from clue_ai.database import connect
from clue_ai.domain import utc_now


def mark_interrupted_runs(database_path: Path) -> int:
    """Mark unfinished searches as stopped once their server process is gone."""
    message = (
        "Clue was stopped before this search finished. Its crawl and scoring work has stopped; "
        "start a new search to continue."
    )
    with connect(database_path) as db:
        cursor = db.execute(
            """UPDATE search_runs
               SET status = 'failed', stage = 'interrupted', message = ?,
                   error = 'Clue stopped before the search finished.', completed_at = ?
               WHERE status IN ('queued', 'running', 'scoring')""",
            (message, utc_now()),
        )
    return cursor.rowcount


def mark_interrupted_preparations(database_path: Path) -> int:
    """Make active application preparations retryable after their worker is gone."""
    message = (
        "Clue stopped while this preparation was active. The run is marked failed; "
        "review any unresolved provider usage before manually retrying."
    )
    with connect(database_path) as db:
        table = db.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'preparation_requests'"
        ).fetchone()
        if table is None:
            return 0
        cursor = db.execute(
            """UPDATE preparation_requests
               SET state = 'failed', status_message = ?, updated_at = ?
               WHERE state IN ('requested', 'researching', 'generating')""",
            (message, utc_now()),
        )
    return cursor.rowcount
