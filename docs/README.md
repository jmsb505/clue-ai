# Project documentation

**Status:** WORKING  
**Research snapshot:** 2026-09-30

This workspace has no application code yet. These documents define the product and a bounded local feasibility pilot. Each source has its own use, attribution, and refresh conditions.

## Authority map

| Question | Authority |
|---|---|
| What the product should do and what it must not do | [Product definition](product-definition.md) |
| What the two reference products and job-search sources show | [Market and reference review](research/market-and-reference-review.md) |
| What free job sources are candidates and how selected Scrapling crawling will work | [Source discovery and crawl review](research/source-discovery-and-crawl-review.md) |
| Proposed boundaries and data flow | [Architecture direction](architecture/overview.md) |
| Whether the personal local app is defined and what remains before real-CV use | [Definition gate](readiness/definition-gate.md) |
| Work order and first increment | [Roadmap](roadmap.md) and [PLAN-001](plans/PLAN-001-free-local-source-discovery.md) |
| Decision history | [Decisions](decisions/) |

The product definition records owner requirements separately from local-use defaults. Research reviews are dated external evidence; source conditions remain per-provider and per-geography. The definition gate passes for a single-user local build, while TypeSafe terms, source behavior, and ranking evidence still need checks before the owner's real CV is used. ADR 0004 records the local-only scope.

## Status labels

- **NORMATIVE** — current intended product behavior, based on an explicit owner decision.
- **WORKING** — a proposed design or plan that still needs validation or owner decisions.
- **EVIDENCE** — observed implementation, source material, or validation results.
- **REFERENCE** — external context that informs decisions but does not set requirements.
- **HISTORICAL** — superseded decision or plan retained for its history.

Use `PASS`, `PARTIAL`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE` in the definition gate. A decision record keeps prior choices and reasons; update it by superseding the old decision rather than erasing history.
