# PLAN-013 — Tech Europe Jobs and comparable European sources

**Status:** M1 implemented and statically validated; M2 planned
**Created:** 2026-10-02
**Last updated:** 2026-10-02

## Objective

Add Tech Europe Jobs as a zero-cost, private local source using Scrapling, then document comparable European early-career and AI/startup job sources with a clear decision about which ones are ready to integrate.

## Motivation

The owner selected [Tech Europe Jobs](https://jobs.techeurope.io/) because it curates European technology companies and exposes AI-related roles. The owner wants wider source coverage while retaining Jev's junior/intern, paid-role, location, profile-fit, and AI-priority assessment. The board's directory visibly gates additional roles and filters behind newsletter signup, so Clue must work only from public links available without that signup.

## Desired state

- Tech Europe Jobs is a built-in, enabled source refreshed every six hours.
- Scrapling visits the public technical home view, the public `/ops` view, and job-detail links directly visible on those views, within a 60-page total budget.
- Job details use `JobPosting` JSON-LD when available, with a bounded HTML fallback; results retain the Tech Europe job-detail URL and source credit.
- The connector never follows off-site Apply links, newsletter/signup routes, or job-detail links discovered from other job-detail pages; a block stops the source without retry.
- Search coverage reports the source and its fetch/parse/block metrics through the existing connector flow.
- Comparable source research distinguishes automatic integration, manual link-out, and sources needing further terms/access review.
- No other non-TypeSafe recurring service, key, subscription, or infrastructure is introduced.

## Out of scope

- Using a newsletter address, account, API, private endpoint, or application form.
- Crawling roles hidden behind Tech Europe's newsletter gate or following external ATS Apply links as a second source.
- Automatically integrating every candidate site found during market research.
- A real CV search, Jev call, browser verification, live Tech Europe crawl, or application action.
- Any change to the unfinished PLAN-007 search-history work.

## Milestone M1 — Tech Europe public-page source

### Implementation

- [x] Register Tech Europe Jobs as a built-in source and make it part of migration seeding for existing local databases.
- [x] Add a Scrapling connector for the two public directory views and their visible same-host job-detail links.
- [x] Enforce the six-hour interval, 60-page cap, ordinary identified requests, host confinement, response-size bound, zero block retries, and direct Tech Europe listing URLs.
- [x] Reuse the current Jev assessment path so every retained listing is evaluated with the user's entry-level, paid, geography, fit, and AI ranking guidance.
- [x] Update source research and decision records to state public coverage and the newsletter-gate limit.
- [x] Update the existing source-registry expectations and user-facing source inventory.

### Acceptance criteria

- [x] A newly initialized database includes the enabled built-in Tech Europe source; an existing database receives it through normal `INSERT OR IGNORE` seeding.
- [x] Only HTTPS pages on `jobs.techeurope.io` are fetched; crawlable routes are `/`, `/ops`, and `/jobs/<slug>` reached directly from a directory view.
- [x] No more than 60 total URLs are scheduled in one search; related jobs discovered from detail pages are not followed.
- [x] A role with JSON-LD or supported visible HTML is normalized with the Tech Europe listing URL, attribution, title, company, description, available location, employment type, and date.
- [x] HTTP 401/403/429, a recognized challenge, or an explicit block pauses the source without retry; other source connectors can continue.
- [x] The source appears in existing source and coverage views without a schema change or a new paid dependency.
- [x] Conda `gen` Ruff, Python syntax compilation, and `git diff --check` pass. No test suite or live crawl is run for this milestone.
- [x] Existing unstaged PLAN-007 work is unchanged and not included in the commit.

### Source-of-truth updates

- [Source discovery review](../research/source-discovery-and-crawl-review.md)
- [ADR 0014](../decisions/0014-techeurope-public-job-source.md)
- [README](../../README.md) and [documentation index](../README.md)
- Existing source-registry assertions in `tests/test_storage.py`

## Milestone M2 — comparable-source research

### Implementation

- [ ] Review official/public source pages for European startup, AI, Italy, and early-career relevance.
- [ ] Record evidence, likely incremental value, access/terms status when found, and whether each candidate is an enabled source, manual link-out, or held for review.
- [ ] Prioritize sources that add junior/intern, paid, AI, and Italy/Europe coverage not already present in Clue's feeds and company crawl.
- [ ] Update this plan with findings, then commit and push this research checkpoint separately from M1.

### Acceptance criteria

- [ ] The review covers at least EuropeStartupJobs, EU-Startups Jobs, StartupJobs.it, Y Combinator Europe, and European Tech Opportunities 2027.
- [ ] It distinguishes observed site features from assumptions about access, reuse, pay, current-open status, and location eligibility.
- [ ] Sources with no evidenced API/feed or unclear access terms are not silently switched on; sources that prohibit automated collection remain manual-only.
- [ ] Findings are connected to Clue's existing zero-cost, one-user, Jev-ranked search workflow.

## Delivery

The owner has explicitly directed validated progress to be committed and pushed directly to `main`; do not create a branch. Keep PLAN-007's working-tree changes untouched and unstaged. Deliver M1 and M2 as separate checkpoints.

## Validation record

Conda `gen` Ruff passed for the changed Python files and source-registry contract; Python syntax compilation passed for the changed Python modules; and `git diff --check` passed. A code-path review confirmed that the new built-in entry reaches the existing search/source coverage flow and that Jev sees normalized retained jobs through the common assessment pipeline. The existing source-registry expectations were updated but not executed. No source request, live crawl, Jev request, test suite, or local server start was performed. The Tech Europe terms page linked from the site was not retrievable through the review browser; this owner-selected connector is restricted to the public pages described in ADR 0014.
