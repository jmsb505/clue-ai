# ADR 0009 — Broader local public crawling and retry policy

**Status:** Accepted by the owner
**Date:** 2026-10-02
**Supersedes:** The robots, per-source review, refresh, and page-budget parts of [ADR 0003](0003-bounded-public-company-crawling.md)

## Context

Clue is a personal local job-search tool. The owner wants broad discovery from public job feeds, employer career sites, and public ATS boards, with Jev as the only paid service. The prior profile enforced `robots.txt` exclusions, crawled shallowly, refreshed public company pages daily, and cached some failures for the full success interval. In the current local database, a Remote First Jobs 404 was recorded as a successful query check; later runs skipped it and showed only two previously indexed matches. Those app-imposed limits reduce the usefulness of the search.

## Decision

- Search public career pages even when their `robots.txt` contains `Disallow`. Scrapling may read `robots.txt` for sitemap discovery; it does not use `Disallow` to filter page requests.
- Use Scrapling with eight global concurrent requests, at most two per domain, a one-second base delay, an identifying User-Agent, and zero retries after blocked responses.
- Raise public career-page limits to 25 HTML pages per employer, 10 child sitemaps, 50 sitemap job pages, 20 dynamic pages per company batch, 100 same-host pages for an owner-added career URL, and 200 JustRemote pages (80 listing pages and 120 job details).
- Refresh frequently updated feeds hourly. Keep RemoteJobs.org, Himalayas, Remotive, and Working Nomads on their documented daily cadence. Refresh company career pages and JustRemote every six hours.
- Distinguish query success from query failure. A failed request does not consume the ordinary success interval; failed feeds and public crawls may retry after five minutes. Explicit 401/403/429 responses, anti-bot challenges, and access denials pause the affected host and are not retried.
- Automatically enable owner-added supported public HTTPS sources after host/identifier validation. Keep pause and remove controls available.
- Preserve publisher-specific request limits and attribution, source URLs, response-size limits, public-host validation, and source page budgets.
- Keep login-only and paywalled content, X scraping, undocumented API reverse engineering, proxy rotation, stealth fetchers, browser impersonation, and CAPTCHA solving out of scope.

## Alternatives considered

- **Keep the daily/robots-respecting profile:** Rejected because public job pages that were otherwise reachable were excluded and repeated searches often reused old results.
- **Remove all crawl bounds or ignore explicit blocks:** Rejected because it can create unnecessary load and repeated denied requests. Wider page budgets, two-per-host concurrency, one-second pacing, and short failure backoff provide broader discovery with a controlled request profile.
- **Require a checklist for every owner-added public board:** Rejected for this single-user app. The supported URL/host validation, visible source status, pause/remove controls, and stop-on-denial behavior are sufficient for the owner's workflow.

## Consequences

- Searches can find more listings and start a retry sooner after a transient error.
- A first or due crawl can take longer and make more requests. Coverage and per-source outcomes remain visible; the app does not promise internet-wide results.
- Daily-updated sources remain daily even when the owner starts another search; their publisher cadence is not an app-imposed cooldown.
- Cached listings remain available when a source fails, but the failed source no longer appears refreshed for its normal interval.
- Owner-added supported sources start automatically after validation; the owner can pause or remove them at any time.
- The change adds no paid feed or hosted infrastructure.

## Validation

The source profile is implemented in `clue_ai/crawl_policy.py`, applied to source initialization and crawler budgets, and recorded in [PLAN-008](../plans/PLAN-008-broader-public-crawling.md). Static checks are recorded in that plan. No live third-party crawl is implied by this decision; wider source recall and latency remain unmeasured until the owner runs the local workflow.

## Evidence

- Owner direction in the project conversation, 2026-10-02: make the public crawling policy substantially less restrictive.
- Local search history on 2026-10-02: Remote First Jobs returned HTTP 404; its query ledger recorded the failed attempt and subsequent runs showed only cached results.
- [Scrapling Spider advanced settings](https://scrapling.readthedocs.io/en/latest/spiders/advanced.html)
- [Scrapling Spider API reference](https://scrapling.readthedocs.io/en/latest/api-reference/spiders.html)
- [Source discovery and crawl review](../research/source-discovery-and-crawl-review.md)
- [Product definition](../product-definition.md)
