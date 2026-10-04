# ADR 0019 — Add documented free AI and global job feeds

- Status: Accepted
- Date: 2026-10-05
- Decision owners: Clue owner

## Context

Clue's local search should reach beyond its existing remote-work boards and employer career pages, with stronger coverage for AI engineering roles. All data sources must cost $0, keep their publisher links and attribution, and support the owner's private local use. Listings still pass through Clue's AI engineering relevance filter, saved search criteria, and Jev assessment. An upstream board's keyword score is not a candidate-fit decision.

## Decision

Add two independently maintained public API sources to the source registry:

- **AI Dev Jobs**: use its anonymous public `GET /api/v1/jobs` endpoint. Run at most five varied AI role-family searches once per daily source interval, one page of at most 50 records per query, with one-second spacing. Use `workplace=remote` only for a remote search. Do not filter by candidate country, `global_remote`, role level, or pay at source time; preserve geography and incomplete pay/level records for local eligibility and Jev review. The API's documented salary figures are USD per year. Link each result to the publisher's `/job/{slug-or-id}` page and show AI Dev Jobs credit. Do not call its candidate matching endpoint or send the candidate profile there.
- **Dev Global Jobs**: use its no-key `GET /api/v1/jobs` endpoint for the technology category. Run at most five varied AI/technology searches once per daily source interval, one page of at most 100 records per query, with one-second spacing. Use `remote=true` only for a remote search. Do not add a country constraint that could suppress roles whose Italy/Europe eligibility must be read from the listing. Preserve the publisher's detail-page URL and visible Dev Global Jobs attribution.

The existing exact listing-URL registry is the identity boundary. Keep distinct listing URLs distinct; do not fuzzy-merge different country variants or vacancies. Repeated query results are deduplicated through their exact canonical URL before they enter Jev's candidate batch. Both source records are included in the current search coverage details.

## Source use evidence

- [AI Dev Jobs API documentation](https://aidevboard.com/docs) documents anonymous public reads, a maximum page size of 50, hourly throttling with rate-limit headers, and no active monthly API paywall. Its [terms](https://aidevboard.com/terms) permit data to appear inside an app but prohibit resale as a standalone dataset.
- [Dev Global Jobs API documentation](https://devglobaljobs.com/developers) documents no-key GET access, a maximum of 100 jobs per request, and a 120-request-per-minute limit. It requires a link to the Dev Global job page and visible source credit. Free use is limited to internal, research, and non-commercial use; commercial redistribution requires written permission.

The configured daily request caps stay well below the publishers' published limits. The app does not fetch application URLs, perform account-based access, or run either provider's candidate matching feature. No new dependency or recurring service is introduced.

## Consequences

- AI-only source coverage and cross-board diversity increase without another paid service.
- Each source can return repeated results across its own query families or overlap other sources; exact URL deduplication prevents repeats from becoming separate Jev items.
- One page per role family favors low-cost breadth over exhaustive pagination. A listing beyond the first page may not be reached by these connectors.
- Keyword query results are discovery leads, not confirmed open jobs, Italy eligibility, paid status, seniority, or candidate fit. Clue and Jev retain those decisions, and the original publisher link remains the authority.
- Automated coverage is broader but remains finite; the app does not claim an internet-wide search.

## Validation limits

The endpoints were reviewed through their publishers' documentation. During implementation, no live feed request or Jev request was made and no captured-fixture test was run. Static compilation, Ruff, code review, and diff checks are the milestone evidence; live source response shapes and coverage remain to be confirmed in the owner's next search.
