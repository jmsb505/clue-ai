# PLAN-008 — Broader public job-page crawling

**Status:** M1 implementation complete; live coverage evaluation pending
**Created:** 2026-10-02
**Last updated:** 2026-10-02

## Objective

Increase Clue's job discovery coverage by crawling more pages on public employer and ATS career sites, including pages their `robots.txt` file excludes, and stop failed attempts from suppressing later searches.

## Motivation

The owner is using Clue for a personal job search and wants broader source coverage. The current crawler obeys `robots.txt`, inspects only a small number of career pages, limits sitemap traversal, and renders only three JavaScript career shells per run. These are Clue-imposed limits that suppress otherwise public job listings.

## Baseline at plan start

- Three Scrapling spiders set `robots_txt_obey = True`.
- Company crawl inspects at most five HTML pages, three child sitemaps, and six sitemap-discovered job pages per company per run.
- The dynamic-render fallback handles at most three career pages per run.
- A separately registered public-career source follows up to 25 same-host job links.
- JustRemote is capped at 60 total pages, 24 listing pages, 45 job-detail pages, and result page 5.
- Owner-added supported public sources start disabled in `Review` and require five explicit confirmations before Clue fetches them.
- Crawl code stops a host after HTTP 401, 403, 429, or an explicit anti-bot challenge and does not retry blocked requests.
- The source review already documents `robots_txt_obey = False`, but product, architecture, and ADR documentation disagree with it.

## Desired state

- Treat `robots.txt` as discovery metadata, not a hard crawl exclusion, for this single-user local job-search tool.
- Search substantially more of each public career site and its public sitemap, and render more JavaScript-based job pages.
- Let the owner add a supported public company or ATS source and have it searched on the next run without a multi-checkbox approval gate.
- Refresh frequently updated public feeds hourly, daily-updated feeds daily, and public company/JustRemote crawls every six hours.
- Record query-fetch failures separately from successful checks and make failed sources eligible again after a five-minute retry interval.
- Keep explicit page and response-size ceilings, low per-domain concurrency, an identifying User-Agent, no blocked retries, and the existing stop-on-denial/challenge behavior.
- Preserve publisher-specific API/feed terms, request quotas, attribution, and canonical listing links.

## Scope

- Add a superseding source-policy decision and update product, architecture, source-review, and roadmap records.
- Set all Scrapling spiders used for public company/career crawling to `robots_txt_obey = False`.
- Raise the local company, sitemap, job-detail, JavaScript-render, and standalone career-page limits.
- Raise the JustRemote local budget to 200 pages (80 listing pages and 120 details), including result pages through page 20.
- Reduce app-imposed refresh waits for rapidly updated feeds to one hour and company/JustRemote crawls to six hours; preserve documented daily API/feed cadence.
- Add failure-aware source/query refresh accounting: failed retrievals receive a five-minute retry window rather than the normal success interval.
- Auto-enable owner-added supported sources after public HTTPS/host validation; retain simple pause/remove controls.
- Keep the enabled-source registry, host confinement, HTTPS validation, response size limits, and publisher-specific API/feed limits.

## Out of scope

- Stealth fetchers, CAPTCHA/Turnstile solving, proxy rotation, browser impersonation, or automated retries after HTTP 401/403/429 or an explicit challenge.
- Login-only, paywalled, or private content; X scraping; undocumented API reverse engineering; paid feeds or infrastructure.
- Changing publisher-specific request limits or attribution requirements.

## Source-of-truth impact

- Add ADR 0009 to supersede the robots and page-budget portions of ADR 0003.
- Update `docs/product-definition.md`, `docs/architecture/overview.md`, `docs/research/source-discovery-and-crawl-review.md`, and `docs/roadmap.md`.
- Record limits and validation evidence here.

## Constraints and decisions

- The app remains local, single-user, and free except for the existing Jev budget.
- The owner wants milestone checkpoints on `main`; do not create a branch.
- Explicit access denials, rate limits, and anti-bot challenges remain stop signals. This milestone broadens discovery and page coverage; it does not defeat those responses.
- Keep at most two concurrent requests per domain and a one-second base delay; stronger publisher-specific limits remain in force.

## Milestone M1 — Expand public crawl coverage

**Goal:** Remove Clue-imposed crawl-depth and robots exclusions that suppress public job listings while keeping explicit block handling.

### Subtasks

- [x] Add ADR 0009 and reconcile the conflicting crawl-policy documents.
- [x] Disable Scrapling's automatic `robots.txt` request filtering on the three public-page spiders.
- [x] Raise company HTML page cap from 5 to 25; child sitemaps from 3 to 10; sitemap job pages from 6 to 50.
- [x] Raise the JavaScript-rendering cap from 3 to 20 pages per company batch.
- [x] Raise standalone registered-career traversal from 25 to 100 same-host pages.
- [x] Raise JustRemote's page budget to 200 while keeping its approved host and page-path scope.
- [x] Follow more linked ATS boards, internal career sections, and job details from each employer page.
- [x] Auto-enable owner-added supported public sources after URL/identifier validation; replace the five-checkbox source review with a clear enable/pause control.
- [x] Use 8 global requests, 2 per domain, and a one-second base delay for Scrapling spiders.
- [x] Preserve blocked-request detection, zero retries, host boundaries, response-size caps, and source-specific publisher limits.
- [x] Make frequent-feed refresh windows one hour, company/JustRemote crawl windows six hours, and preserve daily publisher-updated API cadences.
- [x] Ensure failed requests do not consume a full refresh period; failed feed queries retry after five minutes.
- [x] Update canonical product/architecture/source documentation and record validation.

### Acceptance criteria

- [x] Each public-page Spider has the intended `robots_txt_obey = False`, 8/2 concurrency, one-second delay, and zero blocked retries.
- [x] Crawl budgets match the plan and remain bounded per company/run.
- [x] An explicit 401/403/429/challenge pauses that host without a bypass or retry; other source hosts continue (source-code inspection; no live block simulation).
- [x] Published source API/feed limits and attribution remain unchanged.
- [x] Owner-added URLs remain HTTPS-only, public-IP-only, same-host/known-ATS confined, and bounded; owners can pause or remove them.
- [x] Product, architecture, decision, and source-review docs agree on the new policy.
- [x] Conda `gen` Ruff, byte-compilation, and `git diff --check` pass; app server is stopped.
- [x] Applied the one-time local cache recovery: cleared two failed Remote First Jobs query stamps and scheduled JustRemote plus 80 tracked company boards for the expanded crawl.

### Affected areas

`clue_ai/crawl_policy.py`, `clue_ai/database.py`, `clue_ai/company_sources.py`, `clue_ai/sources.py`, `clue_ai/scrapling_boards.py`, `clue_ai/repository.py`, `clue_ai/web.py`, `clue_ai/templates/sources.html`, `docs/decisions/`, `docs/research/source-discovery-and-crawl-review.md`, `docs/research/profile-aware-company-board-discovery.md`, `docs/product-definition.md`, `docs/architecture/overview.md`, `docs/readiness/definition-gate.md`, `docs/roadmap.md`, `README.md`, and `docs/README.md`.

### Expected Git checkpoint

One coherent M1 checkpoint on `main` after static validation. Existing unvalidated PLAN-007 work remains separate until its UI acceptance is complete.

## Risks and limitations

- Ignoring robots exclusions may increase requests to sites that prefer not to be crawled; low per-domain concurrency, a one-second delay, bounded pages, and immediate stop on explicit denial/challenge limit impact.
- Deeper company batches can make a search take longer. Coverage counts, progress reporting, and source-specific refresh intervals remain visible.
- A failed or blocked source still requires another public source or manual visit; this plan does not promise universal coverage.

## Validation and completion record

- Static validation and source-policy review are required; no test suite or live third-party crawl will be run without the owner's request.
- 2026-10-02: Conda `gen` Ruff and byte-compilation passed. `git diff --check` passed after removing trailing whitespace. No unit suite or live third-party crawl was run; broad crawl recall, parse yield, and runtime remain unmeasured.
- 2026-10-02: Applied the source schedule and query-ledger schema migration to the owner's local `.data/clue.sqlite3`. Removed the two Remote First Jobs query stamps corresponding to HTTP 404 failures, retained its prior successful query stamp and local listings, scheduled the expanded JustRemote crawl, and made 80 tracked company boards due under the expanded profile. Daily publisher sources were left on their daily schedule.
- 2026-10-02: Stopped the existing Clue server through `scripts/clue.ps1`; port 8000 is free. Start the app again to load the new crawler code.
