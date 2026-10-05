# PLAN-018 — Wider discovery, no-repeat listings, and qualification evidence

Status: M1–M3 pushed; M4 implementation complete (static validation; live workflow unverified)
Created: 2026-10-04 · Updated: 2026-10-05

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

- Add AI Dev Jobs through its documented anonymous public read API, with varied AI role/workplace queries, a 50-record page cap, daily refresh, and its hourly throttle.
- Add Dev Global Jobs through its no-key API for internal non-commercial use, with conservative technology/AI role queries, a 100-record page cap, visible source attribution, and its Dev Global Jobs listing URL retained.
- Do not add a candidate-country query filter at source time; it can suppress roles whose remote geography remains to be evaluated from the listing. A remote-only preference may use each API's documented remote parameter.
- Do not add a crawler for AiRemotelyjobs yet: it is highly relevant and shows direct employer listings, but an API/feed and machine-use terms could not be verified. Keep it as a source candidate for later permission/documentation review.
- Do not add OpenJobsEU yet: its published README confirms a static `feed.json`, but this review did not establish the public feed URL or explicit job-data reuse terms. Discover the exact feed and permissions before wiring it in.

### Work and acceptance

- Add the two public API sources and robust normalizers; preserve attribution and original/source listing links.
- Integrate them with the M1 identity ledger so overlapping aggregators do not generate duplicate opportunities or repeated Jev spend.
- Extend role-family search where existing feed APIs support it, without exceeding publisher pagination/rate limits. Record distinct publisher family, fetched, parsed, filtered, duplicate, and new URL counts separately in coverage.
- Run static compilation, Ruff, and diff checks; manually inspect each accepted response envelope, host check, link normalizer, query cap, deduplication path, and coverage accounting. Do not add/run a formal test suite, live crawl, or Jev request during delivery.

Expected commit: `feat: add free AI and global job feeds`.

### M2 progress and evidence

Added daily enabled registry entries and host-restricted connectors for both public APIs. Each runs up to five varied AI role-family queries, one page per query, one second apart, with the provider page limits and a stop on HTTP 429. No candidate country filter is used. Listing links stay on the publisher's human-facing role detail pages; source attribution is retained. Exact URL identity feeds into M1 deduplication. Coverage reports the query request count, raw/parsed count, locally focused count, inserted identities, and reused identities. Source terms, ceilings, and selection rationale are recorded in [ADR 0019](../decisions/0019-free-ai-and-global-job-feeds.md) and the [source review](../research/source-discovery-and-crawl-review.md). Conda-gen compilation passed; Ruff's one new FURB167 warning was fixed and the rerun passed; `git diff --check` passed with only line-ending normalization warnings. A follow-up correction committed as `21e1014` ensures normalized jobs retain human-facing detail links rather than API endpoint URLs. No test suite, live source request, or Jev call was used. Live response-shape/coverage remains unmeasured until the owner's next search.

## M3 — Qualification and seniority assessment

### Work

- Parse at most four explicit employer qualifications from each full listing, distinguishing mandatory from preferred where the posting says so. Never invent requirements from generic role language; show when none were extracted.
- Ask Jev typed per-requirement fit questions with statuses `met`, `partly_met`, `not_met`, and `not_enough_evidence`; separately assess candidate experience/seniority against the role's explicit level and years. Keep employer seniority requirements distinct from Clue's entry-level job filter.
- Persist the requirement text and Jev status/confidence in the search-result snapshot. Render a readable qualification checklist and a seniority alignment signal in the result detail, alongside evidence gaps and the original job link.
- Mark unsupported or absent job criteria unknown/review, not as a candidate deficiency. Do not present any assessment as likelihood of getting hired.
- Keep Jev's $5/month application cap and bound requirement questions per listing and per batch.

### Acceptance

- For an eligible AI-engineering role, the result identifies explicit mandatory qualifications the CV supports, partly supports, does not document, or conflicts with; preferred items remain clearly marked.
- Seniority assessment reflects employer-stated level/years versus the candidate's documented experience and does not infer age from dates.
- Missing employer details remain unknown; there is no fabricated explanation, qualification, or hiring probability.
- Historical snapshots remain readable after later posting changes.
- Inspect the saved JSON shape, question-name map, old-result behavior, semantic result markup, keyboard-native `<details>` disclosure, status text, and responsive CSS. Use static Jinja compilation, Python compilation, Ruff, and diff checks; do not start the local app, call Jev, or run tests during milestone delivery.

Expected commit: `feat: show qualification and seniority fit evidence`.

### M3 progress and evidence

Implemented a bounded extraction of up to four explicit required/preferred qualifications per listing and separate typed Jev assessments for each item and for seniority. Results preserve each assessment in the per-run JSON snapshot and display qualification evidence separately from fit scores and hard filters. Missing or invalid Jev answers remain eligible for a later assessment; missing profile evidence is not labeled as a deficiency. Product behavior and limitations are recorded in [ADR 0020](../decisions/0020-qualification-and-seniority-evidence.md) and [discovery and qualification architecture](../architecture/discovery-and-qualification-assessment.md). Validation uses Conda-gen Python compilation, Ruff, Jinja template compilation, and `git diff --check`; no app, live Jev request, live crawl, or test suite is run. Results remain uncalibrated against the owner's judgments.

## Source-of-truth updates and risks

Update product/architecture/source review, this plan, and an ADR before closing relevant milestones. Record source terms, refresh/pagination ceilings, direct URL and attribution behavior. Risk: a permanent unchanged-URL policy can hide a valid repost that reused a URL; detect material content changes and offer a one-run include-reviewed override. Risk: no static parser can understand every CV/JD requirement format; label extraction coverage and leave unparsed requirements unknown. No real-world applicant outcome is inferred.

## M4 — Remote preference with Milan workplace and language scope

### Work

- Make remote a ranking preference rather than a hard exclusion. Keep remote work eligible only when the posting supports work from the selected country.
- Allow explicit hybrid/on-site roles in the selected local city (Milan by default). Exclude explicit in-person roles elsewhere; retain unclear city/workplace evidence for review when the user allows unknown locations.
- Exclude roles with an explicit Italian-language requirement. English requirements are acceptable; optional/preferred Italian is not a conflict. Keep ambiguous language evidence visible for Jev review.
- Carry workplace preference, local city, and language rule into Jev's typed filter assessment and the saved run criteria. Show local scope exclusions in coverage.
- Let new API queries omit remote-only parameters under this preference so locally relevant Milan office roles remain discoverable. Preserve strict remote-only mode as an explicit user option.

### Acceptance

- A confirmed remote role eligible from Italy remains in scope and receives a remote-preference signal.
- A confirmed Milan hybrid/on-site role remains in scope when it has no explicit Italian requirement.
- A confirmed in-person role outside Milan and a role explicitly requiring Italian do not enter Jev's batch; coverage reports each local exclusion reason.
- Missing city, workplace, or language evidence remains review when allowed. “Italian preferred” and “English required” are not conflicts.
- New searches default to remote preference plus Milan office eligibility; old search snapshots preserve their original criteria. Reassessment of unchanged old listing URLs requires the existing include-reviewed option.
- Static Python compilation, Ruff, Jinja compilation, and whitespace checks pass. Do not start the app, make live source/Jev calls, or run formal tests during delivery.

### M4 progress and evidence

Implemented `remote_preferred` as the new-search default, preserving strict remote-only as an option. Remote postings still need work-from-country evidence; confirmed hybrid/on-site roles in the configurable local city (Milan by default) can remain eligible, while known other-city physical roles are excluded. A conservative local detector excludes explicit Italian-language requirements before Jev; English requirements and clearly optional/preferred Italian remain allowed. Jev receives typed workplace and language criteria, and coverage records exclusions by reason. Product definition, architecture notes, and ADR 0021 record the behavior and its limitations.

Conda-gen `compileall`, Ruff, Jinja compilation for the changed search/results templates, and `git diff --check` passed. No app session, source crawl, Jev request, or formal test suite was run. Static validation does not establish live source reach, parser accuracy across all job-board wording, or fit calibration; ambiguous cases remain reviewable and the employer listing remains authoritative.

Expected commit: `feat: allow Milan roles with remote preference`.
