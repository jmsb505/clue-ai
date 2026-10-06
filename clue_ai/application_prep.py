"""Private evidence sources and owner-triggered application-preparation records."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from clue_ai.config import Settings
from clue_ai.database import connect
from clue_ai.domain import utc_now
from clue_ai.resume import ResumeError, extract_resume_text

SOURCE_TYPES = {"technical_profile", "descriptive_profile", "resume", "writing_sample"}
EVIDENCE_LEVELS = {
    "unknown",
    "measured_result",
    "implemented",
    "demonstration",
    "coursework",
    "exposure",
    "planned",
}
CLAIM_STATUSES = {"unreviewed", "approved", "rejected"}
STRUCTURE_POLICIES = {"preserve", "allow_improvements"}


def add_source(
    database_path: Path,
    settings: Settings,
    filename: str,
    source_type: str,
    content: bytes,
    authorship_label: str = "unknown",
) -> dict[str, Any]:
    """Store one private source under the configured data directory."""
    if source_type not in SOURCE_TYPES:
        raise ValueError("Choose a supported source type.")
    if authorship_label not in {"unknown", "owner_written", "ai_assisted", "other"}:
        raise ValueError("Choose a supported source authorship label.")
    original_name = Path(filename).name[:200]
    suffix = Path(original_name).suffix.casefold()
    if suffix in {".pdf", ".docx"}:
        extracted = extract_resume_text(original_name, content, settings)
    elif suffix in {".md", ".markdown", ".txt"}:
        if len(content) > settings.max_cv_bytes:
            raise ResumeError("Source files must be 12 MB or smaller.")
        try:
            extracted = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ResumeError("Text and Markdown files must use UTF-8 encoding.") from exc
        extracted = _clean_text(extracted)[: settings.max_extracted_chars]
        if len(extracted.strip()) < 20:
            raise ResumeError("The selected file has too little readable text.")
    else:
        raise ResumeError("Use a PDF, DOCX, Markdown, or TXT file.")

    source_id = uuid.uuid4().hex
    source_dir = settings.cv_dir / "application-sources"
    source_dir.mkdir(parents=True, exist_ok=True)
    stored_path = source_dir / f"{source_id}{suffix}"
    content_hash = hashlib.sha256(content).hexdigest()
    stored_path.write_bytes(content)
    try:
        with connect(database_path) as db:
            db.execute(
                """INSERT INTO preparation_sources
                   (id, filename, source_type, file_path, extracted_text, content_sha256,
                    authorship_label, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source_id,
                    original_name,
                    source_type,
                    str(stored_path.resolve()),
                    extracted,
                    content_hash,
                    authorship_label,
                    utc_now(),
                ),
            )
    except Exception:
        stored_path.unlink(missing_ok=True)
        raise
    return get_source(database_path, source_id) or {}


def list_sources(database_path: Path) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT source.id, source.filename, source.source_type, source.content_sha256,
                      source.permitted, source.is_default_cv, source.structure_policy,
                      source.created_at, length(source.extracted_text) AS extracted_chars,
                      COUNT(claim.id) AS claim_count,
                      SUM(CASE WHEN claim.status = 'approved' THEN 1 ELSE 0 END) AS approved_count,
                      SUM(CASE WHEN claim.status = 'unreviewed' THEN 1 ELSE 0 END) AS pending_count
               FROM preparation_sources source
               LEFT JOIN candidate_claims claim ON claim.source_id = source.id
               GROUP BY source.id ORDER BY source.created_at DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def get_source(database_path: Path, source_id: str) -> dict[str, Any] | None:
    with connect(database_path) as db:
        row = db.execute(
            "SELECT * FROM preparation_sources WHERE id = ?", (source_id,)
        ).fetchone()
    return dict(row) if row else None


def set_source_options(
    database_path: Path,
    source_id: str,
    *,
    permitted: bool,
    default_cv: bool,
    structure_policy: str,
) -> bool:
    if structure_policy not in STRUCTURE_POLICIES:
        raise ValueError("Choose a supported CV structure policy.")
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            "SELECT source_type FROM preparation_sources WHERE id = ?", (source_id,)
        ).fetchone()
        if row is None:
            db.execute("ROLLBACK")
            return False
        is_resume = row["source_type"] == "resume"
        if default_cv and not is_resume:
            db.execute("ROLLBACK")
            raise ValueError("Only an uploaded resume can be the default CV.")
        if default_cv:
            db.execute("UPDATE preparation_sources SET is_default_cv = 0")
        db.execute(
            """UPDATE preparation_sources SET permitted = ?, is_default_cv = ?,
               structure_policy = ? WHERE id = ?""",
            (int(permitted), int(default_cv), structure_policy, source_id),
        )
        db.execute("COMMIT")
    return True


def suggest_claims(database_path: Path, source_id: str) -> int:
    """Create unreviewed, source-linked suggestions; never approve them automatically."""
    with connect(database_path) as db:
        source = db.execute(
            "SELECT extracted_text FROM preparation_sources WHERE id = ?", (source_id,)
        ).fetchone()
        if source is None:
            return 0
        lines = _claim_candidates(source["extracted_text"])
        now = utc_now()
        added = 0
        for line in lines:
            result = db.execute(
                """INSERT OR IGNORE INTO candidate_claims
                   (id, source_id, claim_text, evidence_excerpt, created_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (uuid.uuid4().hex, source_id, line, line, now),
            )
            added += result.rowcount
    return added


def list_claims(database_path: Path, source_id: str | None = None) -> list[dict[str, Any]]:
    query = """SELECT claim.*, source.filename, source.source_type
               FROM candidate_claims claim
               JOIN preparation_sources source ON source.id = claim.source_id"""
    params: tuple[str, ...] = ()
    if source_id:
        query += " WHERE claim.source_id = ?"
        params = (source_id,)
    query += (
        " ORDER BY CASE claim.status WHEN 'unreviewed' THEN 0 ELSE 1 END, "
        "source.created_at DESC, claim.created_at, claim.id"
    )
    with connect(database_path) as db:
        rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def review_claim(
    database_path: Path,
    claim_id: str,
    *,
    status: str,
    evidence_level: str,
    category: str,
    role_family: str,
    owner_note: str,
) -> bool:
    if status not in CLAIM_STATUSES or evidence_level not in EVIDENCE_LEVELS:
        raise ValueError("Choose a supported review status and evidence level.")
    reviewed_at = utc_now() if status != "unreviewed" else ""
    with connect(database_path) as db:
        source = db.execute(
            """SELECT source.source_type FROM candidate_claims claim
               JOIN preparation_sources source ON source.id = claim.source_id
               WHERE claim.id = ?""",
            (claim_id,),
        ).fetchone()
        if status == "approved" and source and source["source_type"] not in {"technical_profile", "resume"}:
            raise ValueError("Only a technical profile or resume can support an approved factual claim.")
        result = db.execute(
            """UPDATE candidate_claims SET status = ?, evidence_level = ?, category = ?,
               role_family = ?, owner_note = ?, reviewed_at = ? WHERE id = ?""",
            (
                status,
                evidence_level,
                category.strip()[:80] or "unclassified",
                role_family.strip()[:80],
                owner_note.strip()[:1_000],
                reviewed_at,
                claim_id,
            ),
        )
    return result.rowcount == 1


def approved_claims(
    database_path: Path,
    role_family: str = "",
    selected_cv_id: str = "",
) -> list[dict[str, Any]]:
    """Return only owner-approved claims and their source references."""
    query = """SELECT claim.id, claim.claim_text, claim.evidence_excerpt, claim.category,
                      claim.role_family, claim.evidence_level, claim.owner_note,
                      source.filename, source.source_type, source.content_sha256
               FROM candidate_claims claim
               JOIN preparation_sources source ON source.id = claim.source_id
               WHERE claim.status = 'approved' AND source.permitted = 1
                 AND source.source_type IN ('technical_profile', 'resume')"""
    params: tuple[str, ...] = ()
    if selected_cv_id:
        query += " AND (source.source_type = 'technical_profile' OR (source.source_type = 'resume' AND source.id = ?))"
        params = (selected_cv_id,)
    if role_family:
        query += " AND (claim.role_family = '' OR claim.role_family = ?)"
        params = (*params, role_family)
    query += " ORDER BY claim.category, claim.id"
    with connect(database_path) as db:
        rows = db.execute(query, params).fetchall()
    return [dict(row) for row in rows]


def selected_writing_sources(database_path: Path) -> list[dict[str, Any]]:
    """Return up to three explicitly permitted descriptive/style references."""
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT id, filename, source_type, file_path, content_sha256, authorship_label,
                      extracted_text
               FROM preparation_sources
               WHERE permitted = 1 AND source_type IN ('descriptive_profile', 'writing_sample')
               ORDER BY created_at DESC, id LIMIT 3"""
        ).fetchall()
    return [dict(row) for row in rows]


def contact_suppression_key(name: str, source_url: str, public_email: str = "") -> str:
    email = str(public_email or "").strip().casefold()
    host = (urlsplit(source_url).hostname or "").casefold()
    identity = email or f"{str(name or '').strip().casefold()}|{host}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def suppress_researched_contact(
    database_path: Path,
    request_id: str,
    contact_id: str,
) -> bool:
    """Exclude a contact from this and future Clue-generated packets."""
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        request = db.execute(
            "SELECT state FROM preparation_requests WHERE id = ?", (request_id,)
        ).fetchone()
        contact = db.execute(
            """SELECT name, source_url, public_email FROM researched_contacts
               WHERE id = ? AND request_id = ?""",
            (contact_id, request_id),
        ).fetchone()
        if request is None or contact is None or request["state"] not in {"review", "completed"}:
            db.execute("ROLLBACK")
            return False
        suppression_key = contact_suppression_key(
            contact["name"], contact["source_url"], contact["public_email"]
        )
        db.execute(
            "INSERT OR IGNORE INTO contact_suppressions (suppression_key, created_at) VALUES (?, ?)",
            (suppression_key, utc_now()),
        )
        db.execute(
            "UPDATE researched_contacts SET suppressed = 1 WHERE id = ?", (contact_id,)
        )
        db.execute(
            "UPDATE preparation_packets SET status = 'obsolete' WHERE request_id = ? AND status IN ('review', 'approved')",
            (request_id,),
        )
        db.execute(
            """UPDATE preparation_requests SET state = 'blocked', status_message = ?, updated_at = ?
               WHERE id = ?""",
            (
                "You excluded this contact. The prior packet was invalidated; manually retry to prepare without them.",
                utc_now(),
                request_id,
            ),
        )
        db.execute("COMMIT")
    return True


def get_writing_preferences(database_path: Path) -> dict[str, Any]:
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM writing_preferences WHERE id = 1").fetchone()
    return dict(row) if row else {"content": "", "revision": 0, "updated_at": ""}


def save_writing_preferences(database_path: Path, content: str) -> dict[str, Any]:
    value = _clean_text(content)[:4_000]
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute("SELECT revision FROM writing_preferences WHERE id = 1").fetchone()
        revision = int(previous["revision"] if previous else 0) + 1
        db.execute(
            """INSERT INTO writing_preferences (id, content, revision, updated_at)
               VALUES (1, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET content=excluded.content,
                 revision=excluded.revision, updated_at=excluded.updated_at""",
            (value, revision, utc_now()),
        )
        db.execute("COMMIT")
    return get_writing_preferences(database_path)


def request_preparation(
    database_path: Path,
    job_id: str,
    run_id: str,
    selected_cv_id: str = "",
) -> tuple[dict[str, Any], bool]:
    """Create one idempotent queue item for a Jev match in a specific saved search run."""
    from clue_ai.applications import not_applied_sql

    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            f"""SELECT j.id, j.title, j.company, j.description, j.location_raw,
                       j.workplace_type, j.employment_type, j.salary_min, j.salary_max,
                       j.salary_currency, j.salary_period, j.posted_at, j.valid_through,
                       j.eligibility_status, j.eligibility_evidence, j.canonical_url,
                       r.run_id, r.rank, r.score_state, r.filter_status, r.eligibility_status AS jev_eligibility_status,
                       r.eligibility_evidence AS jev_eligibility_evidence, r.combined_score,
                       r.confidence, r.dimensions_json, r.evidence_json, r.rubric_version,
                       run.created_at AS search_created_at
                FROM jobs j
                JOIN search_results r ON r.job_id = j.id AND r.run_id = ?
                JOIN search_runs run ON run.id = r.run_id
                LEFT JOIN job_user_state user_state ON user_state.job_id = j.id
                WHERE j.id = ? AND run.status = 'complete' AND j.is_active = 1
                  AND COALESCE(user_state.hidden, 0) = 0
                  AND r.score_state = 'scored' AND r.filter_status = 'match'
                  AND {not_applied_sql('j')}
                LIMIT 1""",
            (run_id, job_id),
        ).fetchone()
        if row is None:
            db.execute("ROLLBACK")
            raise ValueError(
                "Preparation is available only for an active, visible, unapplied listing "
                "with a completed Jev match in the selected search run."
            )
        sources = db.execute(
            "SELECT source_url FROM job_sources WHERE job_id = ? ORDER BY id", (job_id,)
        ).fetchall()
        snapshot = dict(row)
        snapshot["source_urls"] = [item["source_url"] for item in sources]
        source_rows = db.execute(
            """SELECT id, filename, source_type, content_sha256, extracted_text,
                      is_default_cv, structure_policy
               FROM preparation_sources WHERE permitted = 1
               ORDER BY created_at DESC"""
        ).fetchall()
        permitted_cv = [item for item in source_rows if item["source_type"] == "resume"]
        if not selected_cv_id:
            defaults = [item for item in permitted_cv if item["is_default_cv"]]
            if defaults:
                selected_cv_id = defaults[0]["id"]
            elif len(permitted_cv) == 1:
                selected_cv_id = permitted_cv[0]["id"]
        selected_cv = next(
            (item for item in permitted_cv if item["id"] == selected_cv_id), None
        )
        if selected_cv is None:
            db.execute("ROLLBACK")
            raise ValueError("Select one permitted CV reference before preparing this listing.")
        approved = db.execute(
            """SELECT claim.id, claim.claim_text, claim.evidence_excerpt, claim.category,
                      claim.role_family, claim.evidence_level, claim.owner_note,
                      source.content_sha256
               FROM candidate_claims claim
               JOIN preparation_sources source ON source.id = claim.source_id
               WHERE claim.status = 'approved' AND source.permitted = 1
                 AND (source.source_type = 'technical_profile' OR
                      (source.source_type = 'resume' AND source.id = ?))
               ORDER BY claim.category, claim.id""",
            (selected_cv["id"],),
        ).fetchall()
        if not approved:
            db.execute("ROLLBACK")
            raise ValueError("Approve at least one supported claim from a selected evidence source first.")
        preferences = db.execute(
            "SELECT content, revision FROM writing_preferences WHERE id = 1"
        ).fetchone()
        preference_content = str(preferences["content"] if preferences else "")
        preference_revision = int(preferences["revision"] if preferences else 0)
        claims_digest = hashlib.sha256(
            json.dumps([dict(item) for item in approved], sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        writing_sources = [
            {
                key: item[key]
                for key in ("id", "filename", "source_type", "content_sha256", "authorship_label")
            }
            for item in db.execute(
                """SELECT id, filename, source_type, content_sha256, authorship_label
                   FROM preparation_sources
                   WHERE permitted = 1 AND source_type IN ('descriptive_profile', 'writing_sample')
                   ORDER BY created_at DESC, id LIMIT 3"""
            ).fetchall()
        ]
        writing_sources_digest = hashlib.sha256(
            json.dumps(writing_sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        snapshot["inputs"] = {
            "selected_cv_id": selected_cv["id"],
            "selected_cv_filename": selected_cv["filename"],
            "selected_cv_sha256": selected_cv["content_sha256"],
            "structure_policy": selected_cv["structure_policy"],
            "approved_claims_sha256": claims_digest,
            "approved_claim_ids": [item["id"] for item in approved],
            "writing_sources": writing_sources,
            "writing_sources_sha256": writing_sources_digest,
            "writing_preferences_revision": preference_revision,
            "writing_preferences_sha256": hashlib.sha256(
                preference_content.encode("utf-8")
            ).hexdigest(),
        }
        snapshot_json = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        snapshot_hash = hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest()
        existing = db.execute(
            """SELECT * FROM preparation_requests WHERE job_id = ? AND snapshot_sha256 = ?
               ORDER BY attempt_no DESC LIMIT 1""",
            (job_id, snapshot_hash),
        ).fetchone()
        if existing and existing["state"] in {
            "requested", "researching", "generating", "review"
        }:
            db.execute("COMMIT")
            return dict(existing), False
        if existing:
            unresolved = db.execute(
                """SELECT 1 FROM openai_usage WHERE request_id = ?
                   AND status IN ('reserved', 'unknown') LIMIT 1""",
                (existing["id"],),
            ).fetchone()
            if unresolved:
                db.execute("ROLLBACK")
                raise ValueError(
                    "A previous API charge for this request is unresolved. Review usage before retrying."
                )
        attempt_no = int(existing["attempt_no"]) + 1 if existing else 1
        now = utc_now()
        request_id = uuid.uuid4().hex
        db.execute(
            """INSERT INTO preparation_requests
               (id, job_id, run_id, snapshot_json, snapshot_sha256, attempt_no, state,
                status_message, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, 'requested', ?, ?, ?)""",
            (
                request_id,
                job_id,
                run_id,
                snapshot_json,
                snapshot_hash,
                attempt_no,
                "Owner-triggered preparation is queued. No research or generation has started yet.",
                now,
                now,
            ),
        )
        created = db.execute(
            "SELECT * FROM preparation_requests WHERE id = ?", (request_id,)
        ).fetchone()
        db.execute("COMMIT")
    return dict(created), True


def retry_preparation(database_path: Path, request_id: str) -> tuple[dict[str, Any], bool]:
    """Create a new owner-triggered attempt for the same immutable job and inputs."""
    with connect(database_path) as db:
        prior = db.execute(
            "SELECT * FROM preparation_requests WHERE id = ?", (request_id,)
        ).fetchone()
        if prior is None:
            raise ValueError("Preparation request was not found.")
        if prior["state"] not in {"blocked", "failed", "cancelled"}:
            raise ValueError("Only a blocked, failed, or cancelled request can be retried.")
        unresolved = db.execute(
            """SELECT 1 FROM openai_usage WHERE request_id = ?
               AND status IN ('reserved', 'unknown') LIMIT 1""",
            (request_id,),
        ).fetchone()
        if unresolved:
            raise ValueError("A previous API charge is unresolved. Reconcile usage before retrying.")
        snapshot = json.loads(prior["snapshot_json"])
        job_id = prior["job_id"]
        run_id = prior["run_id"]
        cv_id = snapshot.get("inputs", {}).get("selected_cv_id", "")
    created, is_new = request_preparation(database_path, job_id, run_id, cv_id)
    if is_new:
        return created, True
    with connect(database_path) as db:
        row = db.execute(
            "SELECT * FROM preparation_requests WHERE id = ?", (created["id"],)
        ).fetchone()
    return dict(row), False


def list_preparations(database_path: Path) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT id, job_id, run_id, snapshot_json, snapshot_sha256, state,
                      status_message, created_at, updated_at,
                      (SELECT event.stage FROM application_events event
                       WHERE event.request_id = preparation_requests.id
                         AND event.event_type IN ('owner_submission_attestation', 'owner_stage_update')
                       ORDER BY event.occurred_at DESC, event.id DESC LIMIT 1) AS application_stage
               FROM preparation_requests ORDER BY updated_at DESC, created_at DESC"""
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["snapshot"] = json.loads(item["snapshot_json"])
        result.append(item)
    return result


def get_preparation(database_path: Path, request_id: str) -> dict[str, Any] | None:
    with connect(database_path) as db:
        row = db.execute(
            "SELECT * FROM preparation_requests WHERE id = ?", (request_id,)
        ).fetchone()
        stage = db.execute(
            """SELECT stage FROM application_events
               WHERE request_id = ?
                 AND event_type IN ('owner_submission_attestation', 'owner_stage_update')
               ORDER BY occurred_at DESC, id DESC LIMIT 1""",
            (request_id,),
        ).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["snapshot"] = json.loads(result["snapshot_json"])
    result["application_stage"] = stage["stage"] if stage else ""
    return result


def _claim_candidates(source_text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for raw_line in source_text.splitlines():
        line = re.sub(r"^\s*(?:[-*•▪◦]+|\d+[.)])\s*", "", raw_line).strip()
        line = " ".join(line.split())
        if len(line) < 25 or len(line) > 600 or line.endswith(":"):
            continue
        normalized = line.casefold()
        if normalized not in seen:
            candidates.append(line)
            seen.add(normalized)
    if not candidates:
        for paragraph in re.split(r"\n\s*\n", source_text):
            line = " ".join(paragraph.split())
            if 25 <= len(line) <= 600 and line.casefold() not in seen:
                candidates.append(line)
                seen.add(line.casefold())
    return candidates[:500]


def _clean_text(value: str) -> str:
    return "".join(
        character if character in "\n\r\t" or ord(character) >= 32 else " "
        for character in value
    )
