from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from clue_ai.company_catalog import GROUP_LABELS, ROLE_LABELS
from clue_ai.crawl_policy import (
    QUERY_ERROR_RETRY_SECONDS,
    SOURCE_ERROR_RETRY_SECONDS,
    TRANSIENT_COMPANY_ERROR_STATES,
)
from clue_ai.database import connect
from clue_ai.domain import NormalizedJob, utc_now
from clue_ai.jobs import canonical_url, job_fingerprint, stable_job_id


def list_companies(database_path: Path) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT id, name, homepage_url, careers_url, board_url, provider, group_id,
                      role_tags_json, discovery_source, discovery_url, tracked, board_state,
                      last_checked_at, last_state, last_error, listing_count
               FROM companies ORDER BY name COLLATE NOCASE"""
        ).fetchall()
    companies = []
    for row in rows:
        company = dict(row)
        try:
            company["role_tags"] = json.loads(company.pop("role_tags_json") or "[]")
        except json.JSONDecodeError:
            company["role_tags"] = []
        company["group_label"] = GROUP_LABELS.get(company["group_id"], "Other")
        company["role_labels"] = [
            ROLE_LABELS[tag] for tag in company["role_tags"] if tag in ROLE_LABELS
        ]
        companies.append(company)
    return companies


def set_company_tracked(database_path: Path, company_id: str, tracked: bool) -> bool:
    with connect(database_path) as db:
        cursor = db.execute(
            """UPDATE companies SET tracked = ?,
               board_state = CASE
                 WHEN ? = 0 AND board_state != 'blocked' THEN 'paused'
                 WHEN ? = 1 AND board_state = 'paused' THEN 'candidate'
                 ELSE board_state END
               WHERE id = ?""",
            (int(tracked), int(tracked), int(tracked), company_id),
        )
    return cursor.rowcount == 1


def companies_due(
    database_path: Path,
    *,
    interval_seconds: int = 21_600,
    limit: int = 100,
    force: bool = False,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT * FROM companies WHERE tracked = 1 AND board_state NOT IN ('blocked', 'paused')
               ORDER BY CASE WHEN last_checked_at = '' THEN 0 ELSE 1 END,
                        last_checked_at, name COLLATE NOCASE LIMIT ?""",
            (max(1, min(int(limit), 100)),),
        ).fetchall()
    due = []
    for row in rows:
        company = dict(row)
        checked = _parse_time(company.get("last_checked_at"))
        last_state = str(company.get("last_state") or "")
        transient_error = last_state in TRANSIENT_COMPANY_ERROR_STATES or bool(
            re.fullmatch(r"http_5\d{2}", last_state)
        )
        refresh_interval = (
            SOURCE_ERROR_RETRY_SECONDS
            if transient_error
            else max(3_600, interval_seconds)
        )
        if (
            force
            or checked is None
            or now - checked >= timedelta(seconds=refresh_interval)
        ):
            try:
                company["role_tags"] = json.loads(company.pop("role_tags_json") or "[]")
            except json.JSONDecodeError:
                company["role_tags"] = []
            due.append(company)
    return due


def update_company_board(
    database_path: Path,
    company_id: str,
    *,
    board_state: str,
    last_state: str,
    careers_url: str = "",
    board_url: str = "",
    provider: str = "",
    error: str = "",
    listing_count: int = 0,
    checked_at: str | None = None,
) -> bool:
    allowed_states = {
        "candidate",
        "resolved",
        "checked",
        "stale",
        "paused",
        "unavailable",
        "blocked",
    }
    if board_state not in allowed_states:
        raise ValueError("Unsupported company board state.")
    safe_error = re.sub(r"[\r\n\t]+", " ", str(error))[:240]
    checked = checked_at or utc_now()
    endpoint = board_url or careers_url
    with connect(database_path) as db:
        cursor = db.execute(
            """UPDATE companies SET board_state = ?, last_checked_at = ?, last_state = ?,
               careers_url = CASE WHEN ? != '' THEN ? ELSE careers_url END,
               board_url = CASE WHEN ? != '' THEN ? ELSE board_url END,
               provider = CASE WHEN ? != '' THEN ? ELSE provider END,
               last_error = ?, listing_count = ? WHERE id = ?""",
            (
                board_state,
                checked,
                last_state[:32],
                careers_url,
                careers_url,
                board_url,
                board_url,
                provider,
                provider,
                safe_error,
                max(0, int(listing_count)),
                company_id,
            ),
        )
        if cursor.rowcount == 1:
            db.execute(
                """UPDATE sources SET endpoint = CASE WHEN ? != '' THEN ? ELSE endpoint END,
                   last_checked_at = ?, last_state = ?, last_error = ? WHERE id = ?""",
                (
                    endpoint,
                    endpoint,
                    checked,
                    last_state[:32],
                    safe_error,
                    f"company-{company_id}",
                ),
            )
    return cursor.rowcount == 1


def retry_company_board(database_path: Path, company_id: str) -> bool:
    with connect(database_path) as db:
        cursor = db.execute(
            """UPDATE companies SET board_state = 'candidate', last_checked_at = '',
               last_state = 'never', last_error = ''
               WHERE id = ? AND tracked = 1 AND board_state = 'blocked'""",
            (company_id,),
        )
    return cursor.rowcount == 1


def list_sources(database_path: Path) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT id, name, kind, endpoint, state, enabled, attribution,
                      interval_seconds, retention_days, policy_note, config_json,
                      is_builtin, last_checked_at, last_state, last_error
               FROM sources WHERE kind != 'company_board'
               ORDER BY is_builtin DESC, name COLLATE NOCASE"""
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        try:
            item["config"] = json.loads(item.pop("config_json") or "{}")
        except json.JSONDecodeError:
            item["config"] = {}
        result.append(item)
    return result


def get_source(database_path: Path, source_id: str) -> dict[str, Any] | None:
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    if not row:
        return None
    item = dict(row)
    try:
        item["config"] = json.loads(item.pop("config_json") or "{}")
    except json.JSONDecodeError:
        item["config"] = {}
    return item


def sources_due(database_path: Path, force: bool = False) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    due: list[dict[str, Any]] = []
    for source in list_sources(database_path):
        if source["state"] != "approved" or not source["enabled"]:
            continue
        if source["kind"] in {"manual_x", "manual_board"}:
            continue
        if source["kind"] in {"remote_first_rss", "remotejobs_api"}:
            # These sources track refreshes per requested role/query, not per source endpoint.
            if source["kind"] == "remote_first_rss":
                source["endpoint"] = "https://remotefirstjobs.com/rss/jobs/{role_slug}.rss"
            due.append(source)
            continue
        checked = _parse_time(source.get("last_checked_at"))
        interval = (
            SOURCE_ERROR_RETRY_SECONDS
            if source.get("last_state") == "error"
            else max(3_600, int(source.get("interval_seconds") or 21_600))
        )
        if force or checked is None or now - checked >= timedelta(seconds=interval):
            due.append(source)
    return due


def role_feed_due(
    database_path: Path, source_id: str, role_slug: str, interval_seconds: int
) -> bool:
    query_hash = hashlib.sha256(role_slug.encode("utf-8")).hexdigest()
    with connect(database_path) as db:
        row = db.execute(
            "SELECT checked_at, state FROM source_query_checks WHERE source_id = ? AND query_hash = ?",
            (source_id, query_hash),
        ).fetchone()
    checked = _parse_time(row["checked_at"]) if row else None
    effective_interval = (
        QUERY_ERROR_RETRY_SECONDS
        if row and row["state"] == "error"
        else max(3_600, int(interval_seconds))
    )
    return checked is None or datetime.now(timezone.utc) - checked >= timedelta(
        seconds=effective_interval
    )


def record_role_feed_check(
    database_path: Path,
    source_id: str,
    role_slug: str,
    checked_at: str | None = None,
    *,
    state: str = "ok",
) -> None:
    query_hash = hashlib.sha256(role_slug.encode("utf-8")).hexdigest()
    with connect(database_path) as db:
        db.execute(
            """INSERT INTO source_query_checks (source_id, query_hash, checked_at, state)
               VALUES (?, ?, ?, ?) ON CONFLICT(source_id, query_hash)
               DO UPDATE SET checked_at = excluded.checked_at, state = excluded.state""",
            (source_id, query_hash, checked_at or utc_now(), state[:16]),
        )


def record_source_state(
    database_path: Path,
    source_id: str,
    state: str,
    message: str = "",
    checked_at: str | None = None,
) -> None:
    checked = checked_at or utc_now()
    # Keep remote error text short and avoid storing response bodies or credentials.
    safe_message = re.sub(r"[\r\n\t]+", " ", str(message))[:240]
    with connect(database_path) as db:
        if state == "blocked":
            db.execute(
                """UPDATE sources SET state = 'blocked', enabled = 0, last_checked_at = ?,
                   last_state = 'blocked', last_error = ? WHERE id = ?""",
                (checked, safe_message or "Source returned a block response.", source_id),
            )
        elif state == "error":
            db.execute(
                """UPDATE sources SET last_checked_at = ?, last_state = 'error', last_error = ?
                   WHERE id = ?""",
                (checked, safe_message, source_id),
            )
        else:
            db.execute(
                """UPDATE sources SET last_checked_at = ?, last_state = ?, last_error = ?
                   WHERE id = ?""",
                (checked, state[:32], safe_message if state == "error" else "", source_id),
            )


def add_source(
    database_path: Path,
    *,
    name: str,
    kind: str,
    endpoint: str,
    config: dict[str, Any],
    attribution: str,
    interval_seconds: int = 21_600,
    retention_days: int = 30,
) -> str:
    source_id = f"user-{uuid.uuid4().hex[:12]}"
    with connect(database_path) as db:
        db.execute(
            """INSERT INTO sources
               (id, name, kind, endpoint, state, enabled, attribution, interval_seconds,
                retention_days, policy_note, config_json, is_builtin)
               VALUES (?, ?, ?, ?, 'approved', 1, ?, ?, ?, ?, ?, 0)""",
            (
                source_id,
                name.strip()[:120],
                kind,
                endpoint,
                attribution.strip()[:120],
                max(3_600, min(int(interval_seconds), 30 * 86_400)),
                max(1, min(int(retention_days), 90)),
                "Owner-added public source. Automatically enabled for local job discovery; pause it anytime from Sources.",
                json.dumps(config, ensure_ascii=False),
            ),
        )
    return source_id


def set_source_enabled(database_path: Path, source_id: str, enabled: bool) -> None:
    with connect(database_path) as db:
        if enabled:
            db.execute(
                """UPDATE sources SET state = 'approved', enabled = 1, last_error = ''
                   WHERE id = ? AND state IN ('review', 'approved') AND kind != 'manual_x'""",
                (source_id,),
            )
        else:
            db.execute("UPDATE sources SET enabled = 0 WHERE id = ?", (source_id,))


def mark_source_for_review(database_path: Path, source_id: str) -> None:
    with connect(database_path) as db:
        db.execute(
            """UPDATE sources SET state = CASE WHEN is_builtin = 0 THEN 'review' ELSE state END,
               enabled = 0 WHERE id = ? AND state != 'blocked'""",
            (source_id,),
        )


def remove_user_source(database_path: Path, source_id: str) -> None:
    with connect(database_path) as db:
        db.execute(
            "DELETE FROM sources WHERE id = ? AND is_builtin = 0",
            (source_id,),
        )
        db.execute(
            """DELETE FROM jobs WHERE NOT EXISTS
               (SELECT 1 FROM job_sources WHERE job_sources.job_id = jobs.id)"""
        )


def claim_scoring_run(database_path: Path, run_id: str) -> bool:
    with connect(database_path) as db:
        cursor = db.execute(
            """UPDATE search_runs SET status = 'queued', stage = 'jev-queued',
               message = 'Jev scoring is queued.'
               WHERE id = ? AND status NOT IN ('queued', 'running', 'scoring')""",
            (run_id,),
        )
    return cursor.rowcount == 1


def update_run(
    database_path: Path,
    run_id: str,
    *,
    status: str | None = None,
    stage: str | None = None,
    message: str | None = None,
    checked_sources: list[str] | None = None,
    found_count: int | None = None,
    matched_count: int | None = None,
    scored_count: int | None = None,
    error: str | None = None,
    completed: bool = False,
) -> None:
    changes: dict[str, Any] = {}
    for key, value in {
        "status": status,
        "stage": stage,
        "message": message,
        "checked_sources_json": json.dumps(checked_sources)
        if checked_sources is not None
        else None,
        "found_count": found_count,
        "matched_count": matched_count,
        "scored_count": scored_count,
        "error": error,
    }.items():
        if value is not None:
            changes[key] = value
    if completed:
        changes["completed_at"] = utc_now()
    if not changes:
        return
    setters = ", ".join(f"{key} = ?" for key in changes)
    with connect(database_path) as db:
        db.execute(
            f"UPDATE search_runs SET {setters} WHERE id = ?",
            (*changes.values(), run_id),
        )


def get_run(database_path: Path, run_id: str) -> dict[str, Any] | None:
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM search_runs WHERE id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    run = dict(row)
    for field in ("criteria_json", "checked_sources_json"):
        try:
            run[field.removesuffix("_json")] = json.loads(run[field])
        except (TypeError, json.JSONDecodeError):
            run[field.removesuffix("_json")] = {}
    return run


def get_latest_run(database_path: Path) -> dict[str, Any] | None:
    with connect(database_path) as db:
        row = db.execute("SELECT id FROM search_runs ORDER BY created_at DESC LIMIT 1").fetchone()
    return get_run(database_path, row["id"]) if row else None


def has_active_runs(database_path: Path) -> bool:
    with connect(database_path) as db:
        row = db.execute(
            "SELECT 1 FROM search_runs WHERE status IN ('queued', 'running', 'scoring') LIMIT 1"
        ).fetchone()
    return row is not None


@dataclass(frozen=True)
class SaveJobsReport:
    saved: int
    deduplicated: int
    inserted: int


def save_jobs(database_path: Path, jobs: list[NormalizedJob]) -> int:
    return save_jobs_with_report(database_path, jobs).saved


def save_jobs_with_report(database_path: Path, jobs: list[NormalizedJob]) -> SaveJobsReport:
    now = utc_now()
    saved = 0
    deduplicated = 0
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        for job in jobs:
            url = canonical_url(job.canonical_url or job.source_url)
            source_url = canonical_url(job.source_url)
            context_url = canonical_url(job.context_url) if job.context_url else ""
            if not url or not source_url or not job.title.strip():
                continue
            fingerprint = (
                ""
                if job.source_id == "x_manual"
                else job_fingerprint(job.title, job.company, job.location_raw, job.posted_at)
            )
            row = db.execute(
                "SELECT id, canonical_url FROM jobs WHERE canonical_url = ?",
                (url,),
            ).fetchone()
            if row is None and job.external_id.strip():
                row = db.execute(
                    """SELECT job.id, job.canonical_url FROM job_sources source
                       JOIN jobs job ON job.id = source.job_id
                       WHERE source.source_id = ? AND source.external_id = ? LIMIT 1""",
                    (job.source_id, job.external_id.strip()),
                ).fetchone()
            job_id = row["id"] if row else stable_job_id(url)
            primary_url = row["canonical_url"] if row else url
            if row is not None:
                deduplicated += 1
            db.execute(
                """INSERT INTO jobs
                   (id, fingerprint, canonical_url, title, company, description, location_raw,
                    workplace_type, employment_type, visa_sponsorship, salary_min, salary_max, salary_currency,
                    salary_period, posted_at, valid_through, eligibility_status,
                    eligibility_evidence, first_seen_at, last_checked_at, is_active)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                   ON CONFLICT(id) DO UPDATE SET
                    fingerprint=CASE WHEN excluded.fingerprint != '' THEN excluded.fingerprint ELSE jobs.fingerprint END,
                    title=excluded.title,
                    company=CASE WHEN excluded.company != '' THEN excluded.company ELSE jobs.company END,
                    description=CASE WHEN excluded.description != '' THEN excluded.description ELSE jobs.description END,
                    location_raw=CASE WHEN excluded.location_raw != '' THEN excluded.location_raw ELSE jobs.location_raw END,
                    workplace_type=CASE WHEN excluded.workplace_type != 'unknown' THEN excluded.workplace_type ELSE jobs.workplace_type END,
                    employment_type=CASE WHEN excluded.employment_type != 'unknown' THEN excluded.employment_type ELSE jobs.employment_type END,
                    visa_sponsorship=CASE WHEN excluded.visa_sponsorship != 'unknown' THEN excluded.visa_sponsorship ELSE jobs.visa_sponsorship END,
                    salary_min=COALESCE(excluded.salary_min, jobs.salary_min),
                    salary_max=COALESCE(excluded.salary_max, jobs.salary_max),
                    salary_currency=CASE WHEN excluded.salary_currency != '' THEN excluded.salary_currency ELSE jobs.salary_currency END,
                    salary_period=CASE WHEN excluded.salary_period != '' THEN excluded.salary_period ELSE jobs.salary_period END,
                    posted_at=CASE WHEN excluded.posted_at != '' THEN excluded.posted_at ELSE jobs.posted_at END,
                    valid_through=CASE WHEN excluded.valid_through != '' THEN excluded.valid_through ELSE jobs.valid_through END,
                    eligibility_status=CASE WHEN excluded.eligibility_status != 'unknown' THEN excluded.eligibility_status ELSE jobs.eligibility_status END,
                    eligibility_evidence=CASE WHEN excluded.eligibility_evidence != '' THEN excluded.eligibility_evidence ELSE jobs.eligibility_evidence END,
                    last_checked_at=excluded.last_checked_at, is_active=1""",
                (
                    job_id,
                    fingerprint,
                    primary_url,
                    job.title.strip()[:300],
                    job.company.strip()[:250],
                    job.description[:20_000],
                    job.location_raw[:1_000],
                    job.workplace_type,
                    job.employment_type,
                    job.visa_sponsorship,
                    job.salary_min,
                    job.salary_max,
                    job.salary_currency[:8],
                    job.salary_period[:40],
                    job.posted_at,
                    job.valid_through,
                    job.eligibility_status,
                    job.eligibility_evidence[:1_000],
                    now,
                    job.last_checked_at or now,
                ),
            )
            db.execute(
                """INSERT INTO job_sources
                   (job_id, source_id, external_id, source_url, context_url, source_posted_at, last_seen_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(job_id, source_id) DO UPDATE SET
                    external_id=excluded.external_id, source_url=excluded.source_url,
                    context_url=excluded.context_url,
                    source_posted_at=excluded.source_posted_at, last_seen_at=excluded.last_seen_at""",
                (
                    job_id,
                    job.source_id,
                    job.external_id or job_id,
                    source_url,
                    context_url,
                    job.posted_at,
                    now,
                ),
            )
            saved += 1
        db.execute("COMMIT")
    return SaveJobsReport(
        saved=saved,
        deduplicated=deduplicated,
        inserted=saved - deduplicated,
    )


def save_run_results(
    database_path: Path,
    run_id: str,
    jobs: list[dict[str, Any]],
    score_state: str = "unscored",
    score_reason: str = "Fit not evaluated yet.",
) -> None:
    with connect(database_path) as db:
        db.execute("DELETE FROM search_results WHERE run_id = ?", (run_id,))
        for rank, job in enumerate(jobs, start=1):
            db.execute(
                """INSERT OR REPLACE INTO search_results
                   (run_id, job_id, rank, score_state, filter_status, score_reason,
                    eligibility_status, eligibility_evidence, freshness_status, freshness_age_days)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    job["id"],
                    rank,
                    score_state,
                    str(job.get("filter_status") or "unassessed"),
                    score_reason,
                    job.get("eligibility_status", "unknown"),
                    str(job.get("eligibility_evidence") or "")[:1_000],
                    job.get("freshness_status", "unknown"),
                    job.get("freshness_age_days"),
                ),
            )


def update_score(
    database_path: Path,
    run_id: str,
    job_id: str,
    *,
    score_state: str,
    score_reason: str = "",
    combined_score: float | None = None,
    confidence: float | None = None,
    dimensions: dict[str, Any] | None = None,
    evidence: list[str] | None = None,
    rubric_version: str = "",
    filter_status: str | None = None,
) -> None:
    with connect(database_path) as db:
        db.execute(
            """UPDATE search_results SET score_state = ?, score_reason = ?,
               combined_score = ?, confidence = ?, dimensions_json = ?, evidence_json = ?,
               rubric_version = ?, filter_status = COALESCE(?, filter_status)
               WHERE run_id = ? AND job_id = ?""",
            (
                score_state,
                score_reason[:300],
                combined_score,
                confidence,
                json.dumps(dimensions or {}),
                json.dumps(evidence or [], ensure_ascii=False),
                rubric_version[:40],
                filter_status,
                run_id,
                job_id,
            ),
        )


def update_filter_status(
    database_path: Path,
    run_id: str,
    job_id: str,
    filter_status: str,
) -> None:
    if filter_status not in {"match", "review", "conflict", "unassessed"}:
        raise ValueError("Unsupported Jev filter status.")
    with connect(database_path) as db:
        db.execute(
            "UPDATE search_results SET filter_status = ? WHERE run_id = ? AND job_id = ?",
            (filter_status, run_id, job_id),
        )


def get_run_result_counts(database_path: Path, run_id: str) -> dict[str, int]:
    with connect(database_path) as db:
        row = db.execute(
            """SELECT COUNT(*) AS total,
                       SUM(CASE WHEN score_state = 'scored' THEN 1 ELSE 0 END) AS scored,
                       SUM(CASE WHEN score_state != 'scored' THEN 1 ELSE 0 END) AS pending_scores,
                       SUM(CASE WHEN filter_status = 'match' THEN 1 ELSE 0 END) AS matches,
                       SUM(CASE WHEN filter_status = 'review' THEN 1 ELSE 0 END) AS review,
                       SUM(CASE WHEN filter_status = 'conflict' THEN 1 ELSE 0 END) AS conflicts,
                       SUM(CASE WHEN filter_status = 'unassessed' THEN 1 ELSE 0 END) AS unassessed
                 FROM search_results r
                 LEFT JOIN job_user_state u ON u.job_id = r.job_id
                 WHERE r.run_id = ? AND COALESCE(u.hidden, 0) = 0""",
            (run_id,),
        ).fetchone()
    return {key: int(value or 0) for key, value in dict(row).items()}


def get_run_results(
    database_path: Path,
    run_id: str,
    *,
    filter_status: str | None = None,
    limit: int | None = None,
    offset: int = 0,
) -> list[dict[str, Any]]:
    valid_statuses = {"match", "review", "conflict", "unassessed"}
    where = "WHERE r.run_id = ? AND COALESCE(u.hidden, 0) = 0"
    params: list[Any] = [run_id]
    if filter_status in valid_statuses:
        where += " AND r.filter_status = ?"
        params.append(filter_status)
    pagination = ""
    if limit is not None:
        pagination = " LIMIT ? OFFSET ?"
        params.extend((max(1, int(limit)), max(0, int(offset))))
    with connect(database_path) as db:
        rows = db.execute(
            f"""SELECT r.rank, r.score_state, r.filter_status, r.score_reason,
                      r.combined_score, r.confidence,
                      r.eligibility_status AS result_eligibility_status,
                      r.eligibility_evidence AS result_eligibility_evidence,
                      r.freshness_status, r.freshness_age_days,
                      r.dimensions_json, r.evidence_json, r.rubric_version,
                      j.id, j.title, j.company, j.description, j.location_raw, j.workplace_type,
                      j.employment_type, j.salary_min, j.salary_max, j.salary_currency,
                      j.salary_period, j.posted_at, j.valid_through, j.eligibility_status,
                      j.eligibility_evidence, j.first_seen_at, j.last_checked_at,
                      COALESCE(u.saved, 0) AS saved, COALESCE(u.hidden, 0) AS hidden
               FROM search_results r
               JOIN jobs j ON j.id = r.job_id
               LEFT JOIN job_user_state u ON u.job_id = j.id
               {where}
               ORDER BY
                 CASE r.filter_status WHEN 'match' THEN 0 WHEN 'review' THEN 1
                      WHEN 'conflict' THEN 2 ELSE 3 END,
                 CASE WHEN r.combined_score IS NULL THEN 1 ELSE 0 END,
                 r.combined_score DESC, r.rank ASC{pagination}""",
            params,
        ).fetchall()
        jobs = [dict(row) for row in rows]
        for job in jobs:
            job["eligibility_status"] = job.pop("result_eligibility_status")
            job["eligibility_evidence"] = job.pop("result_eligibility_evidence")
            sources = db.execute(
                """SELECT s.id, s.name, s.attribution, s.state, s.last_state,
                          s.last_checked_at AS source_checked_at, js.source_url, js.context_url,
                          js.source_posted_at, js.last_seen_at
                   FROM job_sources js JOIN sources s ON s.id = js.source_id
                   WHERE js.job_id = ? ORDER BY js.last_seen_at DESC""",
                (job["id"],),
            ).fetchall()
            job["sources"] = [dict(source) for source in sources]
            for field in ("dimensions_json", "evidence_json"):
                try:
                    job[field.removesuffix("_json")] = json.loads(job[field])
                except (TypeError, json.JSONDecodeError):
                    job[field.removesuffix("_json")] = {} if field == "dimensions_json" else []
    return jobs


def all_active_jobs(database_path: Path) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT j.*, s.id AS source_id, s.name AS source_name, s.attribution,
                      s.state AS source_state, s.last_state AS source_last_state,
                      s.last_checked_at AS source_checked_at,
                      js.source_url, js.context_url, js.source_posted_at,
                      COALESCE(u.hidden, 0) AS hidden, COALESCE(u.saved, 0) AS saved
               FROM jobs j
               JOIN job_sources js ON js.job_id = j.id
               JOIN sources s ON s.id = js.source_id
               LEFT JOIN job_user_state u ON u.job_id = j.id
               WHERE j.is_active = 1
               ORDER BY j.last_checked_at DESC"""
        ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        item = dict(row)
        entry = grouped.get(item["id"])
        link = {
            "id": item.pop("source_id"),
            "name": item.pop("source_name"),
            "attribution": item.pop("attribution"),
            "state": item.pop("source_state"),
            "last_state": item.pop("source_last_state"),
            "source_checked_at": item.pop("source_checked_at"),
            "source_url": item.pop("source_url"),
            "context_url": item.pop("context_url"),
            "source_posted_at": item.pop("source_posted_at"),
        }
        if entry is None:
            entry = item
            entry["sources"] = []
            grouped[entry["id"]] = entry
        entry["sources"].append(link)
    for entry in grouped.values():
        primary = entry["sources"][0]
        entry["source_id"] = primary["id"]
        entry["source_name"] = primary["name"]
        entry["attribution"] = primary["attribution"]
        entry["source_url"] = primary["source_url"]
        entry["source_posted_at"] = primary["source_posted_at"]
    return list(grouped.values())


def manual_x_leads(database_path: Path, limit: int = 100) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT j.id, j.title, j.company, j.location_raw, j.workplace_type,
                      j.description, j.canonical_url AS job_url, j.last_checked_at AS added_at,
                      js.context_url AS post_url, COALESCE(u.hidden, 0) AS hidden
               FROM job_sources js
               JOIN jobs j ON j.id = js.job_id
               LEFT JOIN job_user_state u ON u.job_id = j.id
               WHERE js.source_id = 'x_manual' AND j.is_active = 1
               ORDER BY js.last_seen_at DESC LIMIT ?""",
            (max(1, min(int(limit), 250)),),
        ).fetchall()
    return [dict(row) for row in rows]


def set_job_user_state(database_path: Path, job_id: str, action: str) -> None:
    if action not in {"saved", "hidden"}:
        raise ValueError("Unsupported job action.")
    other = "hidden" if action == "saved" else "saved"
    now = utc_now()
    with connect(database_path) as db:
        db.execute(
            f"""INSERT INTO job_user_state (job_id, {action}, {other}, updated_at)
                VALUES (?, 1, 0, ?)
                ON CONFLICT(job_id) DO UPDATE SET {action}=1, {other}=0, updated_at=excluded.updated_at""",
            (job_id, now),
        )


def clear_job_user_state(database_path: Path, job_id: str) -> None:
    with connect(database_path) as db:
        db.execute("DELETE FROM job_user_state WHERE job_id = ?", (job_id,))


def saved_jobs(database_path: Path) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT j.* FROM jobs j JOIN job_user_state u ON u.job_id = j.id
               WHERE u.saved = 1 ORDER BY u.updated_at DESC"""
        ).fetchall()
        result = [dict(row) for row in rows]
        for job in result:
            sources = db.execute(
                """SELECT s.name, s.attribution, s.state, s.last_state,
                          s.last_checked_at AS source_checked_at,
                          js.source_url, js.last_seen_at
                   FROM job_sources js JOIN sources s ON s.id = js.source_id
                   WHERE js.job_id = ? ORDER BY js.last_seen_at DESC""",
                (job["id"],),
            ).fetchall()
            job["sources"] = [dict(source) for source in sources]
    return result


def hidden_jobs(database_path: Path) -> list[dict[str, Any]]:
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT j.* FROM jobs j JOIN job_user_state u ON u.job_id = j.id
               WHERE u.hidden = 1 ORDER BY u.updated_at DESC"""
        ).fetchall()
        result = [dict(row) for row in rows]
        for job in result:
            sources = db.execute(
                """SELECT s.name, s.attribution, s.state, s.last_state,
                          s.last_checked_at AS source_checked_at,
                          js.source_url, js.last_seen_at
                   FROM job_sources js JOIN sources s ON s.id = js.source_id
                   WHERE js.job_id = ? ORDER BY js.last_seen_at DESC""",
                (job["id"],),
            ).fetchall()
            job["sources"] = [dict(source) for source in sources]
    return result


def prune_expired_data(database_path: Path) -> int:
    now = datetime.now(timezone.utc)
    with connect(database_path) as db:
        query_cutoff = (now - timedelta(days=30)).isoformat(timespec="seconds")
        db.execute("DELETE FROM source_query_checks WHERE checked_at < ?", (query_cutoff,))
        rules = db.execute("SELECT id, retention_days FROM sources").fetchall()
        deleted = 0
        for source in rules:
            cutoff = (now - timedelta(days=max(1, int(source["retention_days"])))).isoformat()
            result = db.execute(
                "DELETE FROM job_sources WHERE source_id = ? AND last_seen_at < ?",
                (source["id"], cutoff),
            )
            deleted += result.rowcount
        db.execute(
            """UPDATE jobs SET is_active = 0 WHERE valid_through != ''
               AND valid_through < ?""",
            (now.isoformat(),),
        )
        db.execute(
            """DELETE FROM jobs WHERE NOT EXISTS
               (SELECT 1 FROM job_sources WHERE job_sources.job_id = jobs.id)"""
        )
    return deleted


def reserve_jev_budget(
    database_path: Path,
    run_id: str,
    model: str,
    reserved_tokens: int,
    price_per_million: float,
    monthly_budget: float,
) -> tuple[int | None, float]:
    now = datetime.now(timezone.utc)
    month_key = now.strftime("%Y-%m")
    rolling_cutoff = (now - timedelta(days=30)).isoformat(timespec="seconds")
    reserve_usd = reserved_tokens * price_per_million / 1_000_000
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute(
            """SELECT COALESCE(SUM(CASE WHEN actual_usd IS NOT NULL
                    THEN actual_usd ELSE reserved_usd END), 0) AS used
               FROM jev_usage WHERE started_at >= ?""",
            (rolling_cutoff,),
        ).fetchone()
        used = float(row["used"] or 0.0)
        if used + reserve_usd > monthly_budget + 1e-12:
            db.execute("ROLLBACK")
            return None, max(0.0, monthly_budget - used)
        cursor = db.execute(
            """INSERT INTO jev_usage
               (run_id, month_key, model, started_at, reserved_tokens, reserved_usd, status)
               VALUES (?, ?, ?, ?, ?, ?, 'reserved')""",
            (
                run_id,
                month_key,
                model,
                now.isoformat(timespec="seconds"),
                reserved_tokens,
                reserve_usd,
            ),
        )
        db.execute("COMMIT")
        return int(cursor.lastrowid), max(0.0, monthly_budget - used - reserve_usd)


def settle_jev_usage(
    database_path: Path,
    usage_id: int,
    actual_tokens: int,
    price_per_million: float,
) -> None:
    actual_usd = max(0, int(actual_tokens)) * price_per_million / 1_000_000
    with connect(database_path) as db:
        db.execute(
            """UPDATE jev_usage SET actual_tokens = ?, actual_usd = ?, status = 'completed'
               WHERE id = ?""",
            (max(0, int(actual_tokens)), actual_usd, usage_id),
        )


def release_jev_reservation(database_path: Path, usage_id: int, code: str) -> None:
    with connect(database_path) as db:
        db.execute(
            """UPDATE jev_usage SET reserved_usd = 0, actual_usd = 0,
               status = 'not_charged', error_code = ? WHERE id = ?""",
            (code[:40], usage_id),
        )


def monthly_jev_usage(database_path: Path, monthly_budget: float) -> dict[str, float]:
    rolling_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
    with connect(database_path) as db:
        row = db.execute(
            """SELECT COALESCE(SUM(CASE WHEN actual_usd IS NOT NULL
                    THEN actual_usd ELSE reserved_usd END), 0) AS used,
                      COUNT(*) AS requests
               FROM jev_usage WHERE started_at >= ?""",
            (rolling_cutoff,),
        ).fetchone()
    used = float(row["used"] or 0.0)
    return {
        "used_usd": used,
        "remaining_usd": max(0.0, monthly_budget - used),
        "budget_usd": monthly_budget,
        "requests": int(row["requests"] or 0),
    }


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return (
        parsed.replace(tzinfo=timezone.utc)
        if parsed.tzinfo is None
        else parsed.astimezone(timezone.utc)
    )
