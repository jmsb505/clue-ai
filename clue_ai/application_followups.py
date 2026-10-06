"""Owner-managed, in-app follow-up reminders for prepared opportunities."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from clue_ai.database import connect
from clue_ai.domain import utc_now

FOLLOW_UP_KINDS = {"outreach", "application"}


def schedule_followup(
    database_path: Path,
    request_id: str,
    *,
    kind: str,
    due_on: str,
    note: str = "",
    today: date | None = None,
) -> str:
    """Create or replace the one active reminder for an owner-triggered request."""
    if kind not in FOLLOW_UP_KINDS:
        raise ValueError("Choose an outreach or application follow-up.")
    try:
        parsed_due = date.fromisoformat(due_on)
    except (TypeError, ValueError) as exc:
        raise ValueError("Choose a valid follow-up date.") from exc
    if parsed_due.isoformat() != due_on:
        raise ValueError("Choose a valid follow-up date.")
    if parsed_due < (today or datetime.now().astimezone().date()):
        raise ValueError("Choose today or a future date for the reminder.")
    note = note.strip()[:500]
    now = utc_now()
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        request = db.execute(
            "SELECT id FROM preparation_requests WHERE id = ?", (request_id,)
        ).fetchone()
        approved_packet = db.execute(
            "SELECT 1 FROM preparation_packets WHERE request_id = ? AND status = 'approved' LIMIT 1",
            (request_id,),
        ).fetchone()
        if request is None or approved_packet is None:
            db.execute("ROLLBACK")
            raise ValueError("Approve a complete packet before scheduling a follow-up reminder.")
        existing = db.execute(
            "SELECT id FROM application_followups WHERE request_id = ? AND state = 'scheduled'",
            (request_id,),
        ).fetchone()
        if existing:
            reminder_id = existing["id"]
            db.execute(
                """UPDATE application_followups
                   SET kind = ?, due_on = ?, note = ?, resolution = '', updated_at = ?
                   WHERE id = ?""",
                (kind, due_on, note, now, reminder_id),
            )
        else:
            reminder_id = uuid.uuid4().hex
            db.execute(
                """INSERT INTO application_followups
                   (id, request_id, kind, due_on, note, state, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'scheduled', ?, ?)""",
                (reminder_id, request_id, kind, due_on, note, now, now),
            )
        db.execute("COMMIT")
    return reminder_id


def finish_followup(
    database_path: Path,
    request_id: str,
    *,
    state: str,
    resolution: str,
) -> bool:
    """Complete a manual action or cancel a reminder after a reply/closure."""
    if state not in {"completed", "cancelled"}:
        raise ValueError("Choose a supported follow-up result.")
    resolution = resolution.strip()[:200]
    with connect(database_path) as db:
        result = db.execute(
            """UPDATE application_followups
               SET state = ?, resolution = ?, updated_at = ?
               WHERE request_id = ? AND state = 'scheduled'""",
            (state, resolution, utc_now(), request_id),
        )
    return result.rowcount > 0


def cancel_followup_for_request(database_path: Path, request_id: str, reason: str) -> int:
    with connect(database_path) as db:
        result = db.execute(
            """UPDATE application_followups SET state = 'cancelled', resolution = ?, updated_at = ?
               WHERE request_id = ? AND state = 'scheduled'""",
            (reason[:200], utc_now(), request_id),
        )
    return result.rowcount


def cancel_followups_for_job(database_path: Path, job_id: str, reason: str) -> int:
    with connect(database_path) as db:
        result = db.execute(
            """UPDATE application_followups SET state = 'cancelled', resolution = ?, updated_at = ?
               WHERE state = 'scheduled' AND request_id IN (
                   SELECT id FROM preparation_requests WHERE job_id = ?
               )""",
            (reason[:200], utc_now(), job_id),
        )
    return result.rowcount


def cancel_followups_for_closed_jobs(database_path: Path) -> int:
    """Drop reminders for roles that disappeared or are no longer active locally."""
    with connect(database_path) as db:
        result = db.execute(
            """UPDATE application_followups SET state = 'cancelled',
                      resolution = 'Listing is no longer active.', updated_at = ?
               WHERE state = 'scheduled' AND request_id IN (
                   SELECT request.id FROM preparation_requests AS request
                   LEFT JOIN jobs AS job ON job.id = request.job_id
                   WHERE job.id IS NULL OR job.is_active = 0
               )""",
            (utc_now(),),
        )
    return result.rowcount


def list_followups(
    database_path: Path,
    *,
    request_id: str | None = None,
    today: date | None = None,
) -> list[dict[str, Any]]:
    query = """SELECT followup.*, request.snapshot_json
               FROM application_followups AS followup
               JOIN preparation_requests AS request ON request.id = followup.request_id
               WHERE followup.state = 'scheduled'"""
    parameters: tuple[Any, ...] = ()
    if request_id:
        query += " AND followup.request_id = ?"
        parameters = (request_id,)
    query += " ORDER BY followup.due_on, followup.created_at"
    current_day = today or datetime.now().astimezone().date()
    with connect(database_path) as db:
        rows = db.execute(query, parameters).fetchall()
    reminders = []
    for row in rows:
        item = dict(row)
        item["snapshot"] = json.loads(item.pop("snapshot_json"))
        due = date.fromisoformat(item["due_on"])
        item["due"] = due <= current_day
        item["overdue"] = due < current_day
        reminders.append(item)
    return reminders
