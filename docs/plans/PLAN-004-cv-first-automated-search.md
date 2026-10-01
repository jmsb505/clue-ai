# PLAN-004 — CV-first automated search and Jev validation

**Status:** M1 implemented, validated, and pushed to `origin/main` at `ea2b73ab53580acee1558b56c2832d50cd4b4e8f`
**Created:** 2026-10-01
**Last updated:** 2026-10-01

## Objective

Make the main workflow one CV upload followed by local parsing, an automatic search across currently approved sources, and automatic Jev fit scoring when the owner has enabled Jev and configured the key. Show clear progress and ranked results; never apply to jobs.

## Motivation

The current app separates CV upload, manual profile review/save, search setup, and Jev scoring. It also fails to infer target roles from a CV, so a first-time user can reach search with no useful role query. The owner expects the direct resume-first flow described in the product definition and on JevJobs/Jobbie: upload once, let the app parse and search, and review match results. X is deferred from this workflow.

## Current state

- Home links to Search and Profile instead of offering a CV-first action.
- `/profile/extract` creates a pending CV draft; the owner must visit the profile editor and save it.
- Search is a separate form. Jev scoring is a separate manual action after a search.
- Local extraction recognizes a small set of section headings but does not derive target roles or CV language.
- The app already has a bounded background source-search worker, Jev scoring guard, local CV storage, and result-progress polling.

## Desired state

From Home, the owner uploads a PDF or DOCX once. Clue extracts job-relevant profile facts locally, derives likely role titles, saves the profile and CV locally, and immediately starts a background search using saved preferences or the initial remote-from-Italy defaults. After deterministic filters, Jev validates and ranks matches automatically when the owner has enabled Jev. The owner sees parsing/search/scoring progress and a result list; they can edit the saved profile or search preferences later. No application is submitted.

If Jev is not enabled, the search still completes and results explain how to enable scoring. Clue never sends the original CV file, direct contact details, work authorization, or source URLs to Jev. Search results remain available when the key, consent, budget, or language gate prevents scoring.

## Scope

- Replace the home-page primary CTA with a CV-first upload and search action; offer a repeat-search action using the saved CV.
- Add a local profile parser that fills the existing profile fields and infers likely role titles from explicit target-role sections or recent position headings.
- Preserve the user's saved search criteria. For first run, use inferred roles, remote work, and Italy as the search defaults.
- Start the current bounded source refresh and deterministic filter flow immediately after a valid upload.
- Automatically run the existing Jev scoring path after a completed search. Preserve the one-time data opt-in, key requirement, English-language gate, and $4 app-side rolling reserve.
- Show background states for source search, filtering, Jev evaluation, completion, and non-scored/error outcomes.
- Keep profile editing and advanced search settings available after the one-action path.
- Update consent copy to explain that enabled Jev scoring happens automatically after searches and identify the fields sent.
- Remove X from the primary navigation and search copy while preserving the separately implemented X feature for later reconsideration.
- Update canonical product, architecture, roadmap, readiness, UI research, and this plan.

## Out of scope

- Automated X discovery or X website/API integration.
- Employer-page autofetch from user-pasted links, new job sources, or source-policy changes.
- Automatic applications, application-form filling, account creation, or email.
- Sending a raw CV, contact details, or an unreviewed full extracted document to Jev.
- Replacing the local Python/Jinja/SQLite stack or adding runtime dependencies.
- Removing the separate profile editor and advanced search form.

## Source-of-truth impact

- Update `docs/product-definition.md` and ADR 0006 to reflect local automatic parsing and one-time consent for automatic Jev scoring.
- Add an ADR for the CV-first workflow and its Jev boundary.
- Update `docs/architecture/overview.md`, `docs/readiness/definition-gate.md`, `docs/roadmap.md`, `docs/research/ui-ux-implementation-review.md`, `README.md`, and `docs/README.md`.
- Update this plan with validation, limitations, and main-branch evidence.

## Existing decisions and constraints

- Single-user local app; the owner requested direct milestone commits and pushes to `main` after validation.
- CV extraction stays local and accepts PDF/DOCX. A profile remains editable after parsing.
- Approved sources remain bounded by source-specific refresh policies. Search does not trigger an unbounded web crawl.
- Jev is the only paid service. App-side Jev requests remain under the existing $4 rolling reserve toward the owner's $5 allocation.
- Jev use requires a saved opt-in and configured key. Do not make external requests without both.
- Score only supported English profile/listing pairs under the current validated rubric. Other listings remain visible and clearly unscored.
- X is outside this milestone.
- No live CV, Jev API, or external source calls during local validation.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, `ui-ux-research`, `frontend-design`, `ponytail-balanced`
- FastAPI multipart upload and background-task guidance from Context7.
- Current TypeSafe Python SDK `system_one`, response usage, and retry guidance from Context7.
- Official reference review: [JevJobs](https://jevjobs.ai/) and [Jobbie](https://jobbie.bot/).
- Conda `gen` for local validation.

## Dependencies

- Existing PDF/DOCX extraction, profile persistence, source registry, filters, result polling, and Jev budget guard.
- Existing `.env` configuration for the TypeSafe key; its value is not to be displayed or committed.

## Risks and unknowns

- CV layouts vary. Role inference must be conservative, keep the parsed profile editable, and avoid silently inventing a target role.
- A missed language classification must produce an unscored result rather than sending unsupported text to Jev.
- Automatic scoring can spend up to the existing app-side reserve. The UI and plan must describe the opt-in as automatic after each search.
- A background operation is tied to the local app process. The UI must keep the run status clear, and validation must confirm the server is shut down afterward.
- Search feeds can be unavailable or stale; preserve cached results and report source status rather than blocking the whole flow.

## Milestones

### M1 — One-upload-to-ranked-results workflow

**Goal:** The owner uploads a CV once and Clue automatically parses it, searches approved sources, applies hard filters, and scores eligible matches with Jev when enabled.

**Subtasks:**

- [x] Build a CV-derived profile parser with conservative role and language inference.
- [x] Add a Home upload/repeat-search action that saves locally and starts a search run.
- [x] Reuse saved criteria; apply remote-from-Italy defaults on first use.
- [x] Chain Jev scoring into search completion behind existing consent, key, language, and budget guards.
- [x] Update progress, result, home, and settings copy for automatic scoring and clear fallback states.
- [x] De-emphasize X from the primary workflow without changing its separate route or fetch prohibition.
- [x] Add tests for profile inference, upload persistence, search startup, auto-score gating, progress, and failure recovery.
- [x] Update source-of-truth docs and this plan.

**Affected areas:** `clue_ai/resume.py`, `web.py`, `services.py`, `domain.py`, `jev.py`, home/profile/search/results/settings templates, project CSS/JavaScript, tests, and product/architecture documentation.

**Dependencies:** None.

**Acceptance criteria:**

- [x] On first use, a valid PDF/DOCX upload is locally parsed, saved, and redirects directly to a search run; no profile-review or advanced-search page is required first.
- [x] Search criteria use the saved preference set when present and otherwise use inferred role titles with the remote-from-Italy defaults.
- [x] Progress shows source search, filtering, Jev evaluation when enabled, and a clear completed/unscored/failed result.
- [x] With consent and a configured key, the normal search flow automatically invokes the existing Jev scoring path after filtering; it does not require a second Score action.
- [x] Without consent, a key, an eligible language pair, or available budget, no unauthorized Jev call occurs and the result explains its unscored state.
- [x] The CV file and extracted full text stay local. The existing minimized Jev payload and contact redaction remain in force.
- [x] Profile editing, search preferences, saved jobs, and no-auto-apply behavior remain available.
- [x] X is not presented as an automated source in the primary workflow and no X request is made.
- [x] Tests, Ruff, compilation, rendered-flow checks, and local server cleanup pass in Conda `gen`.
- [x] Documentation records actual behavior, consent, limitations, and validation evidence.

**Validation:** Test with synthetic PDF/DOCX files and mocked source/Jev adapters. Confirm Jev does not call its client without consent/key or beyond the app cap. Inspect the rendered Home and result progress states. Run project tests, Ruff, byte-compilation, `git diff --check`, and a bounded local startup/shutdown check; do not leave port 8000 listening.

**Documentation updates:** Product definition, architecture, ADR 0006 or follow-up ADR, readiness gate, roadmap, UI review, README/docs index, and this plan.

**Applicable specialized skills:** `ui-ux-research`, `frontend-design`, `ponytail-balanced`.

**Git checkpoint:** M1 implementation commit `ea2b73ab53580acee1558b56c2832d50cd4b4e8f` was pushed directly to `origin/main`; `git ls-remote` confirmed the same remote SHA. This is the implementation milestone commit.

## Final integration validation

Upload a synthetic CV through TestClient, verify the new profile and local file are saved, inspect derived criteria, observe mocked source completion and Jev scoring, and confirm the results page exposes the right score or unscored reason. Include no-key, no-consent, language-unknown, no-results, and source-failure paths. No live Jev or source request is part of this validation.

## Rollback / recovery

Revert the M1 commit to restore the previous profile-review, separate-search, manual-score workflow. The database schema is expected to remain additive or unchanged. The stored profile and CV remain removable through Settings.

## Progress

- 2026-10-01: Owner clarified the required product flow is one CV upload followed by behind-the-scenes parsing, job search, and Jev validation. X is deferred for this workflow.
- 2026-10-01: Baseline inspection found that upload currently creates a pending draft, roles/language are not fully inferred, and search and Jev scoring are separate user actions.
- 2026-10-01: Implemented the one-action CV workflow, English/Italian section and role inference, saved-preference reuse, automatic guarded Jev scoring, and a repeat-search path. Added local tests for successful mocked Jev scoring, no-opt-in behavior, criteria defaults/reuse, profile persistence, and rendered results.
- 2026-10-01: `conda run -n gen python -m pytest -q` passed 90 tests; Ruff, byte-compilation, and `git diff --check` passed. A temporary local startup check rendered the new Home page with a temporary empty data directory; the previous Conda `gen` process and the verification instance were stopped, port 8000 was confirmed free, and temporary data was removed. No live job source or Jev request was made.
- 2026-10-01: Commit `ea2b73ab53580acee1558b56c2832d50cd4b4e8f` was pushed directly to `origin/main`; `git ls-remote` matched the local main SHA.

## Implementation discoveries / decisions

- The reference products lead with resume parsing and matching; Clue should adapt the single-action resume-first pattern and keep its no-auto-apply boundary.
- Context7 confirms FastAPI `BackgroundTasks` runs the registered task after the response; keep this local, bounded workflow in the existing process and expose polling progress.
- Context7 confirms Jev typed `Choice` questions return structured answers and usage. Continue to use the existing adapter and zero-retry policy rather than introducing a second scoring integration.
- A one-time opt-in remains required because selected CV-derived fields and job details leave the device for TypeSafe when Jev is enabled.

## Completion evidence

Implementation, synthetic validation, rendered Home inspection, documentation, direct-to-main push, remote-head confirmation, and bounded server cleanup are complete. The live personal CV workflow remains for the owner to exercise; no real CV, job-source request, or Jev request was used during validation.
