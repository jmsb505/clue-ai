# Project documentation

**Status:** PLAN-001 M1/M2, M3a, and M3b pushed and remote-verified; PLAN-002 M1/M2 and PLAN-003 M1 are pushed. PLAN-004 M1 (CV-first automatic search and Jev review) is pushed and remote-verified at `ea2b73ab53580acee1558b56c2832d50cd4b4e8f`. PLAN-005 M1 (local-origin form fix and Fetch Metadata follow-up) is pushed and remote-verified at `b3b1bc56843866d0cffd8dc834fd93430956b217`. PLAN-008 has one successful live run (718 records fetched; two matches scored); incremental progress display awaits a post-fix run.
**Research snapshot:** 2026-10-02

This repository contains the local personal job-search app, its product definition, source research, architecture, and delivery plans. PLAN-002 M1/M2 and PLAN-001 M1/M2/M3a/M3b are pushed to `main`; M3b's verified SHA is recorded above. PLAN-008's first live workflow completed; its sitemap stage took about 97 seconds, and its progress display is being improved. The owner directs each validated milestone to be committed and pushed to `main`; do not create milestone branches or bypass repository protections. Each external source has its own request limits, attribution, and refresh cadence.

## Authority map

| Question | Authority |
|---|---|
| What the product should do and what it must not do | [Product definition](product-definition.md) |
| What the two reference products and job-search sources show | [Market and reference review](research/market-and-reference-review.md) |
| What free job sources are candidates and how selected Scrapling crawling will work | [Source discovery and crawl review](research/source-discovery-and-crawl-review.md) and [ADR 0009](decisions/0009-broader-local-public-crawling.md) |
| Local system boundaries, data flow, and implementation state | [Architecture overview](architecture/overview.md) |
| Whether the personal local app is defined and what remains before real-CV use | [Definition gate](readiness/definition-gate.md) |
| Work order and implementation milestone | [Roadmap](roadmap.md), [PLAN-001](plans/PLAN-001-free-local-source-discovery.md), [PLAN-002](plans/PLAN-002-local-first-job-search-app.md), [PLAN-004](plans/PLAN-004-cv-first-automated-search.md), [PLAN-008](plans/PLAN-008-broader-public-crawling.md), [PLAN-009](plans/PLAN-009-full-candidate-jev-assessment.md), [PLAN-010](plans/PLAN-010-stop-crawls-with-app.md), [PLAN-011](plans/PLAN-011-entry-level-paid-role-filters.md), and [PLAN-012](plans/PLAN-012-ai-domain-weighted-ranking.md) |
| Manual X search and job-lead handoff | [PLAN-003](plans/PLAN-003-x-manual-leads.md) and [ADR 0007](decisions/0007-x-manual-lead-discovery.md) |
| CV-first upload, automatic search, and Jev trigger | [ADR 0008](decisions/0008-cv-first-automatic-search.md) |
| Full candidate-set Jev assessment | [ADR 0010](decisions/0010-full-candidate-jev-assessment.md) and [PLAN-009](plans/PLAN-009-full-candidate-jev-assessment.md) |
| Stop active crawls and mark interrupted searches | [ADR 0011](decisions/0011-stop-crawls-with-app.md) and [PLAN-010](plans/PLAN-010-stop-crawls-with-app.md) |
| Require junior/intern paid roles and direct listing links | [ADR 0012](decisions/0012-entry-level-paid-job-criteria.md) and [PLAN-011](plans/PLAN-011-entry-level-paid-role-filters.md) |
| Prioritize AI/ML-related roles while retaining profile-fit jobs in other domains | [ADR 0013](decisions/0013-ai-domain-weighted-jev-ranking.md) and [PLAN-012](plans/PLAN-012-ai-domain-weighted-ranking.md) |
| Reset local search state and broaden matching with inspectable requirements | [ADR 0014](decisions/0014-practical-matching-and-clean-slate.md) and [PLAN-014](plans/PLAN-014-clean-slate-and-practical-matching.md) |
| Add a bounded Tech Europe Jobs source and review similar European job boards | [ADR 0014](decisions/0014-techeurope-public-job-source.md) and [PLAN-013](plans/PLAN-013-techeurope-and-european-sources.md) |
| Synthetic Jev ranking evidence | [PLAN-001 M3a evaluation](evaluations/PLAN-001-M3-synthetic-jev.md) |
| Manual local backup and deletion scope | [Backup and deletion guide](operations/local-data-backup-and-deletion.md) |
| Decision history | [Decisions](decisions/) |

The product definition records owner requirements separately from local-use defaults. Research reviews are dated external evidence; source conditions remain per-provider and per-geography. The definition gate passes for a single-user local build. M3a's synthetic benchmark verifies one-batch scoring, filters, and evaluation metrics; Jev tied the simple keyword baseline on assistant-authored labels, so personal relevance remains open. M3b tested local deletion and manual backup/restore using synthetic data. The owner waived TypeSafe account/terms checks and device-encryption confirmation; those facts remain unverified. Source approvals and spoken screen-reader review remain open. ADR 0004 records the local-only scope.

PLAN-003 records the manual-only X search handoff. X is not fetched, scraped, or included in scheduled connector coverage. The CV-first search flow is documented separately in PLAN-004 and ADR 0008.

## Status labels

- **NORMATIVE** — current intended product behavior, based on an explicit owner decision.
- **WORKING** — a proposed design or plan that still needs validation or owner decisions.
- **EVIDENCE** — observed implementation, source material, or validation results.
- **REFERENCE** — external context that informs decisions but does not set requirements.
- **HISTORICAL** — superseded decision or plan retained for its history.

Use `PASS`, `PARTIAL`, `FAIL`, `UNKNOWN`, or `NOT_APPLICABLE` in the definition gate. A decision record keeps prior choices and reasons; update it by superseding the old decision rather than erasing history.
