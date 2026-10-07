# ADR 0030 — Live-pilot generation policy and evidence binding

- Status: Accepted
- Date: 2026-10-07
- Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0028](0028-manual-preparation-for-jev-review-results.md), [ADR 0029](0029-retryable-preparation-snapshots.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md)

## Context

The bounded live pilot exposed three implementation risks. First, a cover-letter paragraph could cite a crawled page URL and receive unrelated facts from that same page. Second, Recruiter's structured response ended at its 5,000-token allowance, and a later request could not reserve against the exhausted Clue-local per-opportunity cap. Third, changes to generation settings were not all represented in the immutable request snapshot, so the dossier could not explain which stage budgets produced an attempt.

Visual review also found that Word's built-in `Title` style added an unwanted paragraph rule despite explicit font settings. A writing-prompt experiment intended to remove repetitive relevance statements led Jev to mark both resulting paragraphs unresolved; the experiment was rolled back.

## Decision

- Give each validated research finding a stable local ID and bind a paragraph only to its cited finding IDs. A shared page URL no longer authorizes every finding from that page. Jev receives the exact selected candidate evidence, exact research findings, and the saved listing facts for each assertion.
- Keep GPT-6 Luna at `reasoning.effort=high`. Set output allowances to Researcher 2,200, Diagnoser 2,800, Recruiter 9,000, Rewriter 16,000, and Hiring Manager 2,400 tokens. Record the full per-stage map, model, effort, prompt version, and schema version in each manually triggered generation-policy snapshot. A policy change yields a new request only after the owner triggers that listing again.
- Keep the successful prompt version `.12`. Do not ship the `.13` transfer-language experiment that Jev rejected. The known-good generated letter remains subject to owner style review because its role-relevance bridge wording is repetitive.
- Use a custom cover-letter title style based on Word's `Normal` style; do not inherit the built-in `Title` paragraph rule.
- Set Clue's local monthly and per-opportunity caps to `$0.15` for the bounded pilot after the prior `$0.10` reservation ceiling blocked a final request. These are app-local controls; OpenAI and Jev account caps/settings are not changed. Jev remains the saved job-match authority and separately decides factual support and final CV approval.

## Consequences

- The latest single-listing run completed generation, Jev support (2/2 letter paragraphs), final CV approval, packet quality, usage settlement, and visual rendering. The original listing result remained `review`; it was not upgraded to a match.
- The CV had zero bullet edits and remained text/order-identical to its selected source. Recruiter marked six requirements partial and one absent from the CV. Jev's CV approval is not a job-fit, hiring, or ATS-success prediction.
- Research returned seven findings, no verified contact, and three unresolved questions. No outreach draft, Gmail draft, email, or application was produced. The packet remains in owner review.
- The real-data sample covers one listing only. Personal relevance calibration, broader contact coverage, owner voice acceptance, and hiring outcomes remain unknown.

## Validation

The regression suite covers exact research-finding binding, generation-policy snapshot invalidation, manual-only request creation, Jev support and final-resume gates, document styles, and the no-send boundary. PLAN-020 records the sanitized live measurements, failed tuning attempts, artifact render, and remaining owner-review limits.
