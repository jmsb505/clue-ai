"""Repair derived filters from retained Jev answers without new API requests."""

from __future__ import annotations

import json
import socket
import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from clue_ai.config import Settings
from clue_ai.database import connect
from clue_ai.domain import SearchCriteria
from clue_ai.geography import POLICY_VERSION
from clue_ai.jev import (
    FILTER_CHECK_INSTRUCTIONS,
    _combine_filter_checks,
    _filter_evidence,
    _parse_filter_answer,
    apply_location_constraint,
)
from clue_ai.jobs import classify_location
from clue_ai.reset import _has_active_runs


def repair_saved_matching(database_path: Path) -> tuple[int, Path]:
    """Caller must stop Clue. Backup and transaction retain profile, scores and charges."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = (
        database_path.parent
        / "backups"
        / f"before-matching-repair-{stamp}-{uuid.uuid4().hex[:8]}.sqlite3"
    )
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    repaired = 0
    with connect(database_path) as db:
        if _has_active_runs(db):
            raise ValueError("Stop Clue and its crawlers before repairing saved searches.")
        with closing(sqlite3.connect(backup_path)) as backup:
            db.backup(backup)
        db.execute("BEGIN IMMEDIATE")
        try:
            if _has_active_runs(db):
                raise ValueError("A search started during repair. Stop Clue first.")
            for run in db.execute("SELECT * FROM search_runs WHERE status = 'complete'").fetchall():
                raw_criteria = json.loads(run["criteria_json"])
                criteria = SearchCriteria(**raw_criteria)
                changed_run = False
                rows = db.execute(
                    """SELECT r.*, j.location_raw, j.description FROM search_results r
                       JOIN jobs j ON j.id = r.job_id WHERE r.run_id = ?""",
                    (run["id"],),
                ).fetchall()
                for row in rows:
                    if row["rubric_version"] != "fit-v1.4.0":
                        continue  # Older composite decisions cannot be reconstructed.
                    dimensions = json.loads(row["dimensions_json"])
                    checks = {
                        name: dimensions[f"filter_{name}"]
                        for name in FILTER_CHECK_INSTRUCTIONS
                        if f"filter_{name}" in dimensions
                    }
                    if not checks or all(
                        c.get("decision_policy") == POLICY_VERSION for c in checks.values()
                    ):
                        continue
                    for check in checks.values():
                        if check.get("decision_policy") == POLICY_VERSION:
                            continue
                        answer = _parse_filter_answer(
                            SimpleNamespace(
                                choice=check.get("model_status"), confidence=check.get("confidence")
                            )
                        )
                        if answer is None:
                            raise ValueError(
                                "Saved check lacks a valid original Jev decision; repair aborted."
                            )
                        check["previous_status"] = check["status"]
                        check.update(answer)
                    job = dict(row)
                    apply_location_constraint(checks, job, criteria)
                    eligibility, location_evidence = classify_location(
                        row["location_raw"], row["description"], criteria.work_from
                    )
                    evidence = [
                        line
                        for line in json.loads(row["evidence_json"])
                        if not line.startswith(
                            (
                                "Jev reports a requirement conflict for",
                                "Verify these requirements on the original posting",
                            )
                        )
                    ]
                    evidence = _filter_evidence(checks) + evidence
                    reason = (
                        row["score_reason"]
                        + f" Local decision correction: {POLICY_VERSION}; no new Jev call."
                    )
                    db.execute(
                        """UPDATE search_results SET filter_status = ?, dimensions_json = ?,
                           eligibility_status = ?, eligibility_evidence = ?, evidence_json = ?,
                           score_reason = ? WHERE run_id = ? AND job_id = ?""",
                        (
                            _combine_filter_checks(checks),
                            json.dumps(dimensions),
                            eligibility,
                            location_evidence,
                            json.dumps(evidence),
                            reason,
                            run["id"],
                            row["job_id"],
                        ),
                    )
                    repaired += 1
                    changed_run = True
                if changed_run:
                    counts = dict(
                        db.execute(
                            "SELECT filter_status, COUNT(*) FROM search_results WHERE run_id = ? GROUP BY filter_status",
                            (run["id"],),
                        ).fetchall()
                    )
                    message = (
                        f"Saved Jev decisions corrected locally: {counts.get('match', 0)} filter matches, "
                        f"{counts.get('review', 0)} need verification, {counts.get('conflict', 0)} conflicts. "
                        "Candidate fit scores are unchanged; no new Jev requests or charges."
                    )
                    db.execute(
                        "UPDATE search_runs SET matched_count = ?, message = ? WHERE id = ?",
                        (counts.get("match", 0), message, run["id"]),
                    )
            # Jobicy's source is an explicitly remote jobs feed, even without the word in its JD.
            db.execute("""UPDATE jobs SET workplace_type = 'remote' WHERE workplace_type = 'unknown'
                          AND EXISTS (SELECT 1 FROM job_sources s WHERE s.job_id = jobs.id
                                      AND s.source_id = 'jobicy')""")
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
    return repaired, backup_path


def main() -> None:
    with socket.socket() as probe:
        probe.settimeout(0.5)
        if probe.connect_ex(("127.0.0.1", 8000)) == 0:
            raise SystemExit(
                "Stop Clue with '.\\scripts\\clue.ps1 stop' before repairing saved searches."
            )
    settings = Settings.from_environment()
    if not settings.database_path.is_file():
        raise SystemExit("No saved Clue database exists.")
    repaired, backup = repair_saved_matching(settings.database_path)
    print(f"Corrected {repaired} saved decisions without new Jev calls. Backup: {backup}")
    print("Clue remains stopped.")


if __name__ == "__main__":
    main()
