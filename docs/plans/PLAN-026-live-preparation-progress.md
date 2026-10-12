# PLAN-026 — Live application preparation progress

Status: Complete — merged to main in PR #10
Created: 2026-10-12 · Last updated: 2026-10-12
Related: [PLAN-022](PLAN-022-application-workspaces.md), [PLAN-023](PLAN-023-ranked-search-history-and-form-guidance.md), [PLAN-024](PLAN-024-lean-task-first-ui.md), [PLAN-025](PLAN-025-preparation-overrides-and-application-email.md)

## Objective

Show useful, live, honest progress after the owner starts packet generation. The dossier must identify the active workflow stage, surface public-page crawl failures without hiding that the workflow can continue, and distinguish a live worker from a worker whose heartbeat has gone stale.

## Motivation

The dossier currently reports that preparation was requested but does not poll for changes. Its progress details are initially closed for active work, and the workflow updates status only when research and generation broadly start or finish. A slow crawler or model request therefore looks indistinguishable from a stalled process.

## Current state

- `requested`, `researching`, and `generating` are stored in `preparation_requests`, but the dossier has no preparation status endpoint or live polling.
- The Researcher may attempt up to four bounded public pages. Individual crawl failures are returned to the model as tool errors and do not necessarily stop packet preparation; the UI does not report them.
- `updated_at` is used to order application folders and should retain its record-change meaning.

## Desired state

- The selected listing dossier opens its progress panel automatically while work is active and updates status without a manual refresh.
- The panel shows a stage-based track and an indeterminate progress indicator; it never claims a fabricated percentage or time-to-completion.
- Status messages name meaningful work: queued/worker slot, public research and each crawl attempt, Diagnoser, Recruiter, Rewriter, Jev factual and resume checks, packet rendering, completion, or a surfaced non-fatal crawl failure.
- A separate worker heartbeat timestamp is refreshed while a task is queued behind the local operation lock or running. The UI reports the last heartbeat and warns that work may be stalled only when that heartbeat is stale.
- The status endpoint returns only progress metadata and never the saved job snapshot, profile, CV, research text, or generated content.
- A denied or blocked public page remains a crawl failure; Clue does not bypass it or retry it outside the existing bounded policy.

## Scope

- Add a backward-compatible heartbeat column and active-state heartbeat updates.
- Add a local preparation status endpoint with stage, elapsed time inputs, heartbeat age, and stale indication.
- Add workflow status transitions around each meaningful research, generation, validation, and rendering step; make non-fatal crawl failures visible.
- Add accessible live polling, an indeterminate bar, stage tracker, elapsed time, heartbeat age, stale warning, and terminal-state handling to the application dossier.
- Add focused route, persistence, template, and workflow tests; update the roadmap, product definition, and architecture.

## Out of scope

- Changing the research page limit, retry rules, anti-bot handling, or crawler access policy.
- Changing provider settings, spending controls, model behavior, application submission, or external actions.
- Predicting completion time or presenting a percentage without measured stage durations.

## Source-of-truth impact

Update `docs/product-definition.md`, `docs/architecture/overview.md`, `docs/roadmap.md`, and this plan. No separate decision record is required: heartbeat is operational metadata, while the existing manual trigger, bounded crawl, Jev validation, and action boundaries remain unchanged.

## Existing decisions and constraints

- Only the owner-triggered listing runs this work. No background batch research or generation is introduced.
- Jev remains the authority for matching and factual/CV validation; GPT creates drafts and Clue keeps them for owner review.
- Crawler blocks are respected. An unreachable public page does not prevent the Researcher from using the saved listing and other allowed pages where possible.
- Keep the UI local, lean, accessible, and dependency-free.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, `ui-ux-research`, `frontend-design`, `ponytail-balanced`.
- Local pytest fixtures and synthetic request records; no live API or crawler is needed for validation.

## Dependencies

- Existing preparation request state machine, bounded Researcher crawler, FastAPI/Jinja application dossier, vanilla JavaScript, and SQLite persistence.

## Risks and unknowns

- A heartbeat proves the local worker thread is alive, not that a remote crawler/model call is making useful progress. The UI must say “may be stalled” only for a stale heartbeat and must not imply that a fresh heartbeat guarantees completion.
- The crawler warning in the report may be emitted by Scrapling when a site blocks a request. The implementation must expose the relevant application-stage outcome without weakening block handling.
- Adding heartbeat metadata requires a safe SQLite migration for existing local databases.

## Milestones

### M1 — Workflow status and heartbeat

Goal:

Persist granular preparation status and heartbeat evidence, expose a safe status endpoint, and report crawl outcomes honestly.

Subtasks:

- [x] Add `worker_heartbeat_at` to existing and new preparation databases without changing `updated_at` ordering.
- [x] Keep the heartbeat alive while waiting for the operation lock and during long work; stop it when work ends.
- [x] Update user-facing status at crawl, writing-agent, Jev check, and rendering boundaries.
- [x] Add a local status route with active/stale and elapsed-time metadata only.

Affected areas:

- `clue_ai/application_prep.py`, `clue_ai/application_workflow.py`, `clue_ai/database.py`, `clue_ai/web.py`, `tests/test_application_prep.py`, `tests/test_application_workflow.py`.

Dependencies: None.

Acceptance criteria:

- [x] Existing SQLite databases gain heartbeat storage on initialization.
- [x] Active requests receive heartbeat updates without changing application-folder sorting semantics.
- [x] Status shows each workflow phase and non-fatal crawl failure; Jev match outcome remains unchanged.
- [x] Status response contains no CV, profile, job-description, research-page, or generated-document contents.
- [x] Stale status is derived from heartbeat age and described as possible stall, not confirmed failure.

Validation:

- [x] Run focused tests for heartbeat migration/update, status route privacy, active/stale response, and workflow stage updates.

Documentation updates:

- [x] Document the endpoint metadata and heartbeat meaning in the architecture overview.

Applicable specialized skills:

- `milestone-delivery`, `ponytail-balanced`.

Expected Git checkpoint:

- Commit backend progress and status endpoint as a milestone checkpoint on this feature branch.

### M2 — Live dossier progress and integration validation

Goal:

Make active preparation visible and understandable from the owner's dossier until it finishes or becomes stale.

Subtasks:

- [x] Open and poll the progress panel for active requests; stop polling for terminal states.
- [x] Show current stage, indeterminate progress, elapsed time, last heartbeat, stale warning, and request errors accessibly.
- [x] Confirm in-app documentation describes crawl blocks, live progress, and the manual owner review boundary.
- [x] Run the relevant full test suite and record evidence in this plan.

Affected areas:

- `clue_ai/templates/preparation_detail.html`, `clue_ai/static/app.js`, `clue_ai/static/app.css`, tests, and product/roadmap documentation.

Dependencies: M1.

Acceptance criteria:

- [x] Active progress is visible without refresh and has no invented percentage or time estimate.
- [x] The interface clearly distinguishes a live worker heartbeat from a stale/missing heartbeat.
- [x] Keyboard and assistive-technology status updates are usable; reduced-motion preference is honored.
- [x] Completion and failure stop polling and show the existing packet review/retry actions.
- [x] Existing manual-only application and outreach boundaries remain visible.

Validation:

- [x] Run targeted tests and repository validation; capture the final test result and any limitation here.

Documentation updates:

- [x] Update product definition, architecture overview, roadmap, and this plan with actual behavior/evidence.

Applicable specialized skills:

- `milestone-delivery`, `ui-ux-research`, `frontend-design`, `ponytail-balanced`.

Expected Git checkpoint:

- Commit dossier UI, documentation, and validated completion evidence on the feature branch.

## Final integration validation

- [x] Confirm clean tracked diff, targeted/full test results, and migration behavior.
- [x] Review final changes on the branch before opening a pull request.

## Rollback / recovery

The schema migration only adds a nullable-by-default text timestamp column and is backward-compatible. Revert the code/UI change to disable polling; leaving the unused column in a local SQLite database is safe. No user documents or external accounts are modified.

## Progress

- 2026-10-12: M1 and M2 completed locally. The dossier polls active requests, reports heartbeat age and possible stalls, and keeps bounded-crawl failures visible through packet review. PR #10 merged this implementation to main.

## Implementation discoveries / decisions

- Use a dedicated heartbeat column, not `updated_at`, because the latter orders application folders and records user-visible state changes.
- Use a 10-second heartbeat and mark it stale after 35 seconds; this is a liveness threshold, not an operation timeout.
- Display step names and an indeterminate bar. A fresh heartbeat means the local worker is alive, not that an external site/provider is responding.

## Completion evidence

- M1 targeted pytest: `tests/test_application_prep.py` focused progress/migration cases — 3 passed; `tests/test_application_workflow.py` agent/crawl progress cases — 6 passed.
- Full suite: `394 passed` in 84.64 seconds; one existing Starlette/AnyIO `BlockingPortal` deprecation warning.
- Static validation: Ruff, Python byte-compilation, JavaScript syntax check, and `git diff --check` pass.
- No live OpenAI call or real public crawl was needed for this UI/runtime-state change. Block behavior was tested with a synthetic crawler response.
- GitHub reported no Actions runs or commit checks for the PR branch. PR #10 merged successfully; local `main` was fast-forwarded to the merge commit.
