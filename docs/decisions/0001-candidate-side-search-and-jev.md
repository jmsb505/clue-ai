# ADR 0001: Candidate-side search with Jev fit evaluation

**Status:** ACCEPTED for product direction  
**Date:** 2026-09-30

## Context

The owner wants a local personal app that accepts their CV and search parameters, searches current job listings, evaluates fit with TypeSafe AI's Jev model, and ranks results. The owner explicitly said the app is not meant to apply automatically and clarified that it is for their own use, not a service to scale. The owner remains the person deciding what to pursue.

Jev returns typed judgments with scores, probability distributions, and confidence. It does not write an explanation. A useful fit result therefore needs transparent evidence from the CV and job listing, as well as a way to display uncertainty.

## Decision

- The product is candidate-side job discovery and comparison, not employer-side applicant selection.
- The first version is a single-user local app; the CV, profile, preferences, listings, and results stay on the owner's device except for the minimum data sent to Jev for scoring.
- TypeSafe Jev is the fit-evaluation model required for job-to-profile validation.
- The product does not complete, submit, or answer job applications. Results link to the original employer or job-board page.
- Exact search rules and permissions stay in ordinary software. Jev's fit estimate is advisory and is not a hiring or interview probability.
- Show the basis and uncertainty of the score using the CV profile and posting evidence; do not present prose as if Jev generated it.

The model rubric, score aggregation, thresholds, and provider terms are not accepted by this decision; they remain subject to feasibility evidence and review.

## Alternatives considered

- **Automatic application product:** Rejected because it conflicts with the owner's no-apply requirement.
- **Employer-facing candidate scoring:** Rejected because the user described a candidate's own search and personal fit review.
- **Free-text LLM score explanation:** Not selected as the fit evaluator. It would not satisfy the required Jev evaluation step, and Jev itself does not generate prose.

## Rationale

The product is valuable when it helps a person spend attention on relevant listings and understand why a role might fit. Keeping the next action with the candidate preserves the requested workflow and avoids silently representing an advisory ranking as an employment decision.

## Consequences and risks

- The platform needs clear result evidence and user control over preferences.
- Scores can still be wrong, incomplete, or misleading; evaluate them and show uncertainty before the owner relies on them.
- Job listings can be expired, duplicated, or fraudulent; source provenance and freshness labels are needed.
- Sending candidate-derived profile data to TypeSafe creates processor, retention, and international-transfer questions. This decision does not resolve the legal basis or terms.
- If Jev's access or evaluation quality is unacceptable, pause the product decision and return to the owner; do not substitute another model without a new decision.

## Reversibility and reconsideration

The candidate-side boundary is reversible only by a new owner decision. Reconsider if the owner changes the product to support applications or employer use, if law or provider terms change the fit-evaluation design, or if benchmark evidence shows Jev is unsuitable for the ranking task.

## Evidence

- Owner request in the project kickoff, 2026-09-30: CV plus preferences, current listing search, Jev fit evaluation, ranked results, no automated applications.
- [TypeSafe Score documentation](https://docs.typesafe.ai/primitives/score) and [API reference](https://docs.typesafe.ai/api).
- [JevJobs live product page](https://jevjobs.ai/) and [Jobbie product page](https://jobbie.bot/) reviewed 2026-09-30.

## Affected source-of-truth documents

- `docs/product-definition.md`
- `docs/architecture/overview.md`
- `docs/readiness/definition-gate.md`
- `docs/roadmap.md`
