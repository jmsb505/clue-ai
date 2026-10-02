# ADR 0016 — Durable application tracker

**Status:** Accepted
**Date:** 2026-10-03
**Related:** [PLAN-016](../plans/PLAN-016-applied-job-tracker.md)

## Decision

The owner manually marks jobs after applying on an external site. Clue stores a local application snapshot with job identity, title, company, location, canonical/known listing links and time marked. It never submits an application or verifies an employer received it. Repeat marking preserves the first date.

Applications are separate from the expiring job index, without a foreign key from their identity to `jobs`. Known URLs are linked to their application with cascading deletion. Exclusion compares exact retained job identity, canonical URL or known source URL; it does not guess that similarly named vacancies are duplicates. Index refreshes remember newly observed URLs belonging to an already tracked identity. A wholly new post with different URLs/identity may require a new mark.

Applied jobs are omitted from discovery candidates sent to Jev, historical result views/counts and saved-role lists. Their original snapshots stay accessible under Applied roles, even after listing retention cleanup, history clearing or search reset. Undo deletes application state only, preserving any saved/hidden choice; an inactive or expired listing still needs to be available in the index to appear in search. Full personal-data deletion clears application snapshots and links. Local backups are separate copies.

Reuse the existing local request boundary, POST forms, source-link validation and visual components. The tracker is a reversible status with date/link, not a pipeline, reminder service or external integration. The schema is additive and initializes existing databases idempotently.
