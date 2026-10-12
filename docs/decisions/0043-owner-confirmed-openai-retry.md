# ADR 0043 — Owner-confirmed retry after unresolved OpenAI usage

- Status: Accepted — implementation and local validation passed; PR pending
- Date: 2026-10-12
- Related: [PLAN-027](../plans/PLAN-027-owner-confirmed-openai-retry.md), [ADR 0011](0011-stop-crawls-with-app.md), [ADR 0023](0023-application-preparation-and-action-boundaries.md)

## Context

Clue records a local OpenAI usage reservation before generation. A timeout or process stop can happen after the provider receives a request but before Clue receives a usage receipt. The row then remains `reserved` or `unknown`; its reserved amount is an estimate and does not prove the actual provider charge. The existing retry guard correctly avoids silently repeating the call, but offers no in-app reconciliation path for application preparation. This left a startup-recovered, failed dossier without an available retry action.

## Decision

1. Continue to block ordinary preparation retries whenever the failed attempt has an OpenAI usage row in `reserved` or `unknown`.
2. On that request's dossier, show the affected stage, status, and estimated reserved value with clear wording that the provider may already have charged and the estimate is not a receipt.
3. Offer a separate retry action only after the owner checks an explicit acknowledgment of possible duplicate billing. Enforce the acknowledgment on the server; do not treat a missing field as consent.
4. Create the new preparation and its owner-reported audit event in one SQLite transaction. The event identifies the prior request and the unresolved usage rows and values that the owner acknowledged.
5. Leave the original usage row unchanged. Do not mark it released, settled, or reconciled, and do not contact OpenAI or claim to know the billed amount.
6. Apply the existing unresolved-usage guard to the latest matching attempt as well, so acknowledgment of an older attempt cannot bypass a newer unresolved reservation.
7. Show the recorded acknowledgment in the new dossier. Keep internal retry-accounting events out of owner-reported application-stage and outcome summaries.
8. Keep consent, any configured provider/account controls, local usage recording, Jev's saved match, content validation, and manual application/outreach boundaries unchanged.

## Consequences

- An owner can proceed after Clue loses a receipt, with the possibility of a duplicate provider charge made explicit.
- Usage accounting remains conservative: unresolved reservations stay visible and are not converted into guessed actual costs.
- The dossier audit trail explains why the next attempt was created and which prior usage rows were knowingly left unresolved. These bookkeeping events do not change application-outcome reports.
- This is not an automatic retry or provider-billing reconciliation feature.

## Validation

PLAN-027 M1 passed 400 repository tests, focused retry/route tests, Ruff, Python byte-compilation, and `git diff --check`. Synthetic tests confirmed that acknowledgment creates a new attempt and audit event while leaving the old usage row unchanged, and that a newer unresolved attempt remains protected. The existing local failed request was inspected read-only; no provider API call or ledger edit was made. GitHub delivery is tracked in PLAN-027.
