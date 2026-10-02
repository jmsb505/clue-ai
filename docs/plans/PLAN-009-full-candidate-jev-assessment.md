# PLAN-009 — Full-candidate Jev assessment

**Status:** M1 implemented; static validation passed; main checkpoint pending
**Created:** 2026-10-02
**Last updated:** 2026-10-02

## Objective

Have Jev assess every active, visible job in the local index against the candidate profile and the complete set of user search criteria, then keep each assessment available in that search run with a clear filter-fit status.

## Motivation

The latest completed crawl parsed 437 listing records, but the search flow applied deterministic role, work-mode, location, and date filters before Jev. Jev therefore scored only two listings, and all eight saved runs contain the same two results. This does not establish that only two jobs fit the candidate. The owner explicitly requires Jev to assess all collected listings using the user's filters.

## Current state

- `run_search()` loads active, non-hidden indexed jobs, calls `filter_jobs()`, and persists only rows that pass its hard filters.
- `score_run()` receives only the persisted subset. Its TypeSafe state omits most search criteria and listing fields needed to assess them.
- Jev is already batched at five listings per request with an 80,000-token reserve per call and a $4 rolling 30-day app cap.
- Job persistence falls back from canonical URL to a fingerprint of title, company, location, and posted date. Distinct postings with missing dates can therefore be merged.
- Results are rendered as one unpaginated list and show a single matching-listing count.

## Desired state

- Snapshot all active, non-hidden indexed listings into each run after retrieval, expiration handling, and strong-identity deduplication. Do not remove a listing before Jev because of a user search criterion.
- Send minimized candidate facts, every current search criterion, and relevant listing facts to Jev in existing bounded batches.
- Store a separate structured Jev assessment of filter compatibility: `match`, `review`, `conflict`, or `unassessed`. A mismatch or unknown stays visible; the result page can group and sort listings by that assessment.
- Keep all candidates visible if Jev is not enabled, unavailable, or the app budget is exhausted. Show the reason and never substitute another model. Do not use an English-only heuristic to skip a listing.
- Use canonical URL or stable source identity for automatic duplicate merging. Keep fingerprint similarity as a review signal rather than deleting a candidate identity.
- Paginate the result view and report candidate, Jev-scored, filter-match, review, conflict, and unassessed counts separately.

## Scope

- Remove the hard-filter pre-gate from the live search-to-Jev flow.
- Enrich the Jev state with target roles, location/work arrangement, employment, salary, sponsorship, freshness, must-have/nice-to-have terms, and filter options.
- Add per-listing filter assessment persistence, run summaries, progress updates, and an accessible paginated results view.
- Replace fingerprint-only auto-merging with strong listing identity checks and clarify source coverage counts.
- Update product, architecture, decision, roadmap, research, and plan documentation.

## Out of scope

- Expanding or changing job sources, their refresh intervals, crawling policy, or attribution.
- Increasing the $4 app-side Jev reserve or the owner's $5 monthly ceiling; adding any paid service or alternate model.
- Sending a live personal CV or triggering a live Jev request during implementation.
- Automatically splitting existing merged database rows where the original source snapshots are no longer available.
- Automated application submission or changes to manual X lead discovery.

## Source-of-truth impact

- Supersede the pre-filter-before-Jev behavior in the Product Definition and ADR 0006 with [ADR 0010](../decisions/0010-full-candidate-jev-assessment.md).
- Update [Architecture Overview](../architecture/overview.md), [UI/UX implementation review](../research/ui-ux-implementation-review.md), [Roadmap](../roadmap.md), and [documentation index](../README.md).
- No changelog exists in this repository; record the shipped behavior and evidence in this plan and source-of-truth docs.

## Existing decisions and constraints

- Single-user local workflow; original CV and profile remain local unless the owner enabled Jev disclosure and consent.
- Send only minimized, contact-redacted profile facts. Listing descriptions and user-entered criteria are untrusted data, not instructions.
- Jev remains the only model used for fit assessment. Keep the current app-side $4 rolling 30-day reservation under the owner's $5/month ceiling.
- Current batch size is five listings. At the local baseline of 1,135 active rows, this is at most 227 requests; 227 maximum 80,000-token reserves at $0.042 per million tokens total about $0.763 for one full pass. The guard remains authoritative if the index or actual usage differs.
- Preserve the local Conda `gen` environment and push each validated checkpoint directly to `main`, per the owner's standing instruction. Keep uncommitted PLAN-007 changes out of this milestone.
- No test suite or live API request will be run during this implementation unless the owner asks for that validation.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, `ui-ux-research`, and `ponytail-balanced`.
- Context7 TypeSafe AI Python SDK and System One documentation; existing TypeSafe client and budget guard.
- Conda `gen`, Ruff, Python byte-compilation, Jinja template parsing, and `git diff --check`.

## Dependencies

- Existing local profile, job index, search-run/result persistence, Jev consent and budget ledger.
- Existing `/searches/{run_id}` result route and Jinja/CSS interface.
- SQLite additive column migration through the existing `initialize()` path.

## Risks and unknowns

- Scoring a larger pool increases sequential request time. Progress must report the assessed/total count for each batch.
- The app's conservative reserve may stop a run before all candidates are scored. All remaining candidates must stay visible and be labeled `unassessed` with the budget reason.
- Job descriptions are truncated before Jev; the UI must not imply that missing evidence means lack of fit.
- Existing fingerprint merges cannot be reversed reliably from the current index alone. Fresh source observations will use stronger identity rules going forward.
- Jev's filter judgment is a review signal, not a legal work-authorization determination or a guarantee that a job remains open.
- A 1,135-item result set requires pagination and clear status counts to remain usable.

## Milestones

### M1 — Assess and show every candidate

**Goal:** Send every active, non-hidden indexed listing through Jev against the current profile and all search criteria, then make every listing and its assessment status reviewable.

**Subtasks:**

- [x] Replace fingerprint-only auto-merge with canonical-URL or stable source-ID identity matching; report inserted versus reused rows clearly.
- [x] Snapshot all active, non-hidden listings into the run without role, location, workplace, salary, employment, sponsorship, or posted-date prefiltering.
- [x] Include all current search criteria and relevant listing facts in the minimized Jev state; add a separate typed filter-compatibility answer for each listing.
- [x] Persist match/review/conflict/unassessed status separately from weighted fit dimensions; keep current scoring and monthly budget protections.
- [x] Report candidate progress per Jev batch and final counts for candidates, scored listings, filter matches, review, conflicts, and unassessed.
- [x] Add status tabs/counts and pagination to the results view; keep every assessed or unassessed candidate reachable.
- [x] Update current product, architecture, decision, roadmap, UI research, and documentation index records.

**Affected areas:** `clue_ai/jev.py`, `clue_ai/services.py`, `clue_ai/repository.py`, `clue_ai/database.py`, `clue_ai/web.py`, `clue_ai/templates/`, `clue_ai/static/app.css`, and `docs/`.

**Dependencies:** Existing Jev client/budget guard; existing active-job index; no new dependency.

**Acceptance criteria:**

- [x] Every active, non-hidden indexed listing is attached to a run before Jev evaluation; user filter values do not remove candidates first.
- [x] Jev request construction includes all search criteria plus role, location, work arrangement, employment, salary, sponsorship, and date facts for every batch.
- [x] Candidates retain separate fit and filter states; missing Jev responses, budget exhaustion, and request errors stay visible and resumable.
- [x] The result page shows total candidates and separate counts for Jev-scored, match, review, conflict, and unassessed; 50-item pagination can reach every result.
- [x] New ingests merge only on canonical URL or source-scoped external ID; fingerprint-only matches no longer collapse distinct postings.
- [x] The app-side cap remains $4 per rolling 30 days, within the owner's $5 ceiling; no other paid component is introduced.
- [x] Product and architecture documentation match the delivered behavior and preserve uncertainty/legal boundaries.

**Validation:**

- [x] `conda run -n gen ruff check` on changed Python modules.
- [x] `conda run -n gen python -m compileall -q clue_ai`.
- [x] Parse the changed results Jinja template with the installed environment.
- [x] `git diff --check`.
- [x] Inspect the pipeline: `filter_jobs()` no longer gates the live result set; no API/client call was made during static validation.
- [x] Record live Jev and visual browser acceptance as pending owner-run workflow; it was not exercised during implementation.

**Documentation updates:** Product Definition, Architecture Overview, ADR 0010, UI/UX review, Roadmap, docs index, and this plan.

**Applicable specialized skills:** `ui-ux-research`, `ponytail-balanced`, `milestone-delivery`.

**Expected Git checkpoint:** One coherent M1 implementation commit on `main`, pushed after local static validation. The planning and decision record may be checkpointed separately before code.

## Final integration validation

- Confirm schema initialization adds assessment fields without changing or deleting existing result rows.
- Confirm the run snapshot includes all active, non-hidden jobs while hidden/expired jobs remain excluded by existing rules.
- Confirm all result states survive history navigation and page selection.
- Confirm the Jev reserve is acquired before each request and remaining listings are marked unassessed when the cap stops the batch loop.
- Run the static validation listed for M1; a real-CV workflow and live JEV spend remain owner-run.

## Rollback / recovery

Revert the M1 commit to restore pre-filtered results and fingerprint fallback. The additive SQLite columns remain harmless defaults; existing rows and source records are not deleted. Do not attempt automatic reconstruction of old fingerprint merges.

## Progress

- [x] Confirmed the latest run parsed 437 records but stored/scored two results; all eight saved runs reference the same two job identities.
- [x] Confirmed current flow hard-filters candidates before saving the per-run results and Jev sees only that subset.
- [x] Resolved current TypeSafe documentation: System One evaluates one state against a map of typed questions; existing five-job batch can carry multiple listing assessments.
- [x] Complete planning and decision documentation checkpoint.
- [x] Implement and statically validate M1; keep PLAN-007 changes unstaged.
- [ ] Commit and push M1 to `main` after staging only this milestone's changes.

## Implementation discoveries / decisions

- **All means all current indexed candidates:** A search evaluates the full active, non-hidden local index after the usual expiry cleanup, including cached listings from sources not refreshed in the current run. Refresh cadence remains visible in source coverage.
- **Jev judges criteria; software reports status:** Do not use deterministic role/location/date filters to exclude a candidate before Jev. Keep hidden, inactive, and expired exclusions, and present Jev's filter status as advisory evidence for the user's review.
- **Strong identity before fuzzy similarity:** Canonical URL and source-scoped external ID may merge a listing. A title/company/location/date fingerprint alone is not sufficient to discard a posting; missing dates make it especially ambiguous.
- **The current batch reserve is adequate at the observed index size:** 1,135 active rows / five jobs per call is 227 calls, with a maximum modeled reserve of about $0.763. The runtime ledger remains the source of truth.
- **Use existing UI foundation:** Status tabs, accessible links, and pagination in Jinja/CSS are smaller and better suited than adding a React table library.

## Completion evidence

Ruff, Python byte-compilation, Jinja parsing, and `git diff --check` passed in Conda `gen`. Source inspection confirms all active non-hidden indexed listings are snapshotted without calling `filter_jobs()` as a gate, filter criteria and relevant job facts enter each bounded Jev request, and per-run result retrieval is paginated. No live search, TypeSafe request, or personal CV was sent during validation. The live end-to-end workflow remains for the owner to run after updating/restarting the local app. Direct-to-main checkpoint is pending.
