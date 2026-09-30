# ADR 0002: No-cost multi-source local job coverage

**Status:** ACCEPTED for product direction  
**Date:** 2026-09-30

## Context

The owner wants the broadest practical personal search across user-selected geographies, initially fully remote from Milan/Italy. The app runs locally for one person. TypeSafe Jev has a maximum budget of $5/month; every other component and source must cost $0. Free job feeds and aggregators can provide cross-company discovery, while public ATS APIs and employer career pages can fill gaps. Each source has its own geographic coverage, attribution, refresh, caching, and access rules.

## Proposed decision

Build a local connector-based catalog using the widest useful combination of free APIs, feeds, public ATS boards, and ordinary public employer career pages. Start with documented job-discovery sources, then add source families and employer watchlists to improve coverage. Track source provenance and show which sources were checked. Use each source's documented public path and allowed refresh and local retention; do not automate logged-in access or bypass a block. Hard-cap TypeSafe Jev at $5/month and stop scoring at the limit.

The first search profile targets fully remote work from Milan/Italy, including listings explicitly open to Europe or worldwide. Geography remains user-selectable. Initial candidates with useful free paths include Jobicy, Remote OK, Remote First Jobs, Startup Jobs, Adzuna, and a limited Jooble trial; actual connector approval depends on current Italy coverage, source rules, and zero-cost operation. Coverage must be disclosed and cannot be described as exhaustive.

## Alternatives considered

- **Crawl every job board indiscriminately:** Rejected because it ignores source-specific rules, creates unnecessary load, and is harder to maintain than broad but registered connectors.
- **Use paid aggregators for broader coverage:** Rejected under the owner's current $0 ceiling for every component other than Jev.
- **Use only direct ATS APIs:** Rejected as a complete strategy because employer ATS boards require company discovery and do not provide a cross-company index. They remain valuable additions for employers missing from free aggregators.

## Rationale

A local connector boundary supports geography-specific source selection and incremental coverage while keeping the CV and results on the owner's device. A source may offer a free personal-use path but limit refresh or caching; record those specifics and favor sources with clear $0 terms.

## Consequences and risks

- Coverage will be incomplete and must be described honestly.
- Provider terms, free-tier limits, geography, and data quality can change; connector-level controls and source-health visibility are necessary.
- Direct feeds require board discovery and per-employer maintenance.
- The $0 source constraint will limit coverage. The app must show which source families and employers it checked; use a user-curated company list or manual source links when a source gap remains.

## Reversibility and reconsideration

The connector architecture is reversible. Reconsider the source mix if a provider changes terms, free-tier limits, availability, geography, freshness, or duplicate rate, or if the owner changes the budget or first-search geography.

## Evidence

- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Lever Postings API](https://github.com/lever/postings-api)
- [Adzuna API terms](https://developer.adzuna.com/docs/terms_of_service)
- [Jooble REST API limits and regional keys](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)
- [LinkedIn User Agreement](https://www.linkedin.com/legal/user-agreement)
- [Jobicy Remote Jobs API](https://jobicy.com/jobs-rss-feed)
- [Remote First Jobs RSS guidance](https://remotefirstjobs.com/rss)
- [Startup Jobs API](https://startup.jobs/api)

## Affected source-of-truth documents

- `docs/product-definition.md`
- `docs/research/market-and-reference-review.md`
- `docs/architecture/overview.md`
- `docs/readiness/definition-gate.md`
- `docs/roadmap.md`
