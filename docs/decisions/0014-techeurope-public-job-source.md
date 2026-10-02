# ADR 0014: Add Tech Europe Jobs as a bounded public-page source

**Status:** Accepted for single-user local use
**Date:** 2026-10-02

## Context

The owner asked to add Tech Europe Jobs to Clue's sources. Its public directory presents curated European technology-company roles and AI facets, and links to individual Tech Europe job-detail pages. The public page also asks visitors to subscribe to reveal additional roles and filters. The site's linked terms page was not retrievable during review, so this decision records the owner's source selection without claiming those terms were reviewed or that all crawl use is generally permitted.

Clue is a local personal search tool. Listings go through the existing Jev fit and search-filter assessment; Clue does not apply for the owner. The wider company-board crawler already uses identified ordinary requests, bounded page budgets, a one-second base delay, host limits, response-size limits, and a stop-on-block policy.

## Decision

- Add Tech Europe Jobs as an enabled built-in connector, using Scrapling.
- Begin only at the public technical home page and public `/ops` page. Follow same-host `/jobs/<slug>` details linked directly from those directory views.
- Cap the entire source crawl at 60 pages per six-hour refresh.
- Do not follow related-role links found on a detail page, newsletter/signup links, external Apply links, or pages requiring an account.
- Normalize structured `JobPosting` data where present and use a site-specific public-HTML fallback otherwise. Keep the Tech Europe detail page as the source URL shown to the user and preserve Tech Europe attribution.
- Stop this connector on HTTP 401, 403, 429, a recognized challenge, or an explicit access block. Do not retry around a block or introduce stealth, proxy rotation, browser impersonation, CAPTCHA solving, or a paid fetch service.
- Revisit the source if its terms become available, the board's access behavior changes, or the owner wants a broader crawl or redistribution.

## Consequences

The source adds curated European startup listings and AI-company context without a recurring non-TypeSafe cost. It may add relevant opportunities, but the public directory is only a partial view; Clue will not retrieve listings hidden behind the newsletter gate. Some public roles may be senior, unpaid, stale, or geographically ineligible, so the existing Jev assessment and user filters remain authoritative. A successful source fetch is not proof that an employer is still accepting applications.

The board detail page is kept as the user-facing listing link, allowing the user to inspect the post and use its Apply link themselves. The automated crawler never visits that external link.

## Evidence and references

- [Tech Europe Jobs](https://jobs.techeurope.io/): on 2026-10-02 its page reported 601 roles at 99 companies and showed a newsletter gate for more roles and filters.
- [Public Tech Europe job detail example](https://jobs.techeurope.io/jobs/stilta-yc-w26-platform-engineer-stockholm-1inw1js): exposes a role detail, company, description, location/date, and an external Apply link.
- [PLAN-013](../plans/PLAN-013-techeurope-and-european-sources.md) records the implementation budget and source-research work.
