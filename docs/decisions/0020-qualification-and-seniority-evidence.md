# ADR 0020 — Show employer-qualification and seniority evidence

- Status: Accepted
- Date: 2026-10-05
- Decision owners: Clue owner

## Context

Jev already scores role, skills, experience, AI relevance, preferences, and the user's separate search filters. That does not tell the owner, item by item, whether the saved profile supports an employer's stated requirements or whether its experience level fits. A generic fit score can hide a mismatch between a role's concrete requirements and the candidate's documented experience.

## Decision

Keep fit score, filter compatibility, qualification comparison, and seniority comparison distinct:

1. A bounded local extractor selects up to four explicit qualification statements from each full listing. Statements under a required/qualification section or with explicit requirement language are labeled `required`; clearly preferred/nice-to-have/bonus language is labeled `preferred`. Required items are shown first. General responsibilities are not turned into requirements. If no discrete statement is found, record `no_explicit_requirements_detected`; this does not mean the employer has no requirements.
2. Ask Jev one typed question per extracted statement. Persist the exact statement, its priority and status: `met`, `partly_met`, `not_met`, or `not_enough_evidence`, plus confidence. `not_met` requires direct contradictory evidence in the candidate's parsed profile. Silence in the CV, incomplete profile evidence, or absent listing details mean `not_enough_evidence`.
3. Ask Jev a separate seniority question from the listing's explicit title/years/level evidence and the candidate's documented experience. Persist status `aligned`, `below_stated_level`, `above_stated_level`, or `not_enough_evidence`, with confidence and the listing evidence. Do not infer age or years from education dates.
4. Store the checks inside each `search_results.dimensions_json` snapshot. Display them inside the per-role Jev detail, along with the full listing description and publisher link. Keep prior runs readable; older result rows without these keys show no new fabricated assessment.
5. Describe all outputs as evidence comparisons, never a hiring probability. Keep the existing Jev opt-in and request budget; cap checks at four employer requirements plus one seniority answer per job. Do not pass the profile to source-board matching APIs.

The no-repeat ledger records a newly assessed URL only if every qualification and seniority question has a valid typed answer, in addition to the existing complete fit score and filter decision. An interrupted or incomplete evidence response remains eligible for reassessment. Historical rows created before this rubric have no qualification-assessment marker and retain their prior M1 completion behavior.

The Jev state treats all candidate, criteria, and job fields as untrusted data, not instructions. The existing minimized profile fields, search filters, and selected listing content are sent only under the app's existing user-controlled Jev opt-in. The raw CV file, direct contact details, and application link remain local.

## Consequences

- The owner can compare individual employer requirements and seniority with profile evidence rather than relying on a single filter label or score.
- Missing or unsupported evidence stays distinguishable from a contradiction.
- The parser may miss requirements in unusual formats or languages; results explicitly state when no requirements were extracted and keep the source listing available.
- More typed Jev questions may increase response size. The application keeps the existing $4 local rolling reserve within the owner's $5 ceiling and must leave results visible when that budget is exhausted.

## Validation limits

No live Jev call, CV, or listing was sent during implementation. Static compilation, linting, source review and template/code inspection are the evidence available for this milestone. Model judgment quality and extraction recall remain uncalibrated until the owner reviews actual results.
