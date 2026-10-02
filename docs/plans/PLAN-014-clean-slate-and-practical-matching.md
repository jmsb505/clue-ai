# PLAN-014 — Clean slate and practical matching

**Status:** Complete; M1 pushed (`777bb48`), M2 validated and delivered in this checkpoint
**Created / updated:** 2026-10-02

## Objective and motivation

Reset the owner's local search state and improve overly strict, opaque matching. The last completed run assessed 1,342 listings but produced no confirmed matches. A combined filter decision cannot identify which requirement failed; inferred target roles also contain a CV sentence. Unknown pay and seniority should remain useful leads without being presented as confirmed paid junior positions.

## Scope and intended behavior

- Preserve the uploaded CV, editable profile, API settings, consent, source configuration and company selections. Clear listings, history, rankings, saved/hidden jobs, query refresh records and crawler timestamps. Retain Jev's spend ledger because resetting searches does not erase prior charges.
- Stop the server and crawler tree before resetting. Make an ignored local SQLite backup, perform deletion in a transaction, refuse active runs, and expose a repeatable `scripts/clue.ps1 reset` command.
- Treat target roles, transferable skills and AI relevance as ranking preferences. Preserve the paid junior/intern focus, explicit location/workplace restrictions, and optional user requirements.
- Evaluate seniority, pay, location, workplace and other requirements independently with Jev. Missing information goes to review; an uncertain conflict goes to review, never to confirmed match. Retain each filter's reported decision and confidence.
- Show match and review listings together as potential opportunities, with clear verification labels. Keep all/conflict/unassessed views and listing URLs.
- Reject action sentences during CV job-title inference. Clean the contaminated saved role list while preserving the rest of the profile.

## Constraints, tools and source-of-truth impact

Use Conda `gen`, implementation-plan and milestone-delivery. No external source crawl or paid Jev request is required to validate software behavior. Keep AI relevance as the largest default weight and assess every retained listing. Preserve existing uncommitted PLAN-007 work. The owner explicitly requires coherent validated checkpoints pushed directly to `main`.

Update the reset operations guide, product definition, README and a new decision record. No schema migration or new dependency is needed. Existing rubric snapshots remain unchanged until the explicitly requested local reset removes their runs.

## M1 — Reusable local search reset

**Goal:** A fresh discovery state with recoverable local backup.

- [x] Add transactional reset, backup and active-run guard.
- [x] Add `clue.ps1 reset`, which stops the server tree first and leaves it stopped.
- [x] Preserve profile/settings/source choices/spend, clear all search and refresh state.
- [x] Add meaningful reset tests: cascades, retention, fresh sources, active-run rejection and rollback on failure.
- [x] Update reset operations and README; validate in Conda `gen` and push checkpoint to main.

**Acceptance:** Synthetic reset empties every search table, preserves CV/profile and ledger, source refreshes are due again, backup restores pre-reset rows, active runs cannot be erased, and repeated reset is safe. Required tests and Ruff pass. Expected checkpoint: `feat: add clean-slate search reset`.

## M2 — Practical Jev criteria and visible opportunities

**Goal:** Rank related roles broadly and retain uncertainty with inspectable filter decisions.

- [x] Replace the composite filter question with five scoped typed checks in each existing batch; version rubric.
- [x] Preserve clear exclusions; use review for missing facts, preferred experience, uncertain model conflicts and stale-but-not-expired postings.
- [x] Rank target roles and AI affinity without exact-title rejection.
- [x] Add opportunities counts/query/view and scoped filter details to result cards.
- [x] Remove action sentences from inferred CV titles.
- [x] Validate mock Jev handling, required/missing answers, ranking, counts, pagination and rendering; update product/decision docs.
- [x] Push checkpoint to main, execute the local reset, clean the saved contaminated target roles, verify local data invariants, and leave app stopped.

**Acceptance:** No missing check can yield confirmed match. Clear confident conflicts remain conflict; ambiguous conflicts remain review. High-fit review roles are visible alongside matches, ordered by fit, with exact counts and paginated links. Every check and posting link is inspectable. Reset state has zero indexed jobs/results/runs/query checks and reset source/company timers while preserving profile and spend.

## Validation, limitations and recovery

Use focused synthetic tests with fake Jev clients and isolated SQLite databases; no live network or paid calls. Run related existing tests, report pre-existing failures accurately, and validate the staged checkpoint independently of PLAN-007 edits. Match quality on real listings remains unverified until the owner starts a fresh search. Model confidence is uncalibrated; the conflict confidence threshold is a conservative software heuristic, not a probability.

The reset backup resides under ignored `.data/backups/`. Restore the SQLite database only with Clue stopped. Git rollback restores code; deleting search rows cannot undo TypeSafe charges.

## Progress and evidence

- Stopped the existing Clue process tree before changing local data.
- Confirmed contaminated inferred target roles and the aggregate filter rubric's opaque decisions.
- M1: Conda `gen` `pytest -q tests/test_reset.py`: **5 passed**. Focused Ruff and PowerShell parser validation passed. Tests cover ledger detachment, profile/CV/source/company retention, backup readability, refresh eligibility, repeated reset, active-run refusal and transactional rollback.
- Executed the authorized local reset with the app stopped: removed **15 searches and 1,342 listings** and cleared all query/crawler timers. SQLite backup created under ignored `.data/backups/`. No live crawl or TypeSafe request was made.
- M2: Focused Conda `gen` validation passed **54 tests**, plus the added filtered second-page test. Coverage includes the five check outcomes, low/invalid confidence, missing answers, filter-only retries without score loss, retained sponsorship and late-description pay details, opportunity counts/order/hidden state, per-check rendering, parsed role cleanup, reset integrity and mocked CV workflow. Updated the existing CV smoke test's obsolete copy assertion and its typed Jev mock; retained its upload/scoring/consent/redaction checks and added the senior conflict assertion.
- Verified the active local database against the reset backup: all six search/index/query tables empty, source/company timers cleared, source choices/company tracking/settings/spend preserved, CV file present, all other profile fields retained, foreign keys valid. Removed only the contaminated action sentence from target-role suggestions.
- Additional discovery: saved-result retrieval previously omitted normalized sponsorship and truncated Jev descriptions at 5,000 characters. It now supplies sponsorship and the existing 9,000-character bound so late compensation details are retained.
- Final integration evidence: exported the staged Git index to an ignored validation directory, confirmed imports came from that snapshot, and ran the focused suite in Conda `gen`: **55 passed**. Ruff passed on all changed Python modules and tests. `git diff --cached --check` passed. The index excludes every pre-existing PLAN-007 hunk; those edits remain in the working tree. The existing CV workflow test now uses typed filter answers rather than invalid numeric filter choices.
- Final local-state check against the backup passed; the launcher reports **Clue stopped, port 8000 free**. No new live crawl or Jev call was made. Real-world matching quality remains for the owner's next fresh search; no match count is promised.
