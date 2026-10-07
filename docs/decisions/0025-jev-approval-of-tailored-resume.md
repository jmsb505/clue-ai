# ADR 0025 — Jev approval of the tailored resume

Status: Accepted
Date: 2026-10-07
Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0024](0024-model-aware-token-budgeting.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md)

## Context

The existing Jev result approves the original candidate/job match before generation. A separate Jev evidence-support check reviews each generated factual block. Neither check established that the *final tailored resume* remained relevant to the selected job after GPT editing. A live synthetic run also demonstrated that a cover letter whose generated paragraphs were all omitted could still be stored as a reviewable packet.

The first implementation added a final Jev resume-fit decision, but also rejected Jev's explicit `approved` label when its reported confidence was below 0.50. The live synthetic response showed that this self-reported value can diverge from the discrete decision, and no calibration evidence justified the second threshold.

## Decision

After per-listing generation and factual grounding, Clue makes a separate Jev request with the exact saved listing, read-only original Jev snapshot, source CV, final tailored resume, and evidence attached to each retained resume edit. Jev returns `approved`, `revise`, or `unresolved`. Only the explicit `approved` label allows the workflow to proceed. Jev's confidence is retained as diagnostic metadata and does not override its discrete result.

The final resume-fit review does not update or recompute the original job match, ranking, filter, qualification, or eligibility fields. The existing Jev evidence-support request remains a separate decision and every included factual block must pass it.

Before rendering, Clue also requires at least two non-empty Jev-supported cover-letter body paragraphs. Each paragraph must have a candidate-evidence or explicit owner-preference reference and a verified public role-source URL; at least one paragraph must cite candidate-experience evidence. If the final resume is not approved or the cover letter fails this quality gate, Clue stores a non-reviewable packet report, records the failed reason, and creates no document artifacts.

## Consequences

- GPT remains the generation and editing agent; Jev remains the decision authority for original fit and final tailored-resume approval.
- The original Jev match record is immutable during preparation. Packet output stores the final resume decision under its own rubric version.
- Model confidence remains visible for evaluation but cannot act as a second, uncalibrated approval rule.
- A generated packet may fail even after every API call succeeds. The local failure report preserves the decision and quality results; no empty cover letter is offered for approval.
- The manual per-listing trigger, owner review, local-only artifacts, and manual outreach/application actions remain in force.

## Validation status

- Unit tests cover explicit approval, revise/unresolved decisions, malformed responses, and proof that the saved Jev match is unchanged.
- Workflow tests cover successful reviewable packets and failure reports with no artifacts when Jev or letter quality rejects the packet.
- Unit and workflow tests cover explicit approval, revise/unresolved decisions, malformed responses, unchanged saved match, and no-artifact failure packets; the full repository suite passed (272 tests).
- A bounded synthetic end-to-end run approved the tailored resume, passed packet quality, reopened both DOCX artifacts, and settled three Jev requests and five GPT calls. Two of three factual blocks were supported; the unsupported block was omitted. The latest DOCX files were not visually rendered.
- Exact-packet owner review, broader role/portfolio coverage, and at most one real owner-selected listing remain separate acceptance gates.
