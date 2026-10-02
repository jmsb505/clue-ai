# PLAN-016 — Applied job tracker

**Status:** M1 validated and delivered in this checkpoint
**Created / updated:** 2026-10-03

## Objective and current state

The owner needs to record jobs already applied to and keep them out of subsequent results. Existing saved/hidden state has no application status and is deleted when indexed jobs expire. Search history currently has unrelated unfinished PLAN-007 changes that must remain unstaged.

## Scope and decisions

Add a local Applied tracker with title, company, location, original posting links and the date marked applied. Add manual Mark applied actions to results/saved roles and Undo applied in the tracker. No automatic applications, reminders, external requests, extra dependencies or additional application pipeline statuses.

Application snapshots and known listing URLs persist separately from indexed jobs, so expiry cleanup, history clearing and search reset cannot reintroduce a previously recorded listing. Match only existing job identity/canonical or known source URLs; title similarities do not prove that two vacancies are the same. Newly reposted jobs with entirely different URLs may require marking again. Complete personal-data deletion clears applications too.

## M1 — Durable application tracking and search exclusion

- Add additive SQLite applications/link tables; retain existing data and repeat initialization safely.
- Record application snapshots idempotently, preserving the original date on repeat clicks; undo only application state.
- Exclude applied listings from visible results, counts, saved lists and discovery candidates/Jev input. Saved/hidden actions must not remove application state.
- Build Applied page and navigation using current components; show posting links, date and reversible action.
- Update product/decision/operations docs and reset retention wording. Preserve unrelated PLAN-007 work.

**Acceptance:** Marking a listing removes it from results/counts and keeps it in Applied. Another search/crawl of the same identity/known URLs remains excluded. An application remains visible after source expiry or search reset. Undo makes retained jobs eligible without wiping saved/hidden state. Unknown mark IDs return 404. Full personal-data deletion clears snapshots/URLs. No automatic application or paid API call occurs.

**Validation:** Static Python checks, schema/repository inspection, isolated local workflow verification of mark/list/undo, counts, reindexing, reset/expiry retention and deletion. Validate the staged snapshot independently of PLAN-007 changes. No new test suite is requested. Capture exact runtime/manual evidence and limitations before commit/push.

**Expected checkpoint:** `feat: track applied jobs and exclude them from searches` on main under standing owner authorization. Applicable skills: implementation-plan and milestone-delivery. Use Conda gen.

## Recovery and source-of-truth impact

Additive tables do not change existing job/profile records. Back up local SQLite before applying schema, keep app stopped when modifying its database. Code rollback leaves new tables unused but retained. Update product definition, ADR 0016, README and local data/reset guide. Local backups may retain old applications until separately removed.

## Progress / evidence

- Located all candidate/results/counts and saved-state paths, plus expiry/reset/full-deletion behavior.
- Implemented independent application snapshots/known URL aliases, idempotent mark, undo, additive schema, source-refresh alias retention and full-deletion cleanup. Reused existing cards/forms/navigation with no new UI dependency or external call.
- Manual local HTTP workflow with isolated synthetic data: results and Applied page returned 200; mark/undo returned 303; unknown listing returned 404; cross-origin undo returned 403. Mark reduced visible candidates/results from two to one and removed the saved role; undo restored both candidates and the original bookmark. Tracker rendered title, location, timestamp, posting link and undo action.
- Manual persistence checks: applied status survived listing expiry, index deletion, reindexing under a known alternate URL and search reset. Original/new known URLs remained tracked; full personal-data deletion removed snapshots/links. Foreign-key checks were empty throughout. No new formal tests were added or run.
- Exported staged index independently of PLAN-007 changes. Repeated the local mark/list/undo workflow against that exact code; counts and saved-state restoration matched the working-copy scenario. Python compilation and Ruff passed; staged whitespace check passed. Temporary servers were closed explicitly after verification.
- Stopped the owner's completed Clue session through the existing process-tree helper. Applied additive schema twice to the actual database, confirming exact retention of every pre-existing table's rows and valid foreign keys. Backup: ignored `.data/backups/before-applied-tracker-20261002T231819Z-5ff8a93f.sqlite3`. No real job was marked applied, and no crawl or paid Jev call ran.
- Both verification port 8001 and Clue port 8000 are free; app remains stopped. Unrelated PLAN-007 changes remain unstaged. Direct main checkpoint uses standing owner authorization.
