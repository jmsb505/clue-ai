# PLAN-001 — Free source discovery and local crawl pilot

Status: ACTIVE — source evidence plan; app implementation tracked in PLAN-002
Created: 2026-09-30  
Last updated: 2026-09-30

## Objective

Determine which $0 sources can support the first personal search—fully remote jobs performable from Milan/Italy, including listings explicitly open to Europe or worldwide—and assess whether a controlled local crawler adds fresh, traceable postings without bypassing site controls or exceeding the Jev-only $5/month budget.

## Motivation

Paid job aggregators and paid infrastructure are outside the owner's budget. Free feeds, public ATS endpoints, and employer career pages offer complementary paths, but broad coverage is fragmented. The platform needs a source list, repeatable registration, truthful coverage reporting, and crawl-quality evidence before it makes coverage claims.

## Current state

- Product definition, reference/market research, source discovery policy, and architecture are documented.
- The public GitHub repository exists; `main` contains the planning/research baseline. PLAN-002 M1 is implemented and locally validated on `main`; its direct commit/push is the current delivery step.
- Scrapling remains the selected crawler; its bounded adapter, JSON-LD parser, and linked-page HTML fallback are wired in PLAN-002. Fixture validation is complete; live-source validation remains pending.
- No source registry has been runtime-validated; TypeSafe API terms and a safe local API-key arrangement remain open. No real candidate data is in use.

## Desired state

A single-user local build can retrieve postings only from source-registry entries approved for personal use, retain provenance and freshness on the owner's device, deduplicate safely, and use Jev within a hard $5/month cap. All other services and data sources cost $0. Results disclose source coverage and link to the provider or original posting. The owner still applies externally.

## Scope

- Create and maintain a local source registry for access/terms notes, allowed paths/endpoints, geography, costs, attribution, limits, refresh interval, local retention, and parser version.
- Verify a representative set of Italy/Europe-relevant job feeds, APIs, ATS boards, and employer career pages. A generic `remote` label is not proof that someone can work from Italy.
- Use Scrapling for registered public company-career pages, configured for ordinary, low-rate, robots-aware requests without stealth or bypass features.
- Measure coverage, freshness, parse success, duplicate/link quality, and incremental operating cost.

## Out of scope

- A public or multi-user service, claims of internet-wide completeness, paid job data, paid infrastructure, proxies, hosted scraping services, search-engine-result scraping, or closed-board scraping.
- Logged-in access, applying, submitting applications, scraping applicant portals, anti-bot/CAPTCHA bypass, or sending real CVs before privacy and TypeSafe gates pass.
- Final selection of all source providers before their terms and $0 cost are confirmed.

## Source-of-truth impact

- Product inputs and non-goals: `docs/product-definition.md`
- Source evidence and crawler rules: `docs/research/source-discovery-and-crawl-review.md`
- System boundaries: `docs/architecture/overview.md`
- Decision: `docs/decisions/0003-bounded-public-company-crawling.md`
- Gate and sequence: `docs/readiness/definition-gate.md`, `docs/roadmap.md`

## Existing decisions and constraints

- Geography remains a user input throughout the product. The first personal validation profile is fully remote from Milan/Italy, with explicitly eligible EU/EEA, Europe, and worldwide listings included.
- The app is candidate-side, single-user, and local; it does not apply for the user.
- TypeSafe Jev is the fit evaluator; maximum TypeSafe spend is $5 per rolling 30 days all-in.
- Every other recurring source or service cost is $0; run the app and store data locally.
- User-controlled deletion of the local CV, profile, preferences, job index, and results is required; no account service is planned.
- Source use terms, robots rules, and rate limits are connector-level requirements.

## Supporting skills / tools

- `implementation-plan` and `milestone-delivery` for milestone governance.
- `project-kickoff` for product definition and readiness.
- Context7 for current Scrapling documentation; official vendor/API pages for source terms.
- Scrapling is selected for the local crawling adapter; its dependency version will be pinned when that implementation milestone begins.

## Dependencies

- The first test location is Milan/Italy with fully remote work; role query comes from the user's CV or search input. Product geography remains selectable.
- Source/API terms and any free key registration required for a candidate connector.
- A secure local runtime, local database/file storage, and protected local Jev API-key configuration.
- TypeSafe's applicable Order, DPA, usage accounting, and a hard spend-stop design.
- Synthetic CV/listing pairs for fit evaluation.

## Risks and unknowns

- A source can expose public postings while restricting aggregation, display, or retention.
- A public-sector feed may prohibit competing search products even if it allows an internal app.
- `robots.txt` is not authorization, and the crawler's default robots setting is off.
- Free-tier providers may prohibit durable storage or scheduled jobs, or fail privacy/security needs.
- Global employer-site discovery and parser maintenance may exceed the local machine's practical capacity and the owner's maintenance time.
- CV work-history text can remain identifiable after direct identifiers are removed; use synthetic data until processor/privacy gates pass.

## Milestones

### M1 — Select a source set for remote-from-Italy searches

Goal: Produce a source registry slice that gives one person's local remote-from-Italy search broad coverage from free feeds, APIs, and public employer sources.

Subtasks:

- [ ] Use Milan/Italy with fully remote work as the first validation profile; take role families from the CV/user query. Do not hard-code this profile into the product.
- [ ] Inventory official employer URLs, documented ATS APIs, feeds with clear personal-use terms, and relevant public employment-service sources for that input.
- [ ] Mark every source `Approved`, `Review`, or `Blocked`; record the documented access path, cost, quota, attribution, cache window, refresh, and canonical links. Exclude sources whose published rules do not support the planned personal use.
- [ ] Confirm each approved source costs $0 at expected test volume.

Affected areas: source registry, ingestion connectors, product coverage disclosure.

Dependencies: documented source paths and any free key registration required by a connector.

Acceptance criteria:

- [ ] Every enabled source has a documented personal-use path, $0 cost, attribution, direct-link, local retention, and refresh rules.
- [ ] Every result preserves location-eligibility evidence and is labeled `Eligible here`, `Needs verification`, `Not eligible`, or `Unknown`; only explicit Italy/EU/EEA/Europe/worldwide eligibility counts as confirmed for the first profile.
- [ ] The coverage report names excluded/under-review sources and does not claim completeness.

Validation:

- [ ] Manual primary-source terms/API review for each enabled source.
- [ ] Manually inspect representative source listings, Italy/Europe eligibility language, and original URLs.
- [ ] No automated tests prescribed until a connector is implemented.

Documentation updates:

- [ ] Update the source registry, source review, ADR 0003, and gate with the actual geography-specific evidence.

Applicable specialized skills: `context7-mcp` for current library/API documentation; recheck the source and TypeSafe documentation before live use with the owner's CV.

Expected Git checkpoint: implement, validate, commit, and push each source milestone directly to `main`. Do not create milestone branches or bypass repository protections; stop and report if a required check or push is rejected.

### M2 — Implement and validate a controlled Scrapling crawler

Goal: Implement the selected Scrapling adapter and validate it on a small set of approved public job and career pages with ordinary, identifiable requests.

Subtasks:

- [ ] Compare a documented feed/API with static HTML/JSON-LD on approved public job and career pages.
- [ ] Use Scrapling Spider for registered public pages; set `robots_txt_obey = True`, `concurrent_requests = 4`, `concurrent_requests_per_domain = 1`, and a base `download_delay = 2.0`.
- [ ] Set an identifying User-Agent with ordinary request headers; honor stricter `Crawl-delay` and `Request-rate` values when robots rules provide them.
- [ ] Test dynamic rendering only for a permitted page that cannot be read from HTTP/feed/schema; no stealth, proxies, or bypass.
- [ ] Capture parse failures, 401/403/429/block signals, delisted jobs, duplicate cases, response size, and last-seen timestamps.

Affected areas: crawler adapter, source registry, normalized listing schema, source-health monitoring.

Dependencies: M1 source set and the owner's local computer; no paid compute or hosted crawl service.

Acceptance criteria:

- [ ] Every result retains a canonical source URL, source ID, observed time, posted date when supplied, and source state.
- [ ] A source block or rate limit stops the connector without an evasion attempt.
- [ ] Results marked “recently checked” meet the defined 24-hour freshness target; older results are labeled stale/unknown.
- [ ] No non-TypeSafe spend is incurred.

Validation:

- [ ] Manual source-by-source crawl audit and link verification.
- [ ] A documented stale/deleted/duplicate sample review; do not send live CVs.

Documentation updates:

- [ ] Record parser coverage, source limitations, data retention, and crawl schedule in the source review and architecture.

Applicable specialized skills: `milestone-delivery`; verify local file, key, and source-data handling.

Expected Git checkpoint: implement, validate, commit, and push each crawler milestone directly to `main`. Do not create milestone branches or bypass repository protections; stop and report if a required check or push is rejected.

### M3 — Validate Jev ranking and zero-cost operations

Goal: Prove the job index and Jev ranking can support a transparent search within the owner's cost ceiling.

Subtasks:

- [ ] Use synthetic CV/listing pairs for ranking evaluation; keep real CV-derived data out of Jev calls until TypeSafe terms and the $5 stop are verified.
- [ ] Compare user/candidate relevance judgments, a keyword baseline, and Jev's bounded scores.
- [ ] Measure top-result relevance, confidence/missingness, hard-filter correctness, duplicate/stale rates, and original-link validity.
- [ ] Add a hard all-in $5/month Jev stop; disable automatic paid-credit refills.
- [ ] Verify local storage, backups, API-key handling, and scheduled crawling run at $0.

Affected areas: Jev adapter, rank/evidence view, local profile/privacy, operations and budget controls.

Dependencies: TypeSafe Order/DPA, local data controls, and approved free sources.

Acceptance criteria:

- [ ] Every displayed fit score has traceable CV/job evidence and a confidence/unknown state; no score implies hiring probability.
- [ ] Hard constraints never pass a benchmark result that violates the user's explicit must-have.
- [ ] Jev pauses at the hard monthly limit and labels unscored listings without using a substitute model.
- [ ] All non-TypeSafe recurring costs are $0 at measured pilot load.

Validation:

- [ ] Written evaluation results and per-search cost ledger.
- [ ] Local deletion and backup test with synthetic data before personal real-CV use.

Documentation updates:

- [ ] Update product definition, cost assumptions, source-of-truth architecture, definition/readiness gate, and decision records.

Applicable specialized skills: `milestone-delivery`; public release-readiness work is out of scope unless the owner later chooses to distribute or host the app.

Expected Git checkpoint: implement, validate, commit, and push each Jev/cost milestone directly to `main`. Do not create milestone branches or bypass repository protections; stop and report if a required check or push is rejected.

## Final integration validation

Source discovery and implementation are tracked separately: the local app is in PLAN-002. Remaining PLAN-001 evidence includes source-by-source terms/access checks, approved-source crawl behavior, Italy eligibility labels, stale/delisted handling, original links, accessibility, Jev cost stop, and source coverage. Do not fetch after an explicit denial or through a restricted access path.

## Rollback / recovery

Disable a connector if terms change, costs appear, rate limits are exceeded, or the source requests removal. Keep source adapters independently switchable. Delete cached postings within source terms and refresh source-state/coverage labels. Stop all Jev calls at the cap. If local execution or acceptable source terms cannot support the personal tool, stop that connector and use another source; do not add paid services.

## Progress

- Research, crawler constraints, candidate table, and gate definition were initially prepared on 2026-09-30.
- Official feed documentation was revisited on 2026-09-30. Jobicy, Remote OK, Remote First Jobs, and Startup Jobs RSS/API paths are the initial private-app feed set with attribution/link/refresh conditions recorded in `source-discovery-and-crawl-review.md`.
- Application, connector, and validation work is tracked in [PLAN-002](PLAN-002-local-first-job-search-app.md); no runtime source validation has been performed yet.

## Implementation discoveries / decisions

- Scrapling is selected. Its documented robots behavior is optional and off by default; set it on explicitly. The Spider also needs explicit global/per-domain concurrency and download-delay settings.
- Scrapling's README advertises anti-bot bypass and proxy rotation. Those features are excluded from the product policy.
- Candidate feeds/APIs with promising $0 paths include Jobicy, Remote OK, Remote First Jobs, Startup Jobs, Adzuna, and a bounded Jooble trial; verify current limits and Italy eligibility before enabling them.
- We Work Remotely and Himalayas have public feed/API guidance that conflicts with broader terms; hold them while using clear alternatives.
- Remotive's public-feed page and general Terms have different apparent scopes; use other free feeds unless that ambiguity is resolved.
- USAJOBS is U.S.-specific and is not a priority for the Milan/Italy pilot.

## Completion evidence

- `docs/research/source-discovery-and-crawl-review.md`
- `docs/decisions/0003-bounded-public-company-crawling.md`
- `docs/readiness/definition-gate.md`
