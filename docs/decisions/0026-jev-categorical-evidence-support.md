# ADR 0026 — Jev categorical verdicts for generated-claim support

Status: Accepted
Date: 2026-10-07
Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0025](0025-jev-approval-of-tailored-resume.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md)

## Context

Clue asks Jev to classify each generated factual block as `supported`, `contradicted`, or `unresolved` using only the linked evidence. The first implementation then downgraded a `supported` answer when Jev's separate self-reported confidence was below 0.50. No owner-labeled calibration set justified that second cutoff.

A bounded live synthetic run showed the effect directly: Jev labeled a computer-vision cover-letter paragraph `supported`, but reported confidence 0.28. Clue changed it to `unresolved`, removed the paragraph, and blocked an otherwise complete packet for having only one body paragraph. This repeated the same category-versus-confidence disagreement already observed in final resume approval and addressed by ADR 0025.

## Decision

Jev's categorical verdict is authoritative for generated-claim support. `supported` remains supported, `contradicted` remains contradicted, and `unresolved` remains unresolved. Reported confidence is retained for diagnosis only and cannot override the categorical result.

Clue keeps the deterministic numeric/date guard: if the generated assertion contains a numeric value or date absent from all linked evidence, Clue downgrades it to `unresolved` even when Jev says `supported`. Missing evidence, malformed/missing Jev answers, and invalid choice labels also remain unresolved. Unsupported or contradicted content is omitted before artifact rendering. The generated-claim decision remains separate from and cannot mutate Jev's saved job-match result.

## Consequences

- Clue no longer applies an uncalibrated second threshold to Jev's categorical support decision.
- Low confidence remains available for evaluation and later calibration, not runtime gating.
- The numeric/date safety check and fail-closed handling of missing or invalid verdicts remain in force.
- The packet remains owner-reviewable; Jev's verdict does not establish truth beyond the cited evidence.
- Changes to this rule use rubric version `jev-grounding-v1.3`.

## Validation

- Unit tests verify that a 0.49-confidence `supported` answer stays supported, an unsupported `300%` claim remains unresolved despite Jev's `supported` label, and missing evidence or malformed responses remain unresolved.
- A bounded synthetic computer-vision run measured the previous failure mode. A successful rerun after the categorical-decision change is required before the packet gate is marked accepted.
