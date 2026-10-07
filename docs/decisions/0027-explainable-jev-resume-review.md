# ADR 0027 — Explainable Jev tailored-resume review

Status: Accepted
Date: 2026-10-07
Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0025](0025-jev-approval-of-tailored-resume.md), [ADR 0026](0026-jev-categorical-evidence-support.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md)

## Context

Repeated synthetic evaluations showed that Jev can approve and later revise a tailored resume built from the same source CV and job fixture. The existing review question returned only a categorical decision and confidence, while Clue recorded a generic explanation. That made a revise result difficult to diagnose and left the reviewer without the selected CV structure policy or the Recruiter's requirement-to-CV coverage map.

The selected structure policy matters: a resume set to preserve should not be rejected just because its source order was retained. The Recruiter map is a document-coverage index, not an additional match score or evidence that the candidate lacks an uncovered skill.

## Decision

Pass the selected structure policy and Recruiter's requirement coverage into the separate Jev tailored-resume review. Clarify that Jev should approve a materially sound resume for owner review, should not demand an ideal rewrite or every preferred qualification, and should require a concrete material reason to choose `revise`.

In the same Jev request, ask for a separate categorical diagnostic reason: no material issue, unsupported claim, material source-evidence loss, obscured role evidence, saved-match inconsistency, or insufficient evidence. Store and surface this reason when Jev chooses `revise`. The diagnostic reason is explanatory only and does not override the overall Jev decision. Only the overall explicit `approved` label opens the packet gate; `revise`, `unresolved`, or a missing/invalid answer continues to block it. Model confidence remains diagnostic only.

## Consequences

- Jev receives the context needed to apply preserve/improve policy and understand the Recruiter's CV coverage map.
- A blocked packet now records a specific categorical reason that can guide later tuning and owner review.
- The overall Jev decision remains the sole final resume gate and cannot modify the saved listing match.
- The tailored-resume review rubric advances to `tailored-resume-fit-v2`.
- This change improves diagnosis but does not make Jev's decisions deterministic or confidence-calibrated.

## Validation

- Offline tests verify the selected structure policy and requirement map reach Jev, each diagnostic reason is preserved, and `revise` still blocks the packet.
- A new bounded live synthetic evaluation is required before treating the rubric update as accepted; previous results show label variance on repeated fixtures.
