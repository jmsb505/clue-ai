# PLAN-027 — Owner-confirmed retry after unresolved OpenAI usage

Status: Validated — PR/merge progression pending
Created: 2026-10-12 · Last updated: 2026-10-12
Related: [PLAN-026](PLAN-026-live-preparation-progress.md), [ADR 0011](../decisions/0011-stop-crawls-with-app.md), [ADR 0023](../decisions/0023-application-preparation-and-action-boundaries.md)

## Objective

Make a failed application preparation retryable when an OpenAI request may have reached the provider but Clue never received a usage receipt, without guessing the charge or erasing the reservation.

## Motivation

PLAN-026 marks work interrupted by stopping Clue as failed and exposes a manual retry. The service then rejects a retry whenever the failed attempt has an OpenAI usage row in `reserved` or `unknown`. There is no application-preparation usage reconciliation action, so the owner can be left with a dossier that offers no way forward even though they are willing to accept a possible duplicate charge.

## Current state

- Ordinary retries and duplicate packet requests are blocked while unresolved OpenAI usage exists.
- The dossier does not explain the unresolved reservation or provide an owner-confirmed path.
- OpenAI usage rows track a reserved estimate and possible actual usage; a reserved or unknown row is not proof that the provider did or did not charge.
- This installation's interrupted Recruiter request has a `reserved` usage row; its value must remain an estimate unless OpenAI later provides a receipt.

## Desired state

- Keep the default retry blocked when its prior request has unresolved OpenAI usage.
- In that request's dossier, show the affected stage, status, and reserved estimate, and require an explicit owner checkbox acknowledging that the request may already have been charged.
- Permit a new attempt only through that checked owner action. Retain the original usage row unchanged and associate a durable audit event with the new attempt, including the prior request and unresolved usage facts.
- Preserve consent, factual validation, Jev matching, external provider controls, and the separate human review/application boundary.

## Scope

- Add a request-scoped unresolved OpenAI usage summary to the preparation dossier.
- Add a required owner acknowledgment to the retry form when needed and validate it server-side.
- Atomically audit the acknowledgment when the new preparation attempt is created, show it in the new dossier, and keep bookkeeping events out of owner-reported outcome statistics.
- Add offline tests for default blocking, acknowledged retry, immutable unresolved usage, audit details, and dossier/route behavior.
- Update the architecture overview, README recovery guidance, this plan, and an ADR.

## Out of scope

- Contacting OpenAI, reading the owner's browser, looking up provider billing, or settling/releasing an uncertain usage row.
- Changing provider account caps, Clue's local cap settings, consent, model configuration, application snapshots, crawler policy, or retry behavior for Jev.
- Automatically retrying a failed preparation or removing duplicate-charge risk.

## Source-of-truth impact

`docs/architecture/overview.md` and `README.md` describe the changed recovery behavior. [ADR 0043](../decisions/0043-owner-confirmed-openai-retry.md) records why acknowledgment creates a new attempt while preserving the unresolved ledger row. No schema migration is expected; `application_events` and `openai_usage` already represent the audit event and reservation.

## Existing decisions and constraints

- `openai_usage.status` values remain `reserved`, `settled`, `unknown`, and `released`. This work cannot infer settlement.
- The owner explicitly starts each application packet; preparation never submits applications or sends outreach.
- Git progression follows the milestone workflow. Do not advance `main` until applicable local validation passes.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, `ponytail-balanced`.
- Existing FastAPI request parsing, Jinja dossier, SQLite transaction, pytest, and Ruff conventions.

## Dependencies

None. No new package or database column is anticipated.

## Risks and unknowns

- A retry can cause an additional provider charge if the original request completed remotely. The explicit acknowledgment and preserved ledger row make that risk visible; Clue cannot remove it.
- The reserved dollar value is an estimate, not an invoice. UI wording must not state that the provider charged that amount.
- If a newer attempt already exists, retry must not bypass its own unresolved-usage guard.

## Milestones

### M1 — Audited owner-confirmed retry

Goal:

Let an owner retry one failed listing after acknowledging its unresolved OpenAI usage, while keeping normal safeguards and the original ledger evidence intact.

Subtasks:

- [x] Pass the acknowledgment only through the retry service path; keep new packet requests blocked by default.
- [x] Record the acknowledgment in `application_events` in the same transaction that creates the new attempt.
- [x] Show stage/status/estimated reserve and a required checkbox in the affected dossier; parse and enforce the field on POST.
- [x] Add service and UI/route regressions, including unchanged usage status/value and audit linkage.
- [x] Update canonical docs and record validation evidence here.

Affected areas:

- `clue_ai/application_prep.py`, `clue_ai/web.py`, `clue_ai/feedback.py`, `clue_ai/templates/preparation_detail.html`, `tests/test_application_prep.py`, `tests/test_application_workflow.py`, README, architecture overview, this plan, and ADR 0043.

Dependencies: None.

Acceptance criteria:

- [x] An unresolved usage row still blocks retry unless the owner explicitly acknowledges possible duplicate provider billing.
- [x] A checked retry creates exactly one new owner-triggered request and a durable owner-reported event containing the prior request and unresolved usage facts.
- [x] The prior `openai_usage` record remains unchanged in its status, reservation, actual-usage, and receipt fields.
- [x] The dossier clearly calls the amount an estimate and identifies the possible charge; the retry control is accessible and server-enforced. The new dossier displays the acknowledgment, while outcome statistics include only application-stage events.
- [x] An unrelated active/latest request with unresolved usage cannot be bypassed by acknowledging an older request.
- [x] No OpenAI/TypeSafe call occurs in offline tests; no external action or Jev-match change is introduced.

Validation:

- [x] Focused retry service and route/dossier tests: 3 relevant preparation tests and the unresolved-receipt workflow guard passed; a final focused run of the HTTP route and newer-attempt guard passed 2 tests.
- [x] Full pytest suite: **400 passed**, with one upstream Starlette/AnyIO deprecation warning, in 99.13 seconds.
- [x] Ruff, Python byte-compilation, and `git diff --check` passed.
- [x] Read the existing local failed request and usage row only: state `failed`; Recruiter usage `reserved` at `$0.0072721`, `actual_usd` unknown. No OpenAI request or local-ledger mutation was made.

Documentation updates:

- [x] Record current behavior in README and architecture overview.
- [x] Accept ADR 0043 after implementation passes.
- [ ] Record PR and merge evidence here.

Applicable specialized skills:

- `milestone-delivery`, `ponytail-balanced`.

Expected Git checkpoint:

- One coherent, validated branch commit; push and open a normal PR, then advance `main` only through the repository's allowed GitHub review path.

## Final integration validation

M1 local integration validation passed. Branch commit, GitHub PR, and merge evidence remain pending.

## Rollback / recovery

The change adds no database schema. Reverting the code restores the existing hard block; audit events and unresolved provider-usage rows remain available. No usage record should be automatically reconciled or deleted as a rollback step.

## Progress

- 2026-10-12: Confirmed that startup recovery marks the stalled request failed but `retry_preparation` still refused its unresolved Recruiter reservation. Implemented a dossier-level owner acknowledgment, unchanged usage ledger, and transactional audit event on `codex/owner-confirmed-openai-retry`.

## Implementation discoveries / decisions

- Acknowledgment is scoped to the failed request and cannot authorize a different latest unresolved attempt. The service re-reads the failed request and all unresolved rows inside the request-creation transaction, and rejects stale acknowledgments.
- No schema migration was needed: the existing `application_events` record and `openai_usage` ledger express the audit and accounting states.

## Completion evidence

- `pytest -q -p no:cacheprovider`: 400 passed; one upstream Starlette/AnyIO deprecation warning (99.13 seconds).
- Focused service, route/dossier, interruption retry, and unresolved-receipt guard tests passed.
- Ruff, Python byte-compilation, and `git diff --check` passed.
- The actual stalled Recruiter usage row was verified read-only as `reserved` with no actual usage receipt. Clue was not started, no retry was triggered, and no external service was contacted.
- GitHub branch push, PR, and merge: pending.
