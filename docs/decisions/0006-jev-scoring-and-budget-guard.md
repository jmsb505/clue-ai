# ADR 0006: Typed Jev fit scoring with a conservative local spend reserve

**Status:** ACCEPTED for the scoring rubric and budget guard; workflow trigger revised by ADR 0008
**Date:** 2026-09-30

## Context

Jev is the required candidate-to-listing evaluator. Its answers are typed decisions and confidence values, not generated explanations. The app must keep hard constraints deterministic, show traceable evidence, avoid sending unnecessary CV fields, and remain under the owner's $5/month TypeSafe ceiling even when a response is delayed or the network fails.

## Decision

**Current consent/trigger rule:** Under [ADR 0008](0008-cv-first-automatic-search.md), the user gives a one-time opt-in. Clue then automatically evaluates eligible listings after searches, using parsed or user-edited profile fields. The prior per-search score action is superseded; all data-minimization, language, key, retry, and budget gates in this ADR remain.

- Use TypeSafe's official Python SDK and `system_one` endpoint with a pinned `jev-1.13.0` model until the owner evaluates a later version.
- Ask four compact, versioned `Choice` questions per listing about role alignment, skills evidence, experience/scope, and optional preference alignment. Use five ordered fit levels (`0`–`4`) plus `unknown`; missing evidence must not be treated as a mismatch. Convert the returned choice distribution to a normalized 0–1 signal, then combine dimensions in code using the user's saved weights. Deterministic hard filters run before Jev.
- Keep a matching snapshot and score confidence locally. Present Jev fit as an estimate, never as hiring probability. Do not claim calibrated levels until synthetic and owner-reviewed evaluation supports them.
- Build evidence from parsed or user-edited candidate fields and exact listing text with deterministic matched/unknown fields. Do not ask Jev to invent free-form evidence or send the raw CV.
- Exclude candidate name, contact details, street address, original file, and full extracted CV text from Jev state. After one-time opt-in, send only bounded parsed or user-edited job-relevant profile fields and listing details needed for the fit judgment.
- Set SDK `RetryPolicy(max_retries=0)` so paid calls are never repeated automatically. A failed call remains an explicit unscored state; the user may retry manually.
- Score at most five listings in a request. Only attempt scoring when the profile is marked English and each listing is confidently identified as English; keep other listings visible and unscored.
- Before each call, reserve an 80,000-token allowance at the current published input price. This deliberately exceeds the documented 64,000-token context as a conservative accounting allowance. Settle successful responses to `usage.input_tokens`; retain the full reserve if the outcome is ambiguous. Do not start a request that would exceed the app's $4.00 rolling 30-day inference cap. The remaining $1.00 is a planned buffer toward the owner's $5 per 30-day ceiling. Provider refill settings and account-wide charges are unverified under the owner's 2026-09-30 waiver.
- Record request count, model version, input tokens, estimated USD, and reserve state without storing an API key or full request payload in the usage ledger.
- When a key is missing, or the cap is reached, show jobs without fit scores and explain why; do not substitute another model.

## Alternatives considered

- **Use Jev as the sole authority for hard filters or location eligibility:** Rejected. User permissions, geography, salary and explicitly hard constraints are product logic; Jev only informs semantic fit.
- **Send the full CV for every job:** Rejected because direct identifiers and irrelevant personal data are unnecessary. Send only bounded parsed or user-edited job-relevant fields.
- **Let the SDK retry automatically:** Rejected for this budgeted workflow because retries may repeat billable requests. Report transient failures and let the owner retry.
- **Use a fallback model:** Rejected under the single-model decision and $0 non-TypeSafe spend requirement.
- **Charge only after API usage is reported:** Rejected as the only guard because a timeout can hide a billable accepted request. Reserve a token allowance above the documented context before sending.

## Consequences and limitations

- The 80k-token reserve is deliberately conservative and can stop scoring while actual usage remains low. The UI displays the rolling reserve total; ambiguous requests remain reserved.
- The guard covers requests sent by this app, not other software using the same account/key, provider-side taxes, or account billing settings. On 2026-09-30 the owner waived TypeSafe account/terms/billing checks for personal local use. This waiver does not verify an account-wide cap. Clue discloses the fields sent and requires one-time opt-in before automatic checks; see ADR 0008.
- TypeSafe currently publishes $42 per billion input tokens, zero output-token price, a 64k total context, and a response usage field. Limits and aliases can change; record the answering model ID and review official docs when upgrading.
- Fit labels, language detection, and weights require a representative synthetic benchmark before personal reliance; score levels do not imply an interview or hiring probability.
- Even minimized work history may identify the candidate; the app must disclose that it is personal data sent to TypeSafe before opting in.

## Implementation state

The client, four-dimension rubric (`fit-v1.1.0`), unknown-evidence handling, contact redaction, English-only gate, per-request reservation, and 30-day ledger are implemented. Automatic invocation after search and one-time consent are implemented by PLAN-004 M1; its tests use synthetic CV data and a mocked Jev client. On 2026-09-30, one earlier live request with synthetic candidate and listing facts returned a scored result on Jev 1.13.0: 1,574 input tokens, fit `0.9904`, confidence `0.9475`, and an app-ledger cost estimate of `$0.00006611`. Offline tests cover invalid-key, rate-limit, 529, timeout, missing-usage, and cap-stop behavior; the latter uses a small synthetic cap to show the call is blocked before creating the client. These checks validate the integration path, not score calibration or provider billing terms.

## Reconsideration

Revisit the reserve size if TypeSafe changes model context/pricing or provides a reliable preflight token count. Revisit confidence/score labels only after written evaluation against representative synthetic examples and the owner's relevance judgments.

## Evidence

- Official model reference: https://docs.typesafe.ai/models
- Official API reference: https://docs.typesafe.ai/api
- Official Python SDK client/retry API: https://docs.typesafe.ai/sdk/python/api/clients/sync
- Official TypeSafe legal index: https://docs.typesafe.ai/legal
- Owner budget and data minimization decision: [ADR 0004](0004-single-user-local-app.md)
- Product scoring boundaries: [product definition](../product-definition.md)
- Delivery/evaluation plan: [PLAN-002](../plans/PLAN-002-local-first-job-search-app.md)

## Affected source-of-truth documents

- `docs/architecture/overview.md`
- `docs/product-definition.md`
- `docs/readiness/definition-gate.md`
- `README.md`
- `docs/plans/PLAN-002-local-first-job-search-app.md`
