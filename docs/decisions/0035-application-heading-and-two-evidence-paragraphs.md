# ADR 0035 — Application heading and two evidence paragraphs

**Status:** Accepted

**Date:** 2026-10-08
**Supersedes:** The three-generated-paragraph structure in [ADR 0034](0034-complete-cover-letter-argument.md). Jev grounding, source binding, final-CV review, manual action boundaries, and the local document scaffold remain unchanged.

## Context

The `.24` live IFOM run revealed that the cover-letter generator was required to produce an application-intent opening in addition to the role title that Clue already renders locally. The generated opening was not supported by Jev after one targeted repair, so the quality gate correctly produced no documents under that contract. The owner then supplied a clear reference form: a local “Application for [role] at [employer]” heading followed by two concise paragraphs. Each paragraph names a concrete project and states the specific listed responsibility that overlaps.

The generated opening added a first-person motivation claim that the technical profile did not support. It also duplicated application intent already expressed in the deterministic title. Jev remains the authority on factual support; it should not be asked to endorse personal motivation inferred from a project description.

## Decision

1. The deterministic renderer provides the application title and role context. GPT returns exactly two body paragraphs, both typed as `evidence`; no generated opening paragraph is required.
2. Each paragraph must cite candidate evidence, a distinct Recruiter-mapped job criterion, and the selected job source. Together, the paragraphs must use distinct candidate evidence and distinct role criteria.
3. A concise, explicit project-to-responsibility pairing is valid writing. Do not append generic claims that the example “connects,” “demonstrates fit,” or is “transferable.” Do not invent an owner action, result, motivation, or qualification.
4. Preserve distinctive project, method, model, hardware, and result details exactly when they appear in the bound candidate evidence. Keep each paragraph to at most two sentences and the body to at most 100 words.
5. A single targeted repair may address unsupported or low-quality paragraphs. Jev checks the final two-paragraph body again. Any missing paragraph, unresolved fact, failed structure, or unapproved CV still blocks document creation.
6. The DOCX renderer retains the selected-CV contact header, date, application title, salutation, polite close, sign-off, and source-derived candidate name. No external submission or outreach is performed.

## Consequences

- The expected form matches the owner's example while removing an unsupported generated-intent claim.
- Jev's factual decision remains separate from the deterministic structure/style checks and the saved Jev match.
- The quality gate can establish evidence support, paragraph count, distinctness, role-source links, length, and known repetition patterns. It cannot certify persuasiveness, personal voice, ATS performance, or hiring outcomes.
- The exact generated files still require owner review before any application or outreach action.

## Validation

The two-paragraph schema has synthetic regression coverage for direct project-to-responsibility examples, distinct candidate evidence, unsupported evidence, bounded repair, and local title rendering. The `.32` IFOM packet passed its v10 rubric, both Jev paragraph-support decisions, final-CV approval, and one-page Word/Poppler rendering; owner review then found its repeated “role includes” lists and generic evidence selection unsatisfactory. [ADR 0036](0036-specific-project-evidence-and-direct-role-links.md) records the refinement. Prompt `.35` passes focused offline tests; live validation is pending because the subsequent `.34` retry stopped at token-count preflight on a local DNS error. See [PLAN-020 evaluation results](../evaluations/PLAN-020-evaluation-results.md).
