# ADR 0006: Typed Jev fit scoring with a conservative local spend reserve

**Status:** ACCEPTED for the first local increment; calibration remains open
**Date:** 2026-09-30

## Context

Jev is the required candidate-to-listing evaluator. Its answers are typed decisions and confidence values, not generated explanations. The app must keep hard constraints deterministic, show traceable evidence, avoid sending unnecessary CV fields, and remain under the owner's $5/month TypeSafe ceiling even when a response is delayed or the network fails.

## Decision

- Use TypeSafe's official Python SDK and `system_one` endpoint with a pinned `jev-1.13.0` model until the owner evaluates a later version.
- Ask four compact, versioned `Choice` questions per listing about role alignment, skills evidence, experience/scope, and optional preference alignment. Use five ordered fit levels (`0`–`4`) plus `unknown`; missing evidence must not be treated as a mismatch. Convert the returned choice distribution to a normalized 0–1 signal, then combine dimensions in code using the user's saved weights. Deterministic hard filters run before Jev.
- Keep a matching snapshot and score confidence locally. Present Jev fit as an estimate, never as hiring probability. Do not claim calibrated levels until synthetic and owner-reviewed evaluation supports them.
- Build evidence from the reviewed candidate profile and exact listing text with deterministic matched/unknown fields. Do not ask Jev to invent free-form evidence or send the raw CV.
- Exclude candidate name, contact details, street address, original file, and unreviewed extracted text from Jev state. Send only reviewed job-relevant profile fields and the bounded listing snapshot needed for the requested judgment.
- Set SDK `RetryPolicy(max_retries=0)` so paid calls are never repeated automatically. A failed call remains an explicit unscored state; the user may retry manually.
- Score at most five listings in a request. Only attempt scoring when the reviewed profile is marked English and each listing is confidently identified as English; keep other listings visible and unscored.
- Before each call, reserve an 80,000-token allowance at the current published input price. This deliberately exceeds the documented 64,000-token context as a conservative accounting allowance. Settle successful responses to `usage.input_tokens`; retain the full reserve if the outcome is ambiguous. Do not start a request that would exceed the app's $4.00 rolling 30-day inference cap. The remaining $1.00 is a buffer toward the owner's $5 per 30-day ceiling; automatic provider credit refills must remain off.
- Record request count, model version, input tokens, estimated USD, and reserve state without storing an API key or full request payload in the usage ledger.
- When a key is missing, or the cap is reached, show jobs without fit scores and explain why; do not substitute another model.

## Alternatives considered

- **Use Jev as the sole authority for hard filters or location eligibility:** Rejected. User permissions, geography, salary and explicitly hard constraints are product logic; Jev only informs semantic fit.
- **Send the full CV for every job:** Rejected because direct identifiers and irrelevant personal data are unnecessary. Send only reviewed job-relevant fields.
- **Let the SDK retry automatically:** Rejected for this budgeted workflow because retries may repeat billable requests. Report transient failures and let the owner retry.
- **Use a fallback model:** Rejected under the single-model decision and $0 non-TypeSafe spend requirement.
- **Charge only after API usage is reported:** Rejected as the only guard because a timeout can hide a billable accepted request. Reserve a token allowance above the documented context before sending.

## Consequences and limitations

- The 80k-token reserve is deliberately conservative and can stop scoring while actual usage remains low. The UI displays the rolling reserve total; ambiguous requests remain reserved.
- The guard covers requests sent by this app, not other software using the same account/key, provider-side taxes, or account billing settings. The owner must disable auto-refills and confirm TypeSafe's terms and billing before real CV use.
- TypeSafe currently publishes $42 per billion input tokens, zero output-token price, a 64k total context, and a response usage field. Limits and aliases can change; record the answering model ID and review official docs when upgrading.
- Fit labels, language detection, and weights require a representative synthetic benchmark before personal reliance; score levels do not imply an interview or hiring probability.
- Even minimized work history may identify the candidate; the app must disclose that it is personal data sent to TypeSafe before a score call.

## Implementation state

The client, four-dimension rubric (`fit-v1.1.0`), unknown-evidence handling, contact redaction, English-only gate, per-request reservation, 30-day ledger, and explicit score action are implemented. Offline mocked validation passed, including minimized synthetic request state and the no-key path. One synthetic live Jev request remains in M2; no real CV has been or will be used for that check.

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
