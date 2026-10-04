# PLAN-018 — Wider discovery, no-repeat listings, and qualification evidence

Status: M1 complete (static validation); M2 and M3 planned
Created: 2026-10-04

## Objective

Expand the distinct job opportunities Clue can reach while avoiding repeat review of an unchanged job at the same posting URL. Improve Jev's evaluation so the results show how the candidate's documented experience lines up with employer-stated qualifications and seniority.

## Product constraints and decisions

- Clue remains a personal local app. Italy/Europe eligibility, paid employment, junior/intern roles, and AI engineering or closely related implementation work remain the candidate focus.
- Public job sources must be free for internal/private use and preserve publisher attribution plus its job link. Jev is the only paid service and its existing monthly cap remains unchanged.
- Refresh source indexes on their normal cadence. Suppress an unchanged researched listing URL from future results and Jev calls; a materially changed posting at that URL may be assessed again. Keep earlier run snapshots available in history.
- The URL registry survives ordinary search-history/cache reset so the same postings do not immediately return. Full personal-data deletion removes it. Provide a deliberate way to include reviewed listings again.
- Crawl public listings only through documented feeds/APIs and the existing bounded Scrapling paths. Preserve direct employer links and intermediary listing links. Do not use logged-in scraping, CAPTCHA bypass, stealth, or retry after an explicit block.
- Continue direct-to-`main` delivery, with a commit and push for each validated milestone. Do not disturb the user's in-progress PLAN-007 changes. No formal tests unless requested; validate with compilation, Ruff, whitespace checks and isolated local workflows without live Jev or publisher calls.

## M1 — Listing URL research ledger

### Work

- Add a local durable registry keyed by canonical listing URL, independent of cached job-row retention, with a signature over substantive posting fields.
- On upgrade, seed the registry from historical rows that have both a complete Jev fit score and completed filter decision.
- Resolve known aliases for one indexed job (publisher URL, board URL, employer URL) to avoid resurfacing the same vacancy through multiple sources.
- Filter unchanged, previously Jev-assessed listing URLs out of a new run before snapshotting and scoring. Keep active source refreshes enabled so new postings continue to be discovered.
- Record research only for listings with a complete Jev assessment; an interrupted or failed assessment must remain eligible for retry.
- Let the user intentionally include previously reviewed URLs when starting a search. Show counts in coverage: previously reviewed skipped, changed/reopened, and newly eligible identities.
- Retain prior search snapshots. Ordinary result/cache reset retains this minimal URL/fingerprint registry; full personal-data deletion clears it.

### Acceptance

- Same exact URL and unchanged posting content encountered from a fresh feed, a refreshed feed, a source alias, or another search run does not enter the new Jev batch or appear as a new opportunity.
- A newly discovered URL appears. A materially edited post or changed application/eligibility conditions at the same URL is reported as updated and can be re-evaluated.
- Failed/interrupted source or Jev work never marks unsaved/assessed listings as researched.
- A deliberate include-reviewed option restores old URLs for one run. Search-history snapshots stay intact.
- Reset output explains URL-ledger retention; full personal-data deletion removes it.

### Validation and expected checkpoint

Compile touched Python modules; run Ruff and whitespace checks. Review the local code paths for alias, unchanged, changed, failed-run, override, reset, and deletion behavior. No live source or Jev calls.

Expected commit: `feat: skip previously researched job listings`.

### M1 progress and evidence

Implemented a durable per-URL content-signature ledger, migration seeding from complete saved Jev decisions, alias-aware same-run filtering, search-history/reset retention, explicit include-reviewed input, and Scrapling detail-page skips for known reviewed URLs. Index/feed refresh schedules are unchanged. Only complete Jev fit plus filter decisions populate the registry; failed or incomplete records stay eligible for retry. Product behavior and reset/deletion semantics are documented in ADR 0018 and the product definition. Conda-gen `compileall` and Ruff passed; `git diff --check` passed with only the repository's existing CRLF normalization warnings. No live sources or Jev requests were used, and no formal test suite was run for this checkpoint.

## M2 — Additional distinct source families

### Research decisions

- Add AI Dev Jobs through its documented anonymous public read API, with AI role/level/workplace queries, pagination caps, and its stated hourly throttle.
- Add Dev Global Jobs through its no-key API for internal non-commercial use, with conservative request count, country/AI role filters, visible source attribution, and its Dev Global Jobs listing URL retained.
- Do not add a crawler for AiRemotelyjobs yet: it is highly relevant and shows direct employer listings, but an API/feed and machine-use terms could not be verified. Keep it as a source candidate for later permission/documentation review.
- Do not add OpenJobsEU yet: its published README confirms a static `feed.json`, but this review did not establish the public feed URL or explicit job-data reuse terms. Discover the exact feed and permissions before wiring it in.

### Work and acceptance

- Add the two public API sources and robust normalizers; preserve attribution and original/source listing links.
- Integrate them with the M1 identity ledger so overlapping aggregators do not generate duplicate opportunities or repeated Jev spend.
- Extend role-family search where existing feed APIs support it, without exceeding publisher pagination/rate limits. Record distinct publisher family, fetched, parsed, filtered, duplicate, and new URL counts separately in coverage.
- Verify connectors with captured fixtures/offline parsing and synthetic payloads. Do not start a live full crawl or use Jev during delivery.

Expected commit: `feat: add free AI and global job feeds`.

## M3 — Qualification and seniority assessment

### Work

- Parse a small capped set of explicit employer requirements from each full listing, distinguishing mandatory from preferred where the posting says so. Never invent requirements from generic role language.
- Ask Jev typed per-requirement fit questions with statuses `met`, `partly_met`, `not_met`, and `not_enough_evidence`; separately assess candidate experience/seniority against the role's explicit level and years. Keep employer seniority requirements distinct from Clue's entry-level job filter.
- Persist the requirement text and Jev status/confidence in the search-result snapshot. Render a readable qualification checklist and a seniority alignment signal in the result detail, alongside evidence gaps and the original job link.
- Mark unsupported or absent job criteria unknown/review, not as a candidate deficiency. Do not present any assessment as likelihood of getting hired.
- Keep Jev's $5/month application cap and bound requirement questions per listing and per batch.

### Acceptance

- For an eligible AI-engineering role, the result identifies explicit mandatory qualifications the CV supports, partly supports, does not document, or conflicts with; preferred items remain clearly marked.
- Seniority assessment reflects employer-stated level/years versus the candidate's documented experience and does not infer age from dates.
- Missing employer details remain unknown; there is no fabricated explanation, qualification, or hiring probability.
- Historical snapshots remain readable after later posting changes.
- Review the results presentation for clarity and accessibility; verify with synthetic captured Jev responses without any live Jev spend.

Expected commit: `feat: show qualification and seniority fit evidence`.

## Source-of-truth updates and risks

Update product/architecture/source review, this plan, and an ADR before closing relevant milestones. Record source terms, refresh/pagination ceilings, direct URL and attribution behavior. Risk: a permanent unchanged-URL policy can hide a valid repost that reused a URL; detect material content changes and offer a one-run include-reviewed override. Risk: no static parser can understand every CV/JD requirement format; label extraction coverage and leave unparsed requirements unknown. No real-world applicant outcome is inferred.
