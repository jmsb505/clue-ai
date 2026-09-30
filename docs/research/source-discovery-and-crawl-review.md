# Source discovery and crawl review

**Status:** RESEARCH / proposed source policy  
**Reviewed:** 2026-09-30  
**Scope:** A single-user local job-search tool using $0 data sources and company career pages. The first search focus is fully remote work from Milan/Italy, including listings explicitly open to Europe or worldwide; no automated applying or public redistribution.

## Executive decision

Use a source registry and a **source-diverse discovery pipeline**. For the first validation search, target fully remote work from Milan/Italy; include EU/EEA, Europe, or worldwide roles only when the listing says that geography is eligible. Query a documented public feed or ATS endpoint first. Where no usable feed exists, consider ordinary, low-rate crawling of the employer's public career page and job-posting paths. This is a local personal-use tool, so do not design around commercial redistribution or public rehosting. Check each source's use terms, robots rules, and access behavior; prefer a clear alternative when published rules conflict with the planned local use. Parse job sitemaps, RSS/Atom, `JobPosting` JSON-LD, and ordinary HTML. Preserve the source URL, posted date, last-check time, and exact location-eligibility evidence.

The local app must not crawl the whole web on each search. It should ingest registered sources on a controlled schedule, then filter its local listing index for the owner's location, role, and preferences. The source list will be broad but incomplete and will vary by geography.

Scrapling is the **selected local crawler** for registered public HTML job and career pages, including employer and ATS pages. Direct APIs and feeds remain separate connectors. Scrapling is licensed under BSD 3-Clause; that covers the library itself, not job-source content or access rules. Use its ordinary `Spider` and static-fetching paths; do not use its advertised stealth, proxy-rotation, fingerprint-impersonation, CAPTCHA, or anti-bot bypass features.

## Source catalog candidates

Eligibility requires both a $0 price at expected volume and terms that allow the product's access, display, attribution, caching, and retention. Public availability or a working endpoint alone is not approval.

| Source | What the reviewed source establishes | Initial status |
|---|---|---|
| Employer-owned careers pages | The canonical job source. A registered connector can follow an official careers link, sitemap, RSS/Atom feed, or public job page. `JobPosting` JSON-LD can provide structured fields. Each employer's terms, robots policy, and page behavior are distinct. | **Crawl candidate per domain.** Use ordinary, low-rate requests and apply the source-specific rules. |
| Greenhouse boards | The [Job Board API](https://docs.greenhouse.io/job-board.html) returns published jobs without authentication for a specific employer board token. It is not a cross-company search index, and discovering board tokens is separate work. | **Candidate.** Check intended-use/display/caching terms and keep the employer's posting link. |
| Lever boards | The [Postings API](https://github.com/lever/postings-api) exposes postings for a particular company site and does not provide full-text search across all open jobs. | **Candidate.** Company-site identifier and source-use review required. |
| SmartRecruiters boards | Its [public Posting API](https://developers.smartrecruiters.com/docs/endpoints) documents unauthenticated endpoints for public data, including active postings for a given company identifier. It describes rate limits and company-specific pagination. | **Candidate.** Verify product display/caching rights and zero-cost limits before enabling. |
| Ashby boards | The documented `jobPosting.list` [API](https://developers.ashbyhq.com/reference/jobpostinglist) requires `jobsRead` access and returns listed and unlisted posts by default; Ashby says public job-board exposure must filter with `listedOnly=true`. | **No third-party admin API use without authorization.** A public employer board may be evaluated as a page source after a separate terms/robots review. |
| Remote OK | Its [FAQ](https://remoteok.com/faq) says its JSON and RSS feeds are free, need no authentication, and may be used by aggregators if Remote OK is credited and each original job URL is linked. | **Approved for the private local app** with visible credit and canonical listing links; poll conservatively, keep the data private, and recheck the terms before public distribution. |
| Jobicy | Its [public API](https://jobicy.com/jobs-rss-feed) is intended for job-discovery products, requires no key, supports `geo` filters and returns `jobGeo`; current docs describe up to 200 listings and ask apps to credit Jobicy and preserve its listing URL. Its optional direct ATS URL API costs $0.01 per job. | **Approved for the private local app** using only `GET /api/v2/remote-jobs`; poll no more than once per hour, credit Jobicy, and keep its canonical listing URL. Exclude the paid direct-ATS URL path. |
| We Work Remotely | Its [public RSS page](https://weworkremotely.com/remote-job-rss-feed) says anyone may use the feed with attribution. Its separate [API terms](https://weworkremotely.com/api-terms-and-guidelines) prohibit using WWR data to build a job-search service and prohibit saving/storing API data. | **Review / omit for now.** The feed page and API terms conflict with persistent local scoring. Prefer a source with clear local-use and retention rules. |
| Remote First Jobs | Its [RSS guidance](https://remotefirstjobs.com/rss) says RSS is free/public, provides the latest 100 listings per feed, and asks for source credit; it says not to submit listings to large third-party job platforms. Feeds refresh every 10 minutes. | **Approved for the private local app** with visible credit, original Remote First Jobs links, and a few-times-daily local refresh; do not republish listings to other job platforms. |
| Startup Jobs | Its [API page](https://startup.jobs/api) offers a free key-based API and no-key RSS feeds. The RSS feed returns 50 jobs from the last 14 days. Its [terms](https://startup.jobs/terms) require a link on the page/app screen using the data and permit republishing only for non-commercial objectives. | **Approved for the private, non-commercial local app using RSS only** with Startup Jobs credit and direct/dofollow canonical links. Do not use the API key path in the first increment. |
| Himalayas | Its [API documentation](https://himalayas.app/api) offers a free, no-key API intended for job-search experiences, with country/worldwide filters and structured `locationRestrictions`; it requires attribution and links back. Its [general terms](https://himalayas.app/terms) prohibit copying/public display, redistribution, and use of service data without consent. | **Review / omit for now.** The API guidance and general terms conflict; prefer sources with clear local-use rules. |
| Arbeitnow | Its [API announcement](https://www.arbeitnow.com/blog/job-board-api) describes a free, no-key API covering mostly German ATS sources, with a `remote` field and Germany/UK variants. Its [terms](https://www.arbeitnow.com/terms) require a link back and reserve revocation, while the general site license restricts public display and use to personal, non-commercial viewing. | **Review / lower priority.** Mostly Germany-focused and not enough to establish remote-from-Italy rights; hold until terms clarify and include only explicitly Italy-eligible roles if approved. |
| Remotive | The [public RSS page](https://remotive.com/remote-jobs/rss-feed) invites aggregation with Remotive attribution and a link back, but the [Terms of Use](https://support.remotive.com/en/article/terms-of-service-u4kbkf/) also prohibit automated crawling and redistribution without written permission. | **Hold / omit for now.** Its feed guidance and general terms conflict; use an alternative unless the published terms clearly cover local personal use. |
| USAJOBS | Its [Search API](https://developer.usajobs.gov/api-reference/job-apis) covers U.S. federal announcements and requires an approved API key. Its [API terms](https://developer.usajobs.gov/apirequest/index) permit storing/reformatting in an application if displayed values stay unchanged, USAJOBS is credited, and users are sent there to view/apply. The terms also prohibit standalone redistribution and a competing job-data product. | **Out of initial scope.** It is U.S.-specific and does not help the Milan/Italy pilot. Revisit only if the user selects a relevant U.S. search. |
| Adzuna | Its [API terms](https://developer.adzuna.com/docs/terms_of_service) expressly permit personal research and set default limits of 25 requests/minute, 250/day, 1,000/week, and 2,500/month. Publishing listings requires “Jobs by Adzuna” attribution/branding and a link. API access requires an app ID/key. | **Good private-use trial candidate.** Register a personal key, confirm Italy-market support, include required credit if displaying results, and verify that caching/running Jev on the local UI fits the permitted personal-research use. No ongoing organization/commercial use is assumed. |
| Jooble | Its [REST API](https://help.jooble.org/en/support/solutions/articles/60001448238-rest-api-documentation) is intended to feed results into a website/search portal, requires a separate key for each country domain, returns Jooble links, and has a 500-lifetime-request quota per key. | **Bounded trial candidate.** Check availability of an Italian API key and current API terms; the lifetime quota may be enough for a focused personal search but not broad/high-frequency discovery. Keep Jooble links and do not treat results as employer-direct unless the URL proves that. |
| LinkedIn and other closed boards | LinkedIn's [User Agreement](https://www.linkedin.com/legal/user-agreement) prohibits scraping/copying and unauthorized automation. Terms differ by board. | **Exclude absent an official partner/feed agreement.** Never use logged-in browser automation, access-control workarounds, or scraped search-result pages. |

### Additional source families to inventory by user-selected geography

- National, regional, municipal, and civil-service employment portals in the selected geography.
- Public employment service APIs and feeds, where the relevant government explicitly offers one for third-party applications.
- Universities, hospitals, charities, trade associations, professional bodies, and local sector boards that publish a permitted feed or public vacancy pages.
- Employer career pages on ATS hosts such as Workday, iCIMS, Oracle Recruiting, Personio, BambooHR, Workable, and Ashby. Treat each hosted public board as a distinct employer source; ATS vendors' apply integrations are not evidence of job-discovery rights.
- Job-board RSS/JSON feeds that expressly allow aggregation, attribution, and direct links, such as the Remote OK feed candidate above.
- Employer-submitted career URLs and user-curated company watchlists, which provide a transparent source seed without brute-forcing board identifiers.

### Italy/Europe remote eligibility model

“Remote” describes workplace arrangement; it does not say where the employer can hire someone. Keep these fields separate in the local normalized listing: `workplace_type`, `eligible_countries` (ISO codes), `eligible_regions` (for example EU/EEA, Europe, EMEA, worldwide), `timezone_restriction`, `eligibility_evidence`, and `eligibility_status`.

- `Eligible here`: the posting explicitly names Italy, EU/EEA, Europe, or worldwide and has no contradictory restriction.
- `Needs verification`: it says only “remote,” names EMEA/time-zone overlap without country-level scope, has unclear or conflicting location rules, or may require confirmation of employer/payroll availability in Italy.
- `Not eligible`: it explicitly limits the role to a geography that excludes Italy, when Italy is a hard user constraint.
- `Unknown`: no reliable eligibility evidence is available.

Do not infer that an Italian resident may work for an employer from a remote label, EMEA, or a compatible time zone. Treat work authorization and visa sponsorship as separate user-provided filters. Show the exact evidence and let the owner open the original posting; never silently turn an unknown into a confirmed Italy match.

Google's [JobPosting documentation](https://developers.google.com/search/docs/appearance/structured-data/job-posting) is a useful parsing and freshness schema, not a general search API or permission to republish. Search-engine result pages are not a substitute for source feeds and must not be scraped.

## Company-site discovery and crawl flow

1. Maintain a source registry mapping employer name, canonical company domain, official careers URL, ATS host/board identifier, geography, source type, and use state.
2. Seed the registry from official company links, employer-submitted URLs, permitted directories, public ATS board metadata, and user-curated employers. Do not brute-force slugs or recursively crawl unrelated site sections.
3. Check the source's public API/feed instructions, terms, and `robots.txt` before enabling a connector. `robots.txt` is a crawler instruction protocol, **not access authorization**, as [RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html) expressly states. Public career pages can be considered for ordinary, low-rate personal retrieval without contacting every employer; skip sources when published terms conflict with the planned use.
4. Fetch an official structured endpoint/feed first. Otherwise begin at the careers page, follow only same-domain career/job links and the employer's explicit ATS link, and prefer a job sitemap or `JobPosting` JSON-LD. Use bounded selectors on linked job-detail pages when structured data is absent.
5. Crawl outside the user request path. Use incremental refresh, `ETag`/`Last-Modified` where available, a source-specific schedule, and source-specific deletion/expiry rules. Default to no more than one concurrent request per domain and at least a 2-second delay, then increase delays to honor `Crawl-delay`, `Request-rate`, `Retry-After`, or stricter terms. These are conservative pilot defaults, not a replacement for the site's stated policy.
6. On `401`, `403`, `429`, CAPTCHA, bot challenge, or explicit block, stop that connector and record the reason. Use another source; do not rotate proxies, imitate browsers, solve challenges, or retry around the block.
7. Store only fields needed for discovery and fit review. Preserve the original employer/board URL and source ID; do not rewrite or silently alter the job text. Remove delisted/expired posts on the source's requested schedule. Display source, employer-posted date when provided, last checked time, and an unknown/stale state when verification is old.

## Selected Scrapling crawler and operating profile

The [Scrapling repository](https://github.com/D4Vinci/Scrapling) describes a Python framework for static HTTP fetching, dynamic browser rendering, adaptive selectors, and concurrent crawling. Its [Spider documentation](https://github.com/D4Vinci/Scrapling/blob/main/docs/spiders/getting-started.md) says `robots_txt_obey` is off by default; when enabled, it checks `Disallow` and honors `Crawl-delay` and `Request-rate`. The [advanced Spider settings](https://github.com/D4Vinci/Scrapling/blob/main/docs/spiders/advanced.md) expose global and per-domain concurrency plus `download_delay`. The [static-fetch docs](https://github.com/D4Vinci/Scrapling/blob/main/docs/fetching/static.md) show custom request headers for an ordinary User-Agent. The [license](https://raw.githubusercontent.com/D4Vinci/Scrapling/main/LICENSE) is BSD 3-Clause.

Selected profile for local implementation:

- Use Scrapling Spider for registered crawl jobs. Set `robots_txt_obey = True`, `concurrent_requests = 4`, `concurrent_requests_per_domain = 1`, and a base `download_delay = 2.0` explicitly.
- Set `max_blocked_retries = 0`; Scrapling otherwise retries blocked responses by default. A 401/403/429, challenge, or explicit block pauses that connector without an automated retry.
- Set an identifying User-Agent through ordinary request headers. Scrapling raises its delay when `Crawl-delay` or `Request-rate` requires more time; robots compliance does not set concurrency.
- Use ordinary `Fetcher` for simple registered HTML fetches; direct APIs and feeds may use their own small HTTP connector. Use `DynamicFetcher` only when JavaScript is necessary and the domain's published rules allow it.
- Do not use `StealthyFetcher`, proxy rotation, stealth headers, browser impersonation, anti-bot bypass, or CAPTCHA/Turnstile automation. If a site rejects an ordinary identified crawler, disable that connector and use another source.
- Configure an honest crawler user-agent with a project identity/policy URL, bounded retries, `Retry-After` support, response-size limits, and per-domain crawl metrics.
- Keep the scraper as an ingestion adapter behind the source registry so it can be replaced without changing product-level job records.

The initial implementation reads `JobPosting` JSON-LD first and follows up to 25 same-host career/job links when the entry page has no structured postings. Linked detail pages may use a bounded `h1`, `article`/`main`, and common location/date selector fallback. Role-specific Remote First Jobs feed checks are keyed by a local hash of each requested role slug and observe the six-hour interval independently; deleting personal data clears that cache.

There is no library fee; crawl execution stays on the owner's machine. No paid proxy, hosted scraper, browser service, feed, or infrastructure may be introduced under the current budget. Keep ingestion narrow and incremental so it remains practical locally.

## Implementation-ready initial feed set (reviewed 2026-09-30)

The first app increment can enable four no-key feed paths for private, non-commercial local discovery. Each result must keep its source credit and original listing URL. The source set remains incomplete and location eligibility is classified from listing text, not inferred from the feed name.

| Source | Documented path | Local refresh/retention | Attribution and use conditions |
|---|---|---|---|
| Jobicy | `https://jobicy.com/api/v2/remote-jobs` | No more than once per hour; use a rolling local index and recheck listings before calling them current. | Credit Jobicy and preserve the Jobicy URL. Never request the optional paid direct-ATS URL. |
| Remote OK | `https://remoteok.com/api` or `https://remoteok.com/remote-jobs.rss` | Conservative six-hour refresh; keep results private to the owner's machine. | Credit Remote OK and link each original post. |
| Remote First Jobs | `https://remotefirstjobs.com/rss/jobs/<role-or-skill-slug>.rss` | Conservative six-hour refresh per requested role slug, despite the feed's more frequent publisher updates. | Credit Remote First Jobs and preserve the source link; do not submit its jobs to other platforms. |
| Startup Jobs | `https://startup.jobs/feeds/jobs?workplace=remote` with optional role filter | Conservative six-hour refresh; publisher feed covers the last 14 days. | Private/non-commercial personal use only; credit Startup Jobs and retain its direct/dofollow job link. Use RSS only in this increment. |

Greenhouse, Lever, and SmartRecruiters public board endpoints are useful employer-specific adapters, but their access paths do not alone settle third-party reuse, caching, or display rights. Keep those connectors `Review` and disabled until each company/source record captures a suitable use basis, zero cost, attribution, and refresh/retention rules. User-entered employer career URLs follow the same per-domain review and must be explicitly `Approved` before Scrapling fetches them.

## Source use states

- **Approved:** $0 at expected personal use; a source offers a public feed/API or ordinary public page usable for the app's personal workflow; no authentication or access-control bypass is needed; crawler instructions and rate limits are handled; attribution/direct-link, local retention, and refresh rules are recorded.
- **Review:** terms restrict automation or personal caching, conflict across source/API documents, or require an account/key whose free-use scope is unclear. Prefer another source while that question is open.
- **Blocked:** terms prohibit required automation/use, access requires evasion, or source owner has refused. Disable and do not retry around the rule.

## Feasibility conclusion

Company-site crawling materially expands source reach compared with a single job API, but coverage depends on discovering company career URLs, per-site terms, parser maintenance, language handling, and crawl capacity. The viable initial promise is **search across the registered sources checked by the local app**, with an on-screen coverage list. “Every job on the internet” is not a feasible or supportable claim under a $0 data budget.

For the Milan/Italy pilot, measure the share of listings with explicit Italy eligibility, EU/Europe-wide eligibility, misleading generic-remote labels, and unresolved country restrictions. Also measure freshness, duplicates, link validity, parser coverage, and local runtime by source family before expanding the crawl.
