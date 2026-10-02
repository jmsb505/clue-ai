"""Clear discovery state while retaining the owner's profile and actual Jev spend."""

from __future__ import annotations

import socket
import sqlite3
import uuid
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from clue_ai.config import Settings
from clue_ai.database import connect

SEARCH_TABLES = (
    "search_results", "search_runs", "source_query_checks", "job_user_state", "job_sources", "jobs"
)


@dataclass(frozen=True)
class ResetResult:
    removed: dict[str, int]
    backup_path: Path


def reset_search_data(database_path: Path) -> ResetResult:
    """Back up and atomically clear search data. The caller must stop Clue first."""
    if not database_path.is_file():
        raise ValueError("No local Clue database exists to reset.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_dir = database_path.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"before-reset-{stamp}-{uuid.uuid4().hex[:8]}.sqlite3"
    with connect(database_path) as db:
        if _has_active_runs(db):
            raise ValueError("Stop Clue and its crawler processes before resetting searches.")
        with closing(sqlite3.connect(backup_path)) as backup:
            db.backup(backup)
        db.execute("BEGIN IMMEDIATE")
        try:
            if _has_active_runs(db):
                raise ValueError("A search started during reset; stop Clue and try again.")
            removed = {
                table: db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                for table in SEARCH_TABLES
            }
            for table in SEARCH_TABLES:
                db.execute(f"DELETE FROM {table}")
            db.execute(
                "UPDATE sources SET last_checked_at = '', last_state = 'never', last_error = ''"
            )
            db.execute(
                """UPDATE companies SET last_checked_at = '', last_state = 'never',
                   last_error = '', listing_count = 0,
                   board_state = CASE WHEN tracked = 1 THEN 'candidate' ELSE 'paused' END"""
            )
            # ON DELETE SET NULL detaches charges from deleted runs without erasing actual spend.
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
    return ResetResult(removed, backup_path)


def _has_active_runs(db: sqlite3.Connection) -> bool:
    return db.execute(
        "SELECT 1 FROM search_runs WHERE status IN ('queued', 'running', 'scoring') LIMIT 1"
    ).fetchone() is not None


def main() -> None:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            raise SystemExit("Clue is running. Use '.\\scripts\\clue.ps1 reset' to stop it first.")
    settings = Settings.from_environment()
    if not settings.database_path.is_file():
        print("No saved search data exists. Clue remains stopped.")
        return
    result = reset_search_data(settings.database_path)
    print(f"Reset {result.removed['search_runs']} searches and {result.removed['jobs']} listings.")
    print("Cleared rankings, saved/hidden jobs, query caches and source/company refresh timers.")
    print("Kept your CV, profile, application tracker, API settings, source choices and Jev spend history.")
    print(f"Local backup: {result.backup_path}")
    print("Clue remains stopped. Start it when you are ready for a fresh search.")


if __name__ == "__main__":
    main()
