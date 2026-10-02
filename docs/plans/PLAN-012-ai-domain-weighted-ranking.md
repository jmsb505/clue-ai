# PLAN-012 — AI-domain-weighted ranking

**Status:** M1 implemented and statically validated; pushed to `main`
**Created:** 2026-10-02
**Last updated:** 2026-10-02

## Objective

Prioritize AI/ML-related roles in Jev's ranking while retaining other jobs that fit the candidate's profile, and fix the result-view count-key crash.

## Motivation

The owner wants the search to favor jobs from or directly related to AI, without losing other roles they could apply to based on their CV. A separate domain score makes that preference visible and adjustable. The results route also pluralizes `match` into the nonexistent key `matchs`, causing a `KeyError` when opening the match filter.

## Desired state

- Jev scores every retained listing on role alignment, skills, experience, AI/ML-domain relevance, and optional preferences.
- AI/ML relevance has the largest individual default weight. It relies on explicit role/product evidence, not the company name alone.
- AI/ML preference affects ranking only. It does not filter or hide non-AI roles that otherwise fit the profile.
- An unknown AI-domain assessment stays unknown and is not treated as a negative score.
- Users can adjust the domain weight on the search form and inspect it in each result's fit breakdown.
- Existing result views use explicit count keys, so `match` correctly reads `matches` and `conflict` reads `conflicts`.
- Completed old assessments remain snapshots; the new rubric is `fit-v1.3.0`.

## Scope

- Add a typed Jev fit dimension and independently combine its result using a saved weight.
- Set AI/ML domain relevance to `35` by default, above role (`25`), skills (`25`), experience (`10`), and optional preferences (`5`).
- Preserve customized weights and transition existing default-only saved searches to the new defaults.
- Display the AI-domain signal and explain that other profile-fit jobs remain eligible.
- Correct explicit match/review/conflict/unassessed result-count mapping.
- Update the product definition, definition gate, ADR, documentation index, and this plan.

## Out of scope

- Filtering job retrieval or result retention by AI keywords.
- Changing role-query discovery, source coverage, crawl policies, location, salary, junior/intern, or paid-only requirements.
- Changing TypeSafe model, consent, candidate fields sent, retry policy, or budget guard.
- Retrospectively rescoring completed prior searches, making live Jev calls, or running a source crawl.

## Milestone M1 — AI-focused fit dimension and result-view fix

### Implementation

- [x] Replace generated result-count plurals with an explicit status-to-count mapping.
- [x] Add Jev's independent AI/ML relevance `Choice` dimension with evidence and uncertainty guidance.
- [x] Combine AI relevance at the highest default individual weight while retaining profile dimensions.
- [x] Expose and explain the weight on search and per-listing results; keep the layout responsive.
- [x] Preserve user-customized old weights and move legacy defaults to the new AI-focused defaults.
- [x] Update product definition, definition gate, ADR 0013, docs index, and this plan.

### Acceptance criteria

- [x] Each newly assessed listing receives the AI/ML dimension as part of the same TypeSafe request as its other fit dimensions.
- [x] AI relevance is independent of profile-fit ratings and is weighted locally at `35/100` by default, the largest individual weight.
- [x] Clear AI/ML work can increase rank; high profile-fit roles outside AI remain present and can rank based on their other fit evidence.
- [x] Missing domain details produce `unknown`, not a zero or a hard-filter conflict.
- [x] Result breakdown names the signal “AI domain relevance”; the search form shows its adjustable weight and default values.
- [x] Existing completed results remain unchanged; new evaluations are versioned `fit-v1.3.0`.
- [x] Opening the Match and Conflict result views reads their correct counts without a `KeyError`.
- [x] Conda `gen` Ruff, Python byte-compilation, Jinja parsing, `git diff --check`, and code-path review pass.
- [x] No test suite, live crawl, or TypeSafe API request was run.

### Source-of-truth updates

- [Product definition](../product-definition.md)
- [Definition gate](../readiness/definition-gate.md)
- [ADR 0013](../decisions/0013-ai-domain-weighted-jev-ranking.md)
- [Documentation index](../README.md)

### Delivery

The owner has authorized validated milestones to be committed and pushed directly to `main`. Keep all pre-existing PLAN-007 search-history changes unstaged and preserve them exactly. Push the result-count bug fix as its own checkpoint before this feature's checkpoint.

## Validation and completion evidence

Conda `gen` Ruff passed for the changed Python modules and adjusted Jev expectations. Python byte-compilation passed for `domain.py`, `filters.py`, and `jev.py`. The search and results Jinja templates parsed; `git diff --check` passed. Code-path review confirmed that the fifth choice is included in Jev's request/parser, weighted in local score combination, kept separate from filter status and candidate retention, and shown in the results breakdown. No test suite, live crawl, live Jev request, or browser workflow was run. The result-count fix was pushed separately as `f78a045`; the AI ranking milestone is pushed in this checkpoint.
