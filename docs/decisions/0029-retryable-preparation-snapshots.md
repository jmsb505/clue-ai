# ADR 0029 — Retryable preparation snapshots

- Status: Accepted
- Date: 2026-10-07
- Related: [ADR 0028](0028-manual-preparation-for-jev-review-results.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md)

## Context

Preparation requests are immutable and idempotent for an active attempt. A settled failed attempt may be retried under the same input snapshot with a higher `attempt_no`. The current schema expresses uniqueness across `(job_id, snapshot_sha256, attempt_no)`, but databases created before `attempt_no` was introduced retained a SQLite unique auto-index on only `(job_id, snapshot_sha256)`. Adding the column could not remove that old constraint, so retries failed locally before an API request.

The retry helper also rebuilt the request without the optional employer-page URL, so a retry could silently lose research context that was bound to the original snapshot.

## Decision

At initialization, detect the legacy two-column unique index and transactionally rebuild only the `preparation_requests` table with the three-column attempt constraint. Temporarily disable SQLite foreign-key enforcement only for that transaction, copy every request row and field, replace the table under its original name, restore both request indexes, and re-enable foreign keys. Leave child tables in place and verify referential integrity in migration tests.

The retry action preserves the original immutable snapshot, including its owner-supplied public employer-page URL, selected CV ID, job/JeV state, and input revisions. It creates a distinct attempt number only after the prior attempt is terminal and all usage is settled. Active same-snapshot attempts remain idempotent.

## Consequences

- Existing failed dossiers become retryable without deleting preparation history, packets, research, or usage records.
- A retry keeps the same research scope and does not silently fall back to an aggregator URL.
- Migration work is limited to the legacy unique constraint and preserves existing child rows and foreign-key relationships.
- An unresolved API receipt still blocks retry; the migration does not change spend gates or provider-account settings.

## Validation

An offline legacy-database test confirms the old constraint is replaced, previous request and child rows remain, a second attempt with the same snapshot can be inserted, and `PRAGMA foreign_key_check` reports no issues. The migration was also applied to a consistent temporary copy of the configured local database; counts for requests, packets, artifacts, research pages, contacts, OpenAI usage, and Jev usage were preserved. A separate retry test confirms the employer-page URL and snapshot JSON are unchanged.
