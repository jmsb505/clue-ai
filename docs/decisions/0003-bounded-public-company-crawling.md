# ADR 0003: Personal-use crawling of public company job pages

**Status:** SUPERSEDED by [ADR 0009](0009-broader-local-public-crawling.md)
**Date:** 2026-09-30

## Context

The owner wants a local personal job search with no recurring spend other than a maximum of $5/month for TypeSafe Jev. There is no free universal job index. Public ATS endpoints and employer career pages can add direct-source coverage, but each has different identifiers, page structure, refresh behavior, and use/caching terms. The owner selected Scrapling for local crawling.

## Decision

Historical decision: use a local source registry with explicit `Approved`, `Review`, and `Blocked` states. This source qualification and the crawl profile below have been replaced by ADR 0009.

Use Scrapling Spider as the crawler for registered public HTML job and career pages, including employer and ATS pages. Keep it behind a connector boundary; documented APIs and feeds remain direct source connectors. Configure `robots_txt_obey = True`, `concurrent_requests = 4`, `concurrent_requests_per_domain = 1`, and `download_delay = 2.0` seconds as the base crawl profile. Set an identifying User-Agent through ordinary request headers. Scrapling honors stricter robots `Crawl-delay` and `Request-rate` values by raising the delay; keep the explicit concurrency limits because robots compliance does not limit concurrency. Stop on access denials, rate limits, bot challenges, or explicit blocks. Do not use anti-bot bypass, CAPTCHA automation, proxy rotation, TLS/browser impersonation, login automation, or search-engine result scraping.

Treat `robots.txt` as one crawler policy, not as a grant to use or republish data. For public company career pages, check published terms and access behavior. If a source explicitly restricts the planned personal use, or its feed/API terms conflict, use a clear alternative. Confirm $0 price, attribution, allowed local cache/retention, refresh limits, and the original link before adding a source.

## Alternatives considered

- **Rely on one job aggregator:** Rejected because no single reviewed source has complete coverage of remote jobs eligible from Italy. Combine free feeds, APIs, and public employer pages.
- **Crawl every board and company indiscriminately:** Rejected because it ignores source terms, creates unnecessary load, and is harder to maintain than a registered, rate-limited set of sources.
- **Use only manual employer pages:** Rejected as the only strategy because official APIs and feeds can offer more stable, structured access where permitted.
- **Use Scrapling's stealth and proxy features to continue after blocks:** Rejected. A block means the connector stops; circumvention is outside product policy.

## Consequences

- Coverage grows through verified source adapters and remains measurable by geography.
- Source discovery, per-domain policy review, parser maintenance, and stale/duplicate handling are ongoing work.
- Public availability and a robots allow rule do not override a source's stated restrictions or allow bypassing access controls.
- Local execution and storage avoid a hosted service; keep scheduled crawling bounded so it stays practical on the owner's machine.
- Scrapling is selected for the local crawler; keep the adapter replaceable if implementation evidence shows it cannot meet the source and cost requirements.

## Reconsideration

Reconsider the source set when terms, fees, use conditions, quality, quota, geography, or user demand changes. Reconsider Scrapling only if the local implementation cannot meet source controls, parser coverage, stability, or zero-cost operation.

## Evidence

- Owner direction in project conversation, 2026-09-30: Scrapling is the selected crawler for this local app.
- [Scrapling project and features](https://github.com/D4Vinci/Scrapling)
- [Scrapling spider controls](https://scrapling.readthedocs.io/en/latest/spiders/getting-started.html)
- [Scrapling advanced Spider settings](https://github.com/D4Vinci/Scrapling/blob/main/docs/spiders/advanced.md)
- [Scrapling static fetching and request headers](https://github.com/D4Vinci/Scrapling/blob/main/docs/fetching/static.md)
- [Scrapling BSD 3-Clause license](https://raw.githubusercontent.com/D4Vinci/Scrapling/main/LICENSE)
- [RFC 9309: Robots Exclusion Protocol](https://www.rfc-editor.org/rfc/rfc9309.html)
- [Source discovery and crawl review](../research/source-discovery-and-crawl-review.md)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Lever Postings API](https://github.com/lever/postings-api)
- [SmartRecruiters public Posting API](https://developers.smartrecruiters.com/docs/endpoints)
- [USAJOBS API terms](https://developer.usajobs.gov/apirequest/index)
- M2 2026-09-30 pilot: one Prima EU Lever API response and its public JSON-LD page matched on posting ID, canonical URL, title, and Milan location; a YLD Greenhouse page returned HTTP 200 but triggered an ambiguous block signal and was not retried. Detailed metrics and parser differences are in the [source review](../research/source-discovery-and-crawl-review.md).
- [Remote OK feed guidance](https://remoteok.com/faq)
- [Jobicy Remote Jobs API](https://jobicy.com/jobs-rss-feed)
- [RemoteJobs.org API](https://remotejobs.org/api-access)
- [Remote First Jobs RSS guidance](https://remotefirstjobs.com/rss)
- [Startup Jobs API](https://startup.jobs/api)
- [Adzuna API terms](https://developer.adzuna.com/docs/terms_of_service)
- [Jooble REST API documentation](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation)
- [Remotive public RSS terms](https://remotive.com/remote-jobs/rss-feed)

## Affected source-of-truth documents

- `docs/product-definition.md`
- `docs/research/source-discovery-and-crawl-review.md`
- `docs/architecture/overview.md`
- `docs/readiness/definition-gate.md`
- `docs/roadmap.md`
