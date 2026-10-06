"""Owner-reported application and interview outcomes, separate from Jev fit."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
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
RESOLVED_STAGES = ("offer", "rejected", "withdrawn", "no_response")


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
        occurred_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
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
                (json.dumps(details_data or {"owner_note": details[:2_000]}, ensure_ascii=False), evidence_level, occurred_at, existing["id"]),
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
                occurred_at,
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


def record_packet_feedback(
    database_path: Path,
    *,
    packet_id: str,
    owner_minutes: int,
    quality_rating: int,
    factual_corrections: int = 0,
    owner_note: str = "",
) -> str:
    """Save private owner estimates for one exact, approved packet version."""
    if not 0 <= owner_minutes <= 600:
        raise ValueError("Enter review and correction time from 0 to 600 minutes.")
    if not 1 <= quality_rating <= 5:
        raise ValueError("Rate packet usefulness from 1 to 5.")
    if not 0 <= factual_corrections <= 99:
        raise ValueError("Enter a factual correction count from 0 to 99.")
    owner_note = owner_note.strip()[:1_000]
    now = utc_now()
    with connect(database_path) as db:
        packet = db.execute(
            "SELECT status FROM preparation_packets WHERE id = ?", (packet_id,)
        ).fetchone()
        if packet is None or packet["status"] != "approved":
            raise ValueError("Approve the exact packet version before recording its review feedback.")
        existing = db.execute(
            "SELECT id FROM packet_feedback WHERE packet_id = ?", (packet_id,)
        ).fetchone()
        if existing:
            feedback_id = existing["id"]
            db.execute(
                """UPDATE packet_feedback SET owner_minutes = ?, quality_rating = ?,
                   factual_corrections = ?, owner_note = ?, updated_at = ? WHERE id = ?""",
                (owner_minutes, quality_rating, factual_corrections, owner_note, now, feedback_id),
            )
        else:
            feedback_id = uuid.uuid4().hex
            db.execute(
                """INSERT INTO packet_feedback
                   (id, packet_id, owner_minutes, quality_rating, factual_corrections,
                    owner_note, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    feedback_id,
                    packet_id,
                    owner_minutes,
                    quality_rating,
                    factual_corrections,
                    owner_note,
                    now,
                    now,
                ),
            )
    return feedback_id


def get_packet_feedback(database_path: Path, packet_id: str) -> dict[str, Any] | None:
    with connect(database_path) as db:
        row = db.execute(
            "SELECT * FROM packet_feedback WHERE packet_id = ?", (packet_id,)
        ).fetchone()
    return dict(row) if row else None


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
        applications = [
            row["job_id"]
            for row in db.execute("SELECT job_id FROM applications ORDER BY applied_at, job_id")
        ]
        latest = {}
        for row in db.execute(
            """SELECT job_id, stage FROM application_events
               WHERE event_type != 'receipt_imported'
               ORDER BY occurred_at DESC, created_at DESC, rowid DESC"""
        ):
            latest.setdefault(row["job_id"], row["stage"])
        packet_review_rows = [
            dict(row)
            for row in db.execute(
                """SELECT review.*, packet.revision, packet.request_id, request.snapshot_json
                   FROM packet_feedback AS review
                   JOIN preparation_packets AS packet ON packet.id = review.packet_id
                   JOIN preparation_requests AS request ON request.id = packet.request_id
                   ORDER BY review.updated_at DESC, review.id"""
            )
        ]
        packet_review_totals = db.execute(
            """SELECT COUNT(*) AS count, AVG(owner_minutes) AS average_minutes,
                      AVG(quality_rating) AS average_quality,
                      SUM(factual_corrections) AS factual_corrections
               FROM packet_feedback"""
        ).fetchone()

    resolved = {stage: 0 for stage in RESOLVED_STAGES}
    pending_count = 0
    for job_id in applications:
        stage = latest.get(job_id, "")
        if stage in resolved:
            resolved[stage] += 1
        else:
            pending_count += 1
    resolved_count = sum(resolved.values())
    outcomes = [
        {
            "stage": stage,
            "count": count,
            "share_percent": round(count * 100 / resolved_count, 1) if resolved_count else None,
        }
        for stage, count in resolved.items()
    ]
    for row in packet_review_rows:
        try:
            snapshot = json.loads(row.pop("snapshot_json"))
        except (json.JSONDecodeError, TypeError):
            snapshot = {}
        row["title"] = snapshot.get("title", "")
        row["company"] = snapshot.get("company", "")
    packet_review_count = packet_review_totals["count"] or 0
    preparation_quality = {
        "count": packet_review_count,
        "average_minutes": round(packet_review_totals["average_minutes"], 1)
        if packet_review_count
        else None,
        "average_quality": round(packet_review_totals["average_quality"], 1)
        if packet_review_count
        else None,
        "factual_corrections": packet_review_totals["factual_corrections"] or 0,
        "reviews": packet_review_rows,
    }
    return {
        "events": events,
        "feedback": feedback,
        "resolution": {
            "tracked_count": len(applications),
            "resolved_count": resolved_count,
            "pending_count": pending_count,
            "outcomes": outcomes,
        },
        "preparation_quality": preparation_quality,
    }
