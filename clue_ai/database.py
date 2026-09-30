from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from clue_ai.domain import CandidateProfile, SearchCriteria, utc_now

DEFAULT_SOURCES = (
    {
        "id": "jobicy",
        "name": "Jobicy",
        "kind": "jobicy_api",
        "endpoint": "https://jobicy.com/api/v2/remote-jobs?count=200",
        "state": "approved",
        "enabled": 1,
        "attribution": "Jobicy",
        "interval_seconds": 21_600,
        "retention_days": 30,
        "policy_note": "Free public job-discovery API; poll no more than hourly; keep Jobicy credit and canonical URL. Never use the paid direct-ATS link option.",
        "config_json": "{}",
        "is_builtin": 1,
    },
    {
        "id": "remotejobs",
        "name": "RemoteJobs.org",
        "kind": "remotejobs_api",
        "endpoint": "https://remotejobs.org/api/v1/jobs",
        "state": "approved",
        "enabled": 1,
        "attribution": "Powered by RemoteJobs.org",
        "interval_seconds": 86_400,
        "retention_days": 14,
        "policy_note": "Free public JSON API; one daily page per role query (up to four), 50 results per request, reasonable use, and visible Powered by RemoteJobs.org credit. Keep the RemoteJobs.org listing URL.",
        "config_json": "{}",
        "is_builtin": 1,
    },
    {
        "id": "remoteok",
        "name": "Remote OK",
        "kind": "remoteok_json",
        "endpoint": "https://remoteok.com/api",
        "state": "approved",
        "enabled": 1,
        "attribution": "Remote OK",
        "interval_seconds": 21_600,
        "retention_days": 30,
        "policy_note": "Free public JSON feed; credit Remote OK and link each original post; private local use only.",
        "config_json": "{}",
        "is_builtin": 1,
    },
    {
        "id": "remotefirstjobs",
        "name": "Remote First Jobs",
        "kind": "remote_first_rss",
        "endpoint": "https://remotefirstjobs.com/rss/jobs/{role_slug}.rss",
        "state": "approved",
        "enabled": 1,
        "attribution": "Remote First Jobs",
        "interval_seconds": 21_600,
        "retention_days": 30,
        "policy_note": "Free public role/skill RSS; credit and keep source links; do not submit listings to other job platforms.",
        "config_json": json.dumps({"role_slugs": []}),
        "is_builtin": 1,
    },
    {
        "id": "startupjobs",
        "name": "Startup Jobs",
        "kind": "startup_rss",
        "endpoint": "https://startup.jobs/feeds/jobs?workplace=remote",
        "state": "approved",
        "enabled": 1,
        "attribution": "Startup Jobs",
        "interval_seconds": 21_600,
        "retention_days": 14,
        "policy_note": "Use no-key RSS only for private, non-commercial use; credit Startup Jobs and keep its direct/dofollow canonical links.",
        "config_json": "{}",
        "is_builtin": 1,
    },
)


SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS profile (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  summary TEXT NOT NULL DEFAULT '',
  target_roles TEXT NOT NULL DEFAULT '',
  skills TEXT NOT NULL DEFAULT '',
  experience TEXT NOT NULL DEFAULT '',
  education TEXT NOT NULL DEFAULT '',
  languages TEXT NOT NULL DEFAULT '',
  profile_language TEXT NOT NULL DEFAULT 'unknown',
  work_authorized_countries TEXT NOT NULL DEFAULT '',
  requires_sponsorship TEXT NOT NULL DEFAULT 'unknown',
  cv_filename TEXT NOT NULL DEFAULT '',
  cv_path TEXT NOT NULL DEFAULT '',
  extracted_text TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS app_settings (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  jev_consent_at TEXT NOT NULL DEFAULT '',
  default_work_from TEXT NOT NULL DEFAULT 'Italy',
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('approved', 'review', 'blocked')),
  enabled INTEGER NOT NULL DEFAULT 0,
  attribution TEXT NOT NULL DEFAULT '',
  interval_seconds INTEGER NOT NULL DEFAULT 86400,
  retention_days INTEGER NOT NULL DEFAULT 30,
  policy_note TEXT NOT NULL DEFAULT '',
  config_json TEXT NOT NULL DEFAULT '{}',
  is_builtin INTEGER NOT NULL DEFAULT 0,
  last_checked_at TEXT NOT NULL DEFAULT '',
  last_state TEXT NOT NULL DEFAULT 'never',
  last_error TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS source_query_checks (
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  query_hash TEXT NOT NULL,
  checked_at TEXT NOT NULL,
  PRIMARY KEY (source_id, query_hash)
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  fingerprint TEXT NOT NULL DEFAULT '',
  canonical_url TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  company TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  location_raw TEXT NOT NULL DEFAULT '',
  workplace_type TEXT NOT NULL DEFAULT 'unknown',
  employment_type TEXT NOT NULL DEFAULT 'unknown',
  visa_sponsorship TEXT NOT NULL DEFAULT 'unknown',
  salary_min REAL,
  salary_max REAL,
  salary_currency TEXT NOT NULL DEFAULT '',
  salary_period TEXT NOT NULL DEFAULT '',
  posted_at TEXT NOT NULL DEFAULT '',
  valid_through TEXT NOT NULL DEFAULT '',
  eligibility_status TEXT NOT NULL DEFAULT 'unknown',
  eligibility_evidence TEXT NOT NULL DEFAULT '',
  first_seen_at TEXT NOT NULL,
  last_checked_at TEXT NOT NULL,
  is_active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS job_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  external_id TEXT NOT NULL DEFAULT '',
  source_url TEXT NOT NULL,
  source_posted_at TEXT NOT NULL DEFAULT '',
  last_seen_at TEXT NOT NULL,
  UNIQUE (source_id, external_id),
  UNIQUE (job_id, source_id)
);
CREATE TABLE IF NOT EXISTS job_user_state (
  job_id TEXT PRIMARY KEY REFERENCES jobs(id) ON DELETE CASCADE,
  saved INTEGER NOT NULL DEFAULT 0,
  hidden INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_runs (
  id TEXT PRIMARY KEY,
  criteria_json TEXT NOT NULL,
  status TEXT NOT NULL,
  stage TEXT NOT NULL DEFAULT '',
  message TEXT NOT NULL DEFAULT '',
  checked_sources_json TEXT NOT NULL DEFAULT '[]',
  found_count INTEGER NOT NULL DEFAULT 0,
  matched_count INTEGER NOT NULL DEFAULT 0,
  scored_count INTEGER NOT NULL DEFAULT 0,
  error TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  completed_at TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS search_results (
  run_id TEXT NOT NULL REFERENCES search_runs(id) ON DELETE CASCADE,
  job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  rank INTEGER NOT NULL DEFAULT 0,
  score_state TEXT NOT NULL DEFAULT 'unscored',
  eligibility_status TEXT NOT NULL DEFAULT 'unknown',
  eligibility_evidence TEXT NOT NULL DEFAULT '',
  freshness_status TEXT NOT NULL DEFAULT 'unknown',
  freshness_age_days INTEGER,
  combined_score REAL,
  confidence REAL,
  dimensions_json TEXT NOT NULL DEFAULT '{}',
  evidence_json TEXT NOT NULL DEFAULT '[]',
  score_reason TEXT NOT NULL DEFAULT '',
  rubric_version TEXT NOT NULL DEFAULT '',
  PRIMARY KEY (run_id, job_id)
);
CREATE TABLE IF NOT EXISTS jev_usage (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT REFERENCES search_runs(id) ON DELETE SET NULL,
  month_key TEXT NOT NULL,
  model TEXT NOT NULL,
  started_at TEXT NOT NULL,
  reserved_tokens INTEGER NOT NULL,
  reserved_usd REAL NOT NULL,
  actual_tokens INTEGER,
  actual_usd REAL,
  status TEXT NOT NULL,
  error_code TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_jobs_checked ON jobs(last_checked_at);
CREATE INDEX IF NOT EXISTS idx_job_sources_source ON job_sources(source_id, last_seen_at);
CREATE INDEX IF NOT EXISTS idx_source_query_checks_checked ON source_query_checks(checked_at);
CREATE INDEX IF NOT EXISTS idx_search_runs_created ON search_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_jev_usage_month ON jev_usage(month_key, status);
"""


@contextmanager
def connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, timeout=10.0, isolation_level=None)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    try:
        yield connection
    finally:
        connection.close()


def initialize(database_path: Path) -> None:
    with connect(database_path) as db:
        db.executescript(SCHEMA)
        _ensure_column(db, "sources", "is_builtin", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(db, "search_results", "score_reason", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "search_results", "rubric_version", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "search_results", "eligibility_status", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(db, "search_results", "eligibility_evidence", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "search_results", "freshness_status", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(db, "search_results", "freshness_age_days", "INTEGER")
        _ensure_column(db, "jobs", "fingerprint", "TEXT NOT NULL DEFAULT ''")
        _ensure_column(db, "jobs", "visa_sponsorship", "TEXT NOT NULL DEFAULT 'unknown'")
        _ensure_column(db, "profile", "profile_language", "TEXT NOT NULL DEFAULT 'unknown'")
        db.execute("CREATE INDEX IF NOT EXISTS idx_jobs_fingerprint ON jobs(fingerprint)")
        now = utc_now()
        db.execute("INSERT OR IGNORE INTO app_settings (id, updated_at) VALUES (1, ?)", (now,))
        for source in DEFAULT_SOURCES:
            db.execute(
                """INSERT OR IGNORE INTO sources
                   (id, name, kind, endpoint, state, enabled, attribution,
                    interval_seconds, retention_days, policy_note, config_json, is_builtin)
                   VALUES (:id, :name, :kind, :endpoint, :state, :enabled, :attribution,
                           :interval_seconds, :retention_days, :policy_note, :config_json,
                           :is_builtin)""",
                source,
            )


def _ensure_column(
    db: sqlite3.Connection, table: str, column: str, definition: str
) -> None:
    known = {row["name"] for row in db.execute(f"PRAGMA table_info({table})")}
    if column not in known:
        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def get_profile(database_path: Path) -> CandidateProfile:
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    if row is None:
        return CandidateProfile()
    return CandidateProfile(**{key: row[key] for key in CandidateProfile.__dataclass_fields__})


def save_profile(database_path: Path, profile: CandidateProfile) -> None:
    values = {key: getattr(profile, key) for key in CandidateProfile.__dataclass_fields__}
    values["updated_at"] = utc_now()
    with connect(database_path) as db:
        db.execute(
            """INSERT INTO profile
               (id, summary, target_roles, skills, experience, education, languages,
                profile_language, work_authorized_countries, requires_sponsorship, cv_filename, cv_path,
                extracted_text, updated_at)
               VALUES (1, :summary, :target_roles, :skills, :experience, :education, :languages,
                       :profile_language,
                       :work_authorized_countries, :requires_sponsorship, :cv_filename, :cv_path,
                       :extracted_text, :updated_at)
               ON CONFLICT(id) DO UPDATE SET
                summary=excluded.summary, target_roles=excluded.target_roles,
                skills=excluded.skills, experience=excluded.experience,
                education=excluded.education, languages=excluded.languages,
                profile_language=excluded.profile_language,
                work_authorized_countries=excluded.work_authorized_countries,
                requires_sponsorship=excluded.requires_sponsorship,
                cv_filename=excluded.cv_filename, cv_path=excluded.cv_path,
                extracted_text=excluded.extracted_text, updated_at=excluded.updated_at""",
            values,
        )


def get_settings(database_path: Path) -> dict[str, str]:
    with connect(database_path) as db:
        row = db.execute("SELECT * FROM app_settings WHERE id = 1").fetchone()
    return dict(row) if row else {"jev_consent_at": "", "default_work_from": "Italy"}


def set_jev_consent(database_path: Path, accepted: bool) -> None:
    with connect(database_path) as db:
        db.execute(
            "UPDATE app_settings SET jev_consent_at = ?, updated_at = ? WHERE id = 1",
            (utc_now() if accepted else "", utc_now()),
        )


def save_search_run(database_path: Path, run_id: str, criteria: SearchCriteria) -> None:
    with connect(database_path) as db:
        db.execute(
            "INSERT INTO search_runs (id, criteria_json, status, stage, message, created_at) VALUES (?, ?, 'queued', 'queued', 'Preparing your search', ?)",
            (run_id, json.dumps(criteria.to_jsonable()), utc_now()),
        )


def delete_personal_data(database_path: Path, cv_path: Path | None, data_dir: Path) -> None:
    cv_root = (data_dir / "cv").resolve()
    if cv_path:
        candidate = cv_path.resolve()
        if candidate.parent == cv_root and candidate.is_file():
            candidate.unlink()
    with connect(database_path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM search_runs")
        db.execute("DELETE FROM jev_usage")
        db.execute("DELETE FROM source_query_checks")
        db.execute("DELETE FROM job_user_state")
        db.execute("DELETE FROM job_sources")
        db.execute("DELETE FROM jobs")
        db.execute("DELETE FROM profile")
        db.execute("DELETE FROM sources WHERE is_builtin = 0")
        db.execute(
            """UPDATE sources SET last_checked_at = '', last_state = 'never', last_error = ''
               WHERE is_builtin = 1 AND state = 'approved' AND enabled = 1"""
        )
        db.execute(
            """UPDATE app_settings SET jev_consent_at = '', default_work_from = 'Italy',
               updated_at = ? WHERE id = 1""",
            (utc_now(),),
        )
        db.execute("COMMIT")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.execute("VACUUM")
    cv_dir = data_dir / "cv"
    if cv_dir.exists():
        for child in cv_dir.iterdir():
            if child.is_file():
                child.unlink()
