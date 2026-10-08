# ADR 0034 — Complete, evidence-led cover-letter structure

- Status: Accepted for PLAN-021 M5 implementation
- Date: 2026-10-07
- Related: [ADR 0032](0032-jev-guided-cover-letter-repair.md), [ADR 0033](0033-selected-cv-evidence-binding.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md)

## Context

The `.20` IFOM output placed a candidate project fact beside a job duty and called that a connection. One of its two paragraphs was not supported by Jev, so the request failed safely. Earlier letters that Jev did support were still sparse and lacked an application opening and document scaffolding. The mechanical gate measured citations, source support, and paragraph count; it did not require a complete letter argument.

The owner provided an authored cover-letter example with a contact header, date, role heading, salutation, direct role-specific opening, distinct project examples, an explanation of the candidate's working approach, and a courteous close. The example sets structure and voice expectations only; its personal facts are not copied into generated applications. Jev remains the authority for factual entailment, not persuasive writing or job matching.

## Decision

1. GPT-6 Luna returns a three-paragraph body: one application opening and two evidence paragraphs. The opening names the employer and role and states a specific reason tied to supported candidate work. Each evidence paragraph develops a different project with source-supported context, owner action, method or result, and a precise relationship to listed role work.
2. Every generated paragraph cites its exact candidate evidence, a matching Recruiter-mapped requirement, and the selected listing or verified research source. Jev checks every final paragraph. Repair remains bounded to one Letter Reviser call, and Jev rechecks the complete revised letter.
3. The local completeness gate requires the opening and two distinct evidence sections, clear application intent, source links, distinct project evidence, and no repeated or known formulaic role-duty boilerplate. It has no minimum word-count threshold. A pass is not a guarantee of persuasive strength or personal-voice acceptance; the owner reviews the exact packet.
4. The DOCX renderer builds a complete letter around the generated body: name and concise contact lines from the selected CV header when present, current date, role heading, generic salutation, polite closing sentence, sign-off, and source-derived name. The model does not invent contact details.
5. These quality changes do not change the saved Jev match, fit, eligibility, filters, or final-CV decision. No generated text is submitted, and no message is sent.
6. Route model calls and any revisions through the existing per-stage token preflight, Clue-local spend reservation, and usage settlement. Do not modify OpenAI or Jev provider-side settings or caps.

## Consequences

- A packet with only paired candidate/role sentences no longer passes solely because Jev supports each fact. Missing openings, duplicate project evidence, and the known "also an explicit part of the role" formula trigger one targeted quality repair or fail closed.
- A third body paragraph increases Rewriter output and Jev support work. The existing Rewriter and Letter Reviser allowances are measured in live evaluation; provider account limits remain unchanged.
- A supported document is structurally complete and evidence-linked, but still needs owner review for persuasiveness, voice, ATS behavior, and hiring outcomes.

## Validation

- Offline regression coverage includes complete-section requirements, opening intent, distinct candidate evidence, the known boilerplate pairing, bounded quality repair, full final Jev recheck, and exact CV-header contact rendering.
- Live validation for GPT-6 Luna at `high`, Jev support, final-CV approval, rendered DOCX inspection, and usage settlement is recorded in [PLAN-020 evaluation results](../evaluations/PLAN-020-evaluation-results.md) and remains pending until completed.
