"""Durable records of applications made by the owner outside Clue."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from clue_ai.database import connect
from clue_ai.domain import utc_now
from clue_ai.jobs import canonical_url


def not_applied_sql(job_alias: str = "j") -> str:
    """Internal SQL predicate; callers supply a fixed SQL alias, never request input."""
    if job_alias not in {"j"}:
        raise ValueError("Unsupported job alias.")
    return f"""NOT EXISTS (
        SELECT 1 FROM applications a
        WHERE a.job_id = {job_alias}.id OR a.canonical_url = {job_alias}.canonical_url
        OR EXISTS (
            SELECT 1 FROM application_urls au
            WHERE au.application_id = a.job_id AND (
                au.url = {job_alias}.canonical_url OR EXISTS (
                    SELECT 1 FROM job_sources js
                    WHERE js.job_id = {job_alias}.id AND js.source_url = au.url
                )
            )
        )
    )"""


def mark_applied(database_path: Path, job_id: str) -> bool:
    """Snapshot a known vacancy. Repeated clicks keep the first recorded date."""
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job is None:
                db.execute("ROLLBACK")
                return False
            urls = {canonical_url(job["canonical_url"])}
            urls.update(
                canonical_url(row["source_url"])
                for row in db.execute(
                    "SELECT source_url FROM job_sources WHERE job_id = ?", (job_id,)
                )
            )
            urls.discard("")
            existing = db.execute(
                f"""SELECT a.job_id FROM applications a WHERE a.job_id = ?
                    OR a.canonical_url IN ({",".join("?" for _ in urls)})
                    OR EXISTS (SELECT 1 FROM application_urls au WHERE au.application_id = a.job_id
                               AND au.url IN ({",".join("?" for _ in urls)})) LIMIT 1""",
                (job_id, *sorted(urls), *sorted(urls)),
            ).fetchone()
            application_id = existing["job_id"] if existing else job_id
            if existing is None:
                db.execute(
                    """INSERT INTO applications
                       (job_id, canonical_url, title, company, location_raw, applied_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        job_id,
                        job["canonical_url"],
                        job["title"],
                        job["company"],
                        job["location_raw"],
                        utc_now(),
                    ),
                )
            db.executemany(
                "INSERT OR IGNORE INTO application_urls (application_id, url) VALUES (?, ?)",
                [(application_id, url) for url in sorted(urls)],
            )
            db.execute("COMMIT")
        except Exception:
            db.execute("ROLLBACK")
            raise
    return True


def mark_snapshot_applied(database_path: Path, snapshot: dict) -> str:
    """Record an owner attestation from a retained preparation after manual submission."""
    job_id = str(snapshot.get("id") or "")
    canonical = canonical_url(str(snapshot.get("canonical_url") or ""))
    urls = {canonical}
    urls.update(canonical_url(str(value)) for value in snapshot.get("source_urls", []))
    urls.discard("")
    if not job_id or not canonical or not urls:
        raise ValueError("The saved vacancy snapshot has no stable listing link.")
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing = db.execute(
            f"""SELECT a.job_id FROM applications a WHERE a.job_id = ?
                OR a.canonical_url IN ({','.join('?' for _ in urls)})
                OR EXISTS (SELECT 1 FROM application_urls au WHERE au.application_id = a.job_id
                           AND au.url IN ({','.join('?' for _ in urls)})) LIMIT 1""",
            (job_id, *sorted(urls), *sorted(urls)),
        ).fetchone()
        application_id = existing["job_id"] if existing else job_id
        if existing is None:
            db.execute(
                """INSERT INTO applications
                   (job_id, canonical_url, title, company, location_raw, applied_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (
                    application_id,
                    canonical,
                    str(snapshot.get("title") or "")[:300],
                    str(snapshot.get("company") or "")[:250],
                    str(snapshot.get("location_raw") or "")[:1_000],
                    utc_now(),
                ),
            )
        db.executemany(
            "INSERT OR IGNORE INTO application_urls (application_id, url) VALUES (?, ?)",
            [(application_id, value) for value in sorted(urls)],
        )
        db.execute("COMMIT")
    return application_id


def find_applied_snapshot(database_path: Path, snapshot: dict) -> str | None:
    """Resolve a prepared vacancy to its stable applied-tracker identity."""
    job_id = str(snapshot.get("id") or "")
    urls = {canonical_url(str(snapshot.get("canonical_url") or ""))}
    urls.update(canonical_url(str(value)) for value in snapshot.get("source_urls", []))
    urls.discard("")
    if not job_id or not urls:
        return None
    with connect(database_path) as db:
        row = db.execute(
            f"""SELECT application.job_id FROM applications AS application
                WHERE application.job_id = ?
                   OR application.canonical_url IN ({','.join('?' for _ in urls)})
                   OR EXISTS (
                       SELECT 1 FROM application_urls AS url
                       WHERE url.application_id = application.job_id
                         AND url.url IN ({','.join('?' for _ in urls)})
                   ) LIMIT 1""",
            (job_id, *sorted(urls), *sorted(urls)),
        ).fetchone()
    return row["job_id"] if row else None


def undo_applied(database_path: Path, application_id: str) -> bool:
    with connect(database_path) as db:
        cursor = db.execute("DELETE FROM applications WHERE job_id = ?", (application_id,))
    return cursor.rowcount > 0


def remember_applied_urls(
    db: sqlite3.Connection, job_id: str, canonical: str, source_url: str
) -> None:
    """Retain new URLs discovered for an already tracked listing during an index refresh."""
    record = db.execute(
        """SELECT job_id FROM applications WHERE job_id = ? OR canonical_url IN (?, ?)
           OR job_id IN (SELECT application_id FROM application_urls WHERE url IN (?, ?)) LIMIT 1""",
        (job_id, canonical, source_url, canonical, source_url),
    ).fetchone()
    if record:
        db.executemany(
            "INSERT OR IGNORE INTO application_urls (application_id, url) VALUES (?, ?)",
            [(record["job_id"], url) for url in {canonical, source_url} if url],
        )


def applied_jobs(database_path: Path) -> list[dict]:
    with connect(database_path) as db:
        records = [
            dict(row)
            for row in db.execute("SELECT * FROM applications ORDER BY applied_at DESC, job_id")
        ]
        for record in records:
            record["urls"] = [
                row["url"]
                for row in db.execute(
                    "SELECT url FROM application_urls WHERE application_id = ? ORDER BY url",
                    (record["job_id"],),
                )
            ]
    return records
