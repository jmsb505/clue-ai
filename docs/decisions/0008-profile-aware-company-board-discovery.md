# ADR 0008 — Profile-aware company board discovery

**Status:** Accepted  
**Date:** 2026-10-01

## Context

The app's primary sourcing path must move beyond five general remote feeds. The user's target includes AI/ML engineering, applied AI/LLM systems, data analysis/engineering, ML platforms, and technical product implementation, with a current work-from-Milan/Italy constraint. Existing Scrapling support starts at one manually registered URL, stays on one host, and follows at most 25 matching job links. It cannot discover an employer or its external ATS board. This fails the user's core expectation of broad company-specific search after CV upload.

Public company directories and ecosystem research can discover employers, but they are not vacancy feeds. The employer's official career page or hosted ATS board is the vacancy authority. Current discovery candidates include Sifted's Europe-wide AI 100, AIxIA's Italian AI map, and the Italian AI market research from Politecnico di Milano. Official ATS interfaces include public Greenhouse GET endpoints, Lever's public postings API, Ashby's lightweight public job board API, SmartRecruiters public posting endpoints, and Personio's XML company career feed. The exact supported fields and authentication path vary by provider.

## Decision

Build a local, profile-aware company-board directory and make multi-company official-board collection a primary source route:

1. Seed the directory from broad European AI and Italian AI/data company lists, then add global AI/data/platform employers where a role can fit.
2. Discover the employer's official career URL and resolve its linked ATS board automatically. Do not make the owner look up company-specific slugs.
3. Prefer documented public, no-auth ATS endpoints and job feeds. Use Scrapling's async Spider, sitemap and scoped link traversal, structured JobPosting parsing, and adaptive selectors for repeated templates when needed. Use normal dynamic rendering only for a public page that cannot be collected from static or structured routes.
4. Batch independent companies in a bounded asynchronous crawl and stream normalized results into the local index. Show source progress and per-domain outcomes.
5. Keep the existing broad remote-job feeds as supplemental coverage. Run the Italy work-location filter on each listing using country/region evidence before JEV scoring.
6. Public official pages are the normal search path. The app performs automated source qualification and only tracks public routes it can fetch within their published behavior; an explicit denial, challenge, or rate limit pauses that connector and does not block the rest of the search. Do not require the user to certify each board through a repeated per-source checklist.
7. Never use login-only content, guessed ATS identifiers, unrelated page crawling, search-result scraping, stealth, proxy rotation, browser impersonation, CAPTCHA solving, or retrying around an explicit block.

## Consequences

- Company-level recall and current listing coverage improve beyond aggregator feeds, while the app remains honest that no catalog covers every employer.
- The app needs a maintainable company catalog, board-resolution data, source metrics, and support for several public ATS formats.
- Search may take longer on its first full catalog run; async batching, incremental refresh, progress, and cached checks must keep later searches practical.
- A catalog company is only a candidate seed, not a live vacancy or a promise of Italy eligibility.
- Each vacancy keeps original source, date, and country evidence; the user follows the original employer link and decides whether to apply.
- This adds no paid source or infrastructure cost. Jev remains the only recurring cost.

## Evidence

- [Profile-aware company-board discovery research](../research/profile-aware-company-board-discovery.md)
- [Current Scrapling crawl implementation](../../clue_ai/sources.py)
- [Current search orchestration](../../clue_ai/services.py)
- [Scrapling documentation](https://github.com/D4Vinci/Scrapling)
- [Greenhouse Job Board API](https://docs.greenhouse.io/job-board.html)
- [Lever Postings API](https://github.com/lever/postings-api)
- [Ashby public Job Postings API](https://developers.ashbyhq.com/docs/public-job-posting-api)
- [SmartRecruiters API authentication](https://developers.smartrecruiters.com/docs/authentication)
- [Personio job XML feed](https://developer.personio.de/v1.0/reference/get_xml)
- [Google JobPosting structured data](https://developers.google.com/search/docs/appearance/structured-data/job-posting)
