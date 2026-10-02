# PLAN-011 — Entry-level, paid roles with direct listing links

**Status:** M1 implemented, statically validated, and pushed to `main` in `4e64f5e`
**Created:** 2026-10-02
**Last updated:** 2026-10-02

## Objective

Make Clue focus on junior and intern positions, require paid work, and provide an obvious link to each specific job listing.

## Motivation

The owner clarified that the intended search is for entry-level roles: junior jobs or internships, and the positions must be paid. The ranked results also need to take the owner directly to the job posting. These are core search requirements, not optional preferences.

## Current state

- Search criteria have no explicit career-level or paid-work requirement.
- Jev receives title, description, employment type, and structured salary fields, but its filter rubric does not mention junior/intern roles or whether the role is paid.
- The full active, non-hidden listing set is retained for Jev under ADR 0010; filter disagreements and unknowns must remain visible.
- Result cards contain source URLs in a small source trail, but do not offer a prominent, consistently labeled job-listing action.

## Desired state

- Every new search carries `junior_or_intern` seniority and `paid_only` as required criteria.
- Jev treats explicit junior/entry-level roles and internships as in-scope; explicit mid/senior roles conflict. Unclear seniority needs review.
- Paid salary, hourly wages, stipends, or other stated monetary compensation satisfy the paid requirement. Explicit unpaid or volunteer work conflicts. If pay is unclear, Jev marks the listing for review and never calls it a filter match.
- All collected candidates remain in the run. These criteria affect Jev's assessment, not pre-Jev retrieval or result retention.
- Every result card has a clear, safe external link to the posting URL supplied by its source. Publisher attribution remains visible.

## Scope

- Add the fixed entry-level and paid-only criteria to the saved search model and Jev state.
- Update Jev's typed filter assessment instructions for these criteria and unknown evidence.
- Explain the requirements on the search form and make the original listing URL a clear result action.
- Update the product definition, definition gate, ADR, documentation index, and this plan.

## Out of scope

- Changing search geography, role families, source coverage, crawl limits, or source refresh intervals.
- Removing candidates before Jev or hiding `review`, `conflict`, or `unassessed` results.
- Adding a new model, compensation parser, paid data feed, or application-submission feature.
- Automatically treating absent compensation details as proof that a job is unpaid or paid.

## Source-of-truth impact

- [Product definition](../product-definition.md) and [Definition gate](../readiness/definition-gate.md) record the entry-level, paid-only search requirements and per-listing source link.
- [ADR 0012](../decisions/0012-entry-level-paid-job-criteria.md) records their assessment semantics.
- Update [docs index](../README.md) and this plan with implementation and validation evidence.

## Existing decisions and constraints

- ADR 0010 requires Jev to assess every active, non-hidden candidate and keep conflicts and uncertainty visible.
- The app is local and personal; external spending remains limited to the existing TypeSafe Jev reserve.
- A result's source URL must point to a specific listing page and be opened by the user; Clue does not apply on the user's behalf.
- The owner has authorized validated milestone pushes directly to `main`; preserve unrelated working-tree changes and do not create a branch.
- Do not invoke a live crawl or Jev request while implementing this milestone.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, and `ponytail-balanced`.
- Conda `gen`, Ruff, Python byte-compilation, Jinja template parsing, and `git diff --check` for static validation.

## Dependencies

- Existing `SearchCriteria` persistence and Jev search-filter question.
- Existing per-result source URL records and safe external-link conventions.

## Risks and unknowns

- Listings often omit pay details. They remain available as `review` and must not be represented as confirmed paid matches.
- Seniority labels vary. Jev should use title and responsibility evidence and mark ambiguous cases `review` rather than overclaiming.
- Saved runs retain their original criteria and assessments; the new rubric applies to new searches, with no silent retroactive rescore.
- A source may not provide a specific posting URL. The result should communicate that the listing link is unavailable rather than link to a generic search page.

## Milestones

### M1 — Persist and assess the required criteria; expose the listing link

**Goal:** Make junior/intern and paid work mandatory search criteria for Jev, while preserving every candidate and linking each result to its posting.

**Subtasks:**

- [x] Add stable search criteria values for junior/intern roles and paid-only work.
- [x] Include both requirements in the Jev state and typed filter rubric with explicit conflict/review semantics.
- [x] Explain the fixed requirements on the search form without presenting them as optional filters.
- [x] Add a clearly labeled per-result link to the specific source listing, retaining source attribution and safe link attributes.
- [x] Update product definition, definition gate, ADR 0012, docs index, and plan progress.

**Affected areas:** `clue_ai/domain.py`, `clue_ai/filters.py`, `clue_ai/jev.py`, `clue_ai/templates/home.html`, `clue_ai/templates/search.html`, `clue_ai/templates/results.html`, and product/decision/plan documentation.

**Dependencies:** Existing Jev fit/filter assessment flow and `job_sources.source_url`.

**Acceptance criteria:**

- [x] New and repeated searches persist `junior_or_intern` and `paid_only` criteria without trusting client-posted values for these fixed requirements.
- [x] Jev receives both criteria and instructions to classify explicit unpaid or out-of-level roles as `conflict`, unclear facts as `review`, and confirmed qualifying roles as `match` if all other hard filters match.
- [x] Every collected listing remains in its search snapshot regardless of the Jev label.
- [x] The search form clearly states the role-level and paid-work requirements.
- [x] The CV-first start page discloses the default junior/intern, paid-only search criteria.
- [x] Each result exposes its specific posting URL as an obvious external action; link targets are escaped and use `noopener`/`noreferrer`.
- [x] Existing source trail continues to identify the publisher; unavailable listing links are not replaced with generic source-homepage URLs.
- [x] Source-of-truth docs consistently record the intended requirements and uncertainty handling.

**Validation:**

- [x] Ruff and Python byte-compilation pass for changed Python modules in Conda `gen`.
- [x] Changed Jinja templates parse successfully and `git diff --check` passes.
- [x] Code-path inspection confirms these criteria are passed to Jev and never gate candidate retention.
- [x] No job crawl, Jev API call, or test suite is run for this milestone.

**Documentation updates:** Product Definition, Definition Gate, ADR 0012, docs index, and this plan.

**Applicable specialized skills:** `ponytail-balanced`, `milestone-delivery`.

**Expected Git checkpoint:** One scoped commit on `main`, pushed after applicable local static validation. Keep unrelated PLAN-007 work unstaged.

## Final integration validation

Conda `gen` Ruff, byte-compilation, Jinja parsing, both staged and working-tree diff checks, code-path inspection, and the scoped push to `origin/main` at `4e64f5e` are complete. No crawl or TypeSafe request was triggered.

## Rollback / recovery

Revert the scoped M1 commit to remove the two criteria and result action. The criteria are additive JSON fields with defaults, so no database migration or row rewrite is required. Preserve local search records and job-source URLs.

## Progress

- [x] Confirmed the existing code supports full-candidate Jev evaluation and persists per-source listing URLs.
- [x] Recorded the owner's fixed entry-level and paid-only requirements and the need for an obvious listing link.
- [x] Implement and statically validate M1; push the scoped checkpoint directly to `main` (`4e64f5e`).

## Implementation discoveries / decisions

- “Paid” means explicit monetary compensation, including a wage, salary, stipend, commission, or other stated paid arrangement. Equity-only, unpaid, and volunteer roles do not satisfy the requirement; omitted or contradictory pay evidence requires review or conflict as specified in ADR 0012.
- An ambiguous level or unclear pay cannot be promoted to a filter match. Keep it in the run for the owner to inspect.
- The listing URL is the specific `source_url` provided for that job observation, not the source's generic home or search page.
- The Jev rubric version is now `fit-v1.2.0`; previously saved result snapshots keep their stored assessment and only show the new criteria labels when those criteria were saved with the run.

## Completion evidence

Conda `gen` Ruff passed for `domain.py`, `filters.py`, `jev.py`, and the updated Jev version assertion; byte-compilation passed for the changed Python modules; Jinja parsed the home, search, and results templates; staged and working-tree `git diff --check` passed. Code inspection confirmed that request parsing hard-codes the required criteria, the saved dataclass includes them, Jev receives both, and result collection is not gated by them. Commit `4e64f5e` was pushed to `origin/main`. No unit suite, crawl, Jev request, or live browser workflow was run.
