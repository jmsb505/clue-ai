"""Owner-reported application and interview outcomes, separate from Jev fit."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from clue_ai.database import connect
from clue_ai.domain import utc_now

APPLICATION_STAGES = {
    "submitted",
    "screen",
    "technical",
    "final",
    "offer",
    "rejected",
    "withdrawn",
    "no_response",
}
INTERVIEW_STAGES = {"screen", "technical", "final"}


def record_stage(
    database_path: Path,
    *,
    job_id: str,
    request_id: str,
    stage: str,
    details: str = "",
    details_data: dict[str, Any] | None = None,
    evidence_level: str = "owner_reported",
    event_type: str = "",
) -> str:
    if stage not in APPLICATION_STAGES:
        raise ValueError("Choose a supported application stage.")
    if evidence_level not in {"owner_reported", "receipt_imported"}:
        raise ValueError("Choose a supported outcome evidence source.")
    event_type = event_type or ("owner_submission_attestation" if stage == "submitted" else "owner_stage_update")
    if event_type not in {"owner_submission_attestation", "owner_stage_update", "receipt_imported"}:
        raise ValueError("Choose a supported application event type.")
    with connect(database_path) as db:
        existing = None
        if event_type != "receipt_imported":
            existing = db.execute(
                """SELECT id FROM application_events
                   WHERE job_id = ? AND request_id = ? AND stage = ? AND event_type = ?
                   ORDER BY created_at DESC LIMIT 1""",
                (job_id, request_id, stage, event_type),
            ).fetchone()
        if existing:
            db.execute(
                "UPDATE application_events SET details_json = ?, evidence_level = ?, occurred_at = ? WHERE id = ?",
                (json.dumps(details_data or {"owner_note": details[:2_000]}, ensure_ascii=False), evidence_level, utc_now(), existing["id"]),
            )
            return existing["id"]
        event_id = uuid.uuid4().hex
        db.execute(
            """INSERT INTO application_events
               (id, job_id, request_id, event_type, stage, evidence_level,
                details_json, occurred_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event_id,
                job_id,
                request_id,
                event_type,
                stage,
                evidence_level,
                json.dumps(details_data or {"owner_note": details[:2_000]}, ensure_ascii=False),
                utc_now(),
                utc_now(),
            ),
        )
    return event_id


def record_interview_feedback(
    database_path: Path,
    *,
    job_id: str,
    request_id: str,
    stage: str,
    self_assessment: str,
    employer_feedback: str,
    gap_tags: list[str],
) -> str:
    if stage not in INTERVIEW_STAGES:
        raise ValueError("Choose screen, technical, or final interview stage.")
    own = self_assessment.strip()[:4_000]
    employer = employer_feedback.strip()[:4_000]
    tags = list(dict.fromkeys(value.strip()[:60] for value in gap_tags if value.strip()))[:12]
    feedback_id = uuid.uuid4().hex
    with connect(database_path) as db:
        db.execute(
            """INSERT INTO interview_feedback
               (id, job_id, request_id, stage, self_assessment, employer_feedback,
                gap_tags_json, occurred_at, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (feedback_id, job_id, request_id, stage, own, employer, json.dumps(tags), utc_now(), utc_now()),
        )
    return feedback_id


def outcome_summary(database_path: Path) -> dict[str, Any]:
    with connect(database_path) as db:
        events = [dict(row) for row in db.execute(
            """SELECT stage, evidence_level, COUNT(*) AS count
               FROM application_events GROUP BY stage, evidence_level ORDER BY stage"""
        ).fetchall()]
        feedback = [dict(row) for row in db.execute(
            """SELECT stage, COUNT(*) AS count,
                      SUM(CASE WHEN self_assessment != '' THEN 1 ELSE 0 END) AS self_reported,
                      SUM(CASE WHEN employer_feedback != '' THEN 1 ELSE 0 END) AS employer_reported
               FROM interview_feedback GROUP BY stage ORDER BY stage"""
        ).fetchall()]
    return {"events": events, "feedback": feedback}
