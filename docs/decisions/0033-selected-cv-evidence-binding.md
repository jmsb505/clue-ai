# ADR 0033 — Selected-CV evidence binding for generated application material

Status: Accepted for the PLAN-020 M7 implementation
Date: 2026-10-07
Related: [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md), [ADR 0026](0026-jev-categorical-evidence-support.md), [ADR 0032](0032-jev-guided-cover-letter-repair.md)

## Context

The live `.20` IFOM packet failed its letter gate after Jev supported only one of two body paragraphs. The second paragraph made a candidate skill-level statement Jev could not establish. One targeted revision did not produce a supported replacement. The packet failed closed and produced no documents; Jev approved the unchanged tailored resume.

The underlying evidence path was incomplete. Recruiter received the selected CV and returned exact `cv_line_ids` for role criteria, but the Rewriter's content schemas and Jev grounding assertions could cite only approved or technical-profile `claim_ids`. A criterion mapped to CV text therefore could not be grounded through that same text. The Rewriter favored broad profile statements, while concrete project lines remained unavailable as citations.

## Decision

1. Generated factual blocks may cite `cv_line_ids` from the single CV explicitly selected for the preparation request, in addition to permitted `claim_ids`.
2. Clue resolves every CV line ID against that request's extracted line map, binds Jev's assertion to the exact line text and selected source, and removes blocks with invalid or out-of-snapshot IDs before Jev sees them.
3. Recruiter requirement linkage may use either mapped CV line IDs or mapped profile/approved claim IDs. A letter still needs two distinct mapped role criteria and two Jev-supported paragraphs before documents are created.
4. Apply the same exact CV-line evidence binding to resume edits, application-answer drafts, and outreach drafts. Each remains subject to Jev support and owner review.
5. Recruiter receives the selected technical profile as source-bound evidence excerpts rather than a duplicate full raw profile body. Rewriter and the letter repair receive only the exact technical-profile excerpts that Recruiter mapped to criteria. Descriptive-profile and writing-sample routing remains as previously defined.
6. Prefer concrete project evidence over a skills inventory or a development-level label. No wording rule can establish facts absent from the cited CV/profile text; Jev remains the factual-support decision-maker.

## Consequences

- A CV line can support generated text even when the owner has not separately promoted it into the evidence-bank claim workflow. The owner-provided source and Jev check remain visible in the dossier.
- The same role-to-candidate-evidence path now exists from Recruiter mapping through Rewriter citation, Jev review, and final document gating.
- Invalid IDs remain fail-closed. Existing two-paragraph quality and final-resume approval requirements are not relaxed.
- Removing duplicated technical-profile text reduces request size while preserving the exact evidence excerpts selected for the role. The change does not reduce context by silently truncating source text; it routes mapped excerpts to the generation stage.
- A Jev-supported paragraph is still not a measure of persuasive strength, voice, ATS behavior, or hiring outcomes. Owner review remains required.

## Validation evidence

PLAN-020 M7 records offline regression results and live listing retests. Acceptance remains pending until those checks, exact document inspection, and usage reconciliation are recorded.
