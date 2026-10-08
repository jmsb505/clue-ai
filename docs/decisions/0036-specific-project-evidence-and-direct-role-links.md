# ADR 0036 — Prefer specific project evidence and direct role links

**Status:** Accepted

**Date:** 2026-10-08
**Related:** [ADR 0035](0035-application-heading-and-two-evidence-paragraphs.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md)

## Context

The `.32` IFOM packet passed its mechanical quality gate, Jev support for both cover-letter paragraphs, and Jev's separate final-CV decision. The owner-facing letter still fell short: both paragraphs ended with formulaic lists introduced by “IFOM's role includes,” and the selected evidence favored general workflow/tool claims over two named technical-profile projects. The exact one-page document rendered without clipping, so this was a writing and evidence-selection failure rather than a document-integrity failure.

The output exposed two gaps. First, the evidence selector could spend its limited slots on broad skill statements even when the role map matched distinctive project claims. Second, the quality rubric treated a factual project paragraph plus a factual job-duty list as a complete cover-letter argument.

## Decision

1. Rank specific, role-relevant project claims ahead of generic skill summaries when selecting evidence for the two cover-letter paragraphs. Keep generic claims eligible when they are the best supported match; do not drop them from the underlying profile.
2. Each paragraph must state one specific piece of candidate work and link it to one distinct mapped job responsibility in natural, direct language. Reject repetitive formulations such as “the role includes [technology list]” and repair them once using only bound evidence and role sources.
3. Keep the local application heading and document scaffold. Require distinct candidate evidence and distinct role criteria, then rerun Jev support over the repaired final paragraphs. This writing refinement cannot change Jev's saved job-fit decision or final-CV approval rules.
4. Apply the 100-word body ceiling and keep unsupported facts, invented metrics, generic relevance bridges, and repeated examples out of the letter. The mechanical gate checks known patterns; it does not claim to measure persuasion or personal voice.
5. Align wrapped resume bullet lines under their text with a hanging indent to preserve readable structure when a tailored bullet wraps.

## Consequences

- Role-relevant named projects become more likely to anchor the cover letter while the full selected profile remains available to authorized stages.
- Jev remains the factual entailment validator, but passing Jev alone is explicitly insufficient for writing-quality acceptance.
- The revised selector and rubric require live retesting on the individually selected listing. Until that succeeds, `.35` has offline evidence only.
- Clue still creates drafts for owner review. It does not send outreach or submit an application.

## Validation

Focused offline regressions cover named-project ranking, the direct two-sentence owner example, formulaic role-list repair, paragraph evidence separation, Jev recheck, and resume hanging indents. At this ADR's checkpoint, the full repository suite passed 329 tests in 63.86 seconds; Ruff, `compileall`, and `git diff --check` passed. The `.34` manual retry stopped before generation when exact token-count preflight could not resolve `api.openai.com`, so `.35` had no live output at that time. The subsequent `.38` live result is documented in [ADR 0037](0037-first-person-project-evidence-in-cover-letters.md) and the current [PLAN-020 evaluation results](../evaluations/PLAN-020-evaluation-results.md).
