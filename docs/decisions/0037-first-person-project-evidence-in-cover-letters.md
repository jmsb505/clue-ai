# ADR 0037 — Require direct owner action in preferred-project letter examples

**Status:** Accepted

**Date:** 2026-10-08
**Related:** [ADR 0035](0035-application-heading-and-two-evidence-paragraphs.md), [ADR 0036](0036-specific-project-evidence-and-direct-role-links.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md)

## Context

The `.32` IFOM letter passed Jev's factual-support checks and the then-current mechanical rubric, but the owner rejected its generic role-duty lists and weak project selection. Prompt `.38` improved project selection, but the live `.37` retry still described preferred work indirectly and omitted distinctive deployment details. The owner supplied a compact reference: a direct first-person project statement followed by a sentence naming the corresponding advertised responsibility.

The defect was not just factual support. A letter can be true, supported, and structurally complete while still failing to say what the candidate personally did in a useful application voice.

## Decision

1. For each preferred technical-profile example, the Rewriter starts with a direct first-person action in the first sentence. It cites a CV line or exact profile claim that attributes the action to the owner.
2. Preserve distinctive supported project, model/method, and named deployment-target details when relevant to the advertised responsibility. Do not replace a specific deployed system with a broad later summary.
3. State one distinct advertised responsibility directly in each paragraph. The owner-provided compact example is a style pattern, not permission to copy a fact into a letter without source binding.
4. The deterministic quality gate checks first-person action, preferred-profile detail, evidence mapping, distinct role requirements, length, and repetition. Jev still checks factual entailment and separately decides whether to approve the final CV. Neither Jev decision can change the saved job match.
5. Keep exact-packet owner review mandatory. A passed rubric and Jev support do not certify persuasion, personal voice, ATS performance, or hiring outcomes.

## Consequences

- Prompt `.38` produced a live IFOM letter in the owner's compact two-example format and passed the v13 writing gate.
- Zero CV bullet edits were retained in this run. Jev's final-CV approval is not evidence that the CV was materially tailored.
- Research found a public general recruitment inbox, but the Rewriter produced no outreach draft. Contact research and outreach drafting remain separate quality gaps.
- The saved IFOM result stayed `review`; document generation and the separate Jev decisions do not change matching or eligibility.
- The test changed only Clue-local OpenAI request caps. Provider-account settings and caps were not changed.

## Validation

The live `.38` run completed five GPT-6 Luna calls at `high`; Jev supported both letter paragraphs and separately approved the final CV. Both DOCX files were exported through read-only Microsoft Word and rasterized with Poppler for inspection. The cover letter rendered as one clean page; the resume rendered as two pages with a sparse second page and no clipping. The full repository suite passed 333 tests; Ruff, Python byte-compilation, and `git diff --check` passed. See the sanitized [PLAN-020 evaluation](../evaluations/PLAN-020-evaluation-results.md).
