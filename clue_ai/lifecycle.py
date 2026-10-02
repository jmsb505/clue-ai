"""Recovery for searches interrupted when the local Clue process stops."""

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
