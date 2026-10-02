# PLAN-010 — Stop crawl work with the local app

**Status:** M1 pushed to `main` at `444ba0e`; static validation passed, no live crawl or process-tree smoke run
**Created:** 2026-10-02
**Last updated:** 2026-10-02

## Objective

When the owner stops Clue, terminate its active search, Scrapling, and browser work, and leave no search displayed as still running after shutdown.

## Motivation

Clue executes source collection and Jev scoring as background work inside the local Python server. The existing stop helper force-stopped only the server PID, which did not explicitly terminate child processes. Killing the process during a search could also leave a persisted `queued`, `running`, or `scoring` record that blocked later searches or kept showing a spinner.

## Current state

- `scripts/clue.ps1 stop` validates the listener is a Python executable from Conda `gen`, then calls `Stop-Process -Force` on that PID only.
- Search and Jev workers run inside the server process; Scrapling may create child browser processes for dynamic pages.
- An abruptly stopped search can remain in an active state in SQLite.

## Desired state

- The stop helper terminates the validated Clue process tree, including child crawler/browser processes, and confirms port 8000 is free.
- Any unfinished search is marked failed with an explicit interrupted message after the server process is gone. This also runs before a fresh start, recovering state after an unexpected server exit.
- Listings already saved remain in the local index; stopping Clue does not delete profile, CV, results, or source data.
- The recommended stop command is explicit in the startup output and README.

## Scope

- Use Windows `taskkill /T /F` for the already-validated Conda `gen` server PID.
- Add a small SQLite recovery function for active search records and invoke it after stop and before/after the managed server lifetime.
- Update the operator instructions, a decision record, the documentation index, and this plan.

## Out of scope

- Graceful cancellation inside each source connector or resumable crawl checkpoints.
- Rolling back listings from sources that completed before the stop.
- Resetting source refresh timestamps or Jev budget reservations.
- Live crawl or Jev API validation.

## Source-of-truth impact

- [ADR 0011](../decisions/0011-stop-crawls-with-app.md) records the stop contract.
- Update the root README and docs index with the supported stop behavior.
- No schema change or changelog entry is needed; no changelog exists.

## Existing decisions and constraints

- Single-user local Windows app, launched and managed through Conda `gen`.
- Preserve `.data/`, uploaded CV, local profile, and indexed listings when stopping.
- Do not run a live source crawl or Jev request as part of this change.
- Keep unrelated uncommitted PLAN-007/PLAN-009 work out of this checkpoint.
- The owner directs validated milestones to be committed and pushed directly to `main`; do not create a branch.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, and `ponytail-balanced`.
- Context7 FastAPI lifespan and Scrapling spider lifecycle documentation.
- Conda `gen`, Ruff, Python byte-compilation, PowerShell parser, and `git diff --check`.

## Dependencies

- Existing `scripts/clue.ps1` validation of port 8000 listener paths.
- Existing SQLite `search_runs` status fields; no schema migration.

## Risks and unknowns

- Force-stopping the process tree does not roll back source records already written by completed fetches. Those results remain usable and traceable.
- If another program launches detached work outside Clue's process tree, Windows tree termination cannot manage it; current Scraping work is launched by Clue.
- Runtime process-tree behavior and visual recovery messaging remain unverified by a live crawl in this change.

## Milestones

### M1 — Stop the server process tree and recover interrupted runs

**Goal:** Make the supported stop command end all Clue-owned crawl work and make an interrupted search visibly terminal.

**Subtasks:**

- [x] Replace single-PID termination with recursive termination of the validated Python process tree.
- [x] Preserve Conda `gen` path validation, PID-marker recovery, and port-free confirmation.
- [x] Mark queued/running/scoring searches as failed with stage `interrupted` after the app is gone and before a new managed start.
- [x] Keep persisted listings and the user's local profile data unchanged.
- [x] Update start/stop instructions, ADR 0011, and the docs index.

**Affected areas:** `scripts/clue.ps1`, `clue_ai/lifecycle.py`, `README.md`, `docs/README.md`, and `docs/decisions/`.

**Dependencies:** Existing `search_runs` table and Conda `gen` installation.

**Acceptance criteria:**

- [x] `stop` validates the target Python path before calling `taskkill /T /F` and verifies port 8000 is free.
- [x] Stopping or restarting marks every persisted active run as failed/interrupted only after its process is gone; normal completed runs are unchanged.
- [x] The helper and README state that stopping Clue also stops its crawl/browser processes.
- [x] No profile, CV, listing, or source rows are deleted by the stop/recovery logic.

**Validation:**

- [x] `conda run -n gen ruff check clue_ai/lifecycle.py` — passed.
- [x] `conda run -n gen python -m compileall -q clue_ai/lifecycle.py` — passed.
- [x] PowerShell parser check for `scripts/clue.ps1` — passed.
- [x] `git diff --check` — passed.
- [x] Code-path inspection confirms process-tree termination follows Conda path validation and interrupted-state writes happen after the server is stopped.
- [x] `scripts/clue.ps1 status` confirms Clue is stopped and port 8000 is free.
- No live crawl, process-tree smoke, unit suite, or Jev request was run; none was requested.

**Documentation updates:** README, docs index, ADR 0011, and this plan.

**Applicable specialized skills:** `ponytail-balanced`, `milestone-delivery`.

**Expected Git checkpoint:** One scoped commit on `main`, pushed after local validation. Do not include unrelated PLAN-007 or PLAN-009 changes.

## Final integration validation

Run Conda `gen` Ruff and byte-compilation on the changed Python module, parse the PowerShell helper, inspect the guarded process-tree path, confirm the current port is free, and run `git diff --check`. Do not trigger a live crawl or Jev request.

## Rollback / recovery

Revert the helper and lifecycle changes to restore the single-PID stop behavior. The recovery function updates only `search_runs` rows that are still queued, running, or scoring; it does not delete or rewrite candidate/source data.

## Progress

- [x] Confirmed the existing helper stopped only the server PID; search workers run inside that process.
- [x] Resolved current FastAPI lifecycle and Scrapling spider-stop documentation through Context7.
- [x] Implemented process-tree stop and interrupted-run recovery.
- [x] Run static validation; process-tree smoke and live crawl were not run.
- [x] Commit and push the scoped M1 checkpoint to `main` (`444ba0e`).

## Implementation discoveries / decisions

- Use Windows `taskkill /T /F` after the current Conda executable-path guard. This is the local app's operating-system boundary for stopping server-owned children.
- Recover active run rows after termination and before the next managed launch. Completed source responses may have already updated the local index; keep that partial progress.
- Mark an interrupted run as `failed` with a specific message, using existing schema/status behavior and no migration.

## Completion evidence

Ruff, Python byte-compilation, PowerShell parsing, `git diff --check`, and local server status passed. Commit `444ba0e` is pushed to `main`. No unit suite, synthetic process-tree smoke, live crawl, or Jev request was run.
