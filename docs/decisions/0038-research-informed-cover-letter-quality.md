# ADR 0038 — Research-informed, flexible cover-letter quality

**Status:** Accepted  
**Date:** 2026-10-11  
**Related:** [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0034](0034-complete-cover-letter-argument.md), [ADR 0035](0035-application-heading-and-two-evidence-paragraphs.md), [ADR 0036](0036-specific-project-evidence-and-direct-role-links.md), [ADR 0037](0037-first-person-project-evidence-in-cover-letters.md), [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md)

## Context

The owner rejected generated text that read like a short project note. The example supplied for comparison demonstrates the kind of concise, evidence-led connection the owner values; it does not define a required word count, paragraph count, or section sequence. Earlier revisions had turned examples into exact format and evidence-count gates, which could reward a template over a useful argument.

Career-service guidance reviewed for this decision consistently recommends tailoring a letter to the employer and role, grounding the case in relevant experience, and keeping it concise. MIT CAPD advises researching the employer and position, explaining relevant experience beyond repeating resume content, and explicitly connecting examples to the role. Oxford Careers describes the letter as a story that complements the CV, asks applicants to explain why the job and organization interest them, and recommends relevant, evidence-backed accomplishments linked to job criteria. The seven primary university sources in the [research report](../evaluations/cover-letter-research-and-validation.md) offer business-letter moves and roughly one-page guidance for ordinary applications; these are common practices, not universal word or paragraph quotas. The useful quality bar is whether the prose develops a credible, role-specific case. A few compressed achievement notes may be too thin even when their facts are relevant, while a concise letter can pass when it explains the candidate's contribution and why that experience matters to the role.

## Decision

1. Treat the owner's sample as a quality reference only. Do not require an exact word count, paragraph count, or rhetorical-section sequence. Around one page is practical guidance for an ordinary industry letter, not a pass/fail boundary.
2. Ask GPT-6 Luna to write a complete, role-specific argument in the owner's direct, modest voice. Develop relevant experience beyond resume-like claims by explaining the evidenced contribution, meaningful context or approach, outcome where known, and how that experience prepares the candidate for advertised work. The body must introduce the application, develop relevant evidence, explain the particular application rationale, and conclude professionally; these functions may share paragraphs. The signature cannot replace a conclusion. Use one strong example when that is enough; use additional examples only when each contributes distinct, relevant evidence. Tailor the letter using verified role facts and the selected technical/descriptive profile material when it adds supported value. Do not invent motivation or pad the letter.
3. Keep source validation deterministic. Every factual paragraph must cite exact candidate evidence and a Recruiter-mapped role requirement; Jev checks every final factual paragraph against the cited evidence and selected listing. At least one concrete candidate example is required. A role-only paragraph may be used when it has a valid listing source and mapped requirement. Jev treats requests to discuss the application and thanks as communicative acts, while still requiring evidence for any accompanying factual assertion, motivation, availability, prior contact, or promised commitment.
4. Add a separate GPT writing-quality review with five dimensions: completeness, role/employer tailoring, candidate-evidence development, argument coherence, and voice/clarity. The reviewer must distinguish a developed application argument from a few short project notes; relevance alone does not make a letter complete. It judges this by the explanation in the prose, never by word or section counts. Every dimension must score at least 3/4, with no material unresolved issue, before a packet is reviewable. At most two bounded source-aware revisions are allowed. Every revision is followed by writing review and a complete Jev evidence recheck. A second revision repairs a gap revealed by final validation; supported paragraphs remain locked and paragraph IDs are rebased after omissions. Failure after the bounded attempts prevents document generation.
5. Keep Jev's saved job match immutable and distinct from both the factual-support check and Jev's separate approval of the final tailored CV. Generate local documents only after all gates pass. The owner reviews the final packet and performs every submission or outreach action.

6. Use descriptive project titles throughout generated CVs, cover letters, and outreach drafts. Do not insert candidate project brands or repository names. Retain original labels only in internal source metadata for traceability; relevant model, method, and hardware details can remain. This supersedes earlier visible project-name requirements.

## Consequences

- Rewriter and repair schemas treat the `section` value as optional internal metadata. It is never printed as a document heading and does not determine letter acceptance.
- The deterministic letter gate records word, paragraph, and section-label counts as diagnostics, but does not use those counts as quality thresholds. It checks evidence, sources, attribution, role links, repetition, and known clarity issues.
- The writing reviewer evaluates the complete application case rather than a template. It checks whether examples are explained and connected to the work, rather than merely repeated as resume bullets or compressed project notes. Its review is separate from Jev's factual and matching decisions.
- The career-service sources inform guidance; they do not guarantee ATS performance, interviews, or hiring outcomes. The owner remains the final judge of personal voice and suitability.
- Earlier exact two-example and exact-section contracts in ADRs 0034–0037 are superseded where they prescribe a required letter shape or minimum evidence count. Their factual-grounding, direct-action, technical-detail, Jev, and human-review safeguards remain in force.

## Validation

The focused workflow suite and live end-to-end packet evidence are recorded in [PLAN-021](../plans/PLAN-021-evidence-led-generation-quality.md) and the [PLAN-020 evaluation report](../evaluations/PLAN-020-evaluation-results.md). The submitted example remains a reference, not a format threshold.

## Research

- [MIT CAPD — How to Write an Effective Cover Letter](https://capd.mit.edu/resources/how-to-write-an-effective-cover-letter/)
- [MIT CAPD — Career Toolkit: Writing a Cover Letter](https://capd.mit.edu/resources/career-toolkit-writing-a-cover-letter/)
- [Oxford Careers — Cover letters](https://www.careers.ox.ac.uk/node/768226)
