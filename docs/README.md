# Project documentation

**Status:** PLAN-002 M1/M2 pushed and remote-verified on `main`; PLAN-001 M2 locally validated and awaiting its separate `main` checkpoint
**Research snapshot:** 2026-09-30

This repository contains the local personal job-search app, its product definition, source research, architecture, and delivery plans. PLAN-002 M1 and the separate M2 synthetic Jev acceptance checkpoint are pushed to `main`; PLAN-001 M1 is also pushed. PLAN-001 M2 passed local validation and is being prepared as a separate `main` checkpoint. The owner directs each validated milestone to be committed and pushed to `main`; do not create milestone branches or bypass repository protections. Each external source has its own use, attribution, and refresh conditions.

## Authority map

| Question | Authority |
|---|---|
| What the product should do and what it must not do | [Product definition](product-definition.md) |
| What the two reference products and job-search sources show | [Market and reference review](research/market-and-reference-review.md) |
| What free job sources are candidates and how selected Scrapling crawling will work | [Source discovery and crawl review](research/source-discovery-and-crawl-review.md) |
| Local system boundaries, data flow, and implementation state | [Architecture overview](architecture/overview.md) |
| Whether the personal local app is defined and what remains before real-CV use | [Definition gate](readiness/definition-gate.md) |
| Work order and implementation milestone | [Roadmap](roadmap.md), [PLAN-001](plans/PLAN-001-free-local-source-discovery.md), and [PLAN-002](plans/PLAN-002-local-first-job-search-app.md) |
| Decision history | [Decisions](decisions/) |

The product definition records owner requirements separately from local-use defaults. Research reviews are dated external evidence; source conditions remain per-provider and per-geography. The definition gate passes for a single-user local build. A synthetic Jev API request has verified the technical integration, while provider terms, source behavior, and ranking evidence remain open before the owner's real CV is used. ADR 0004 records the local-only scope.

## Status labels

- **NORMATIVE** — current intended product behavior, based on an explicit owner decision.
- **WORKING** — a proposed design or plan that still needs validation or owner decisions.
- **EVIDENCE** — observed implementation, source material, or validation results.
- **REFERENCE** — external context that informs decisions but does not set requirements.
- **HISTORICAL** — superseded decision or plan retained for its history.

Use `PASS`, `PARTIAL`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE` in the definition gate. A decision record keeps prior choices and reasons; update it by superseding the old decision rather than erasing history.
