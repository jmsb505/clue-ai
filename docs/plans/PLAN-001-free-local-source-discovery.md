# PLAN-001 — Free source discovery and local crawl pilot

Status: ACTIVE — M1/M2, M3a, and M3b pushed and remote-verified on `main`; owner waived TypeSafe account/terms and device-encryption checks; personal relevance calibration remains open
Created: 2026-09-30  
Last updated: 2026-09-30

## Objective

Determine which $0 sources can support the first personal search—fully remote jobs performable from Milan/Italy, including listings explicitly open to Europe or worldwide—and assess whether a controlled local crawler adds fresh, traceable postings without bypassing site controls or exceeding the Jev-only $5/month budget.

## Motivation

Paid job aggregators and paid infrastructure are outside the owner's budget. Free feeds, public ATS endpoints, and employer career pages offer complementary paths, but broad coverage is fragmented. The platform needs a source list, repeatable registration, truthful coverage reporting, and crawl-quality evidence before it makes coverage claims.

## Current state

- Product definition, reference/market research, source discovery policy, and architecture are documented.
- The public GitHub repository exists; PLAN-002 M1 is implemented, validated, and pushed to `main` at `00e8398d8a0d73082bb3d9217633f169b92a339c`. PLAN-001 M1 is separately pushed and verified at `69f536ee00e3eadc50fd877d99c87371add387d5`; PLAN-001 M2 was pushed separately and remote-verified at `0ee104bd699645025980ee8874ebb590846ca3da`.
- Scrapling remains the selected crawler. Its robots-aware, bounded Spider now covers direct job pages through JSON-LD or static HTML fallback, and M2 compared one Lever EU API listing with its public page. Other individual employer/ATS sources remain `Review` until approved per board.
- The five-source feed/API registry was smoke-validated through the app's host-restricted fetcher. M2 validates an EU Lever API/page comparison as a transient parser experiment; that employer board remains disabled in `Review`, as do other ATS sources, until ongoing-use conditions are checked. On 2026-09-30 the owner waived TypeSafe account/terms verification and local device-encryption confirmation. Account-level details remain unverified; no real candidate data was sent during implementation.

## Desired state

A single-user local build can retrieve postings only from source-registry entries approved for personal use, retain provenance and freshness on the owner's device, deduplicate safely, and use Jev within a hard $5/month cap. All other services and data sources cost $0. Results disclose source coverage and link to the provider or original posting. The owner still applies externally.

## Scope

- Create and maintain a local source registry for access/terms notes, allowed paths/endpoints, geography, costs, attribution, limits, refresh interval, local retention, and parser version.
- Verify a representative set of Italy/Europe-relevant job feeds, APIs, ATS boards, and employer career pages. A generic `remote` label is not proof that someone can work from Italy.
- Use Scrapling for registered public company-career pages, configured for ordinary, low-rate, robots-aware requests without stealth or bypass features.
- Measure coverage, freshness, parse success, duplicate/link quality, and incremental operating cost.

## Out of scope

- A public or multi-user service, claims of internet-wide completeness, paid job data, paid infrastructure, proxies, hosted scraping services, search-engine-result scraping, or closed-board scraping.
- Logged-in access, applying, submitting applications, scraping applicant portals, anti-bot/CAPTCHA bypass, or sending real CV-derived fields without the local disclosure/opt-in and an explicit scoring action.
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
- A local Jev spend-stop design. The owner later waived checking TypeSafe account/terms details; those remain unverified, while the app-side rolling reserve remains in force.
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

- [x] Use Milan/Italy with fully remote work as the first validation profile; take role families from the CV/user query. Do not hard-code this profile into the product.
- [x] Inventory official employer URLs, documented ATS APIs, feeds with clear personal-use terms, and relevant public employment-service sources for that input.
- [x] Mark every source `Approved`, `Review`, or `Blocked`; record the documented access path, cost, quota, attribution, cache window, refresh, and canonical links. Exclude sources whose published rules do not support the planned personal use.
- [x] Confirm each approved source costs $0 at expected test volume.

Affected areas: source registry, ingestion connectors, product coverage disclosure.

Dependencies: documented source paths and any free key registration required by a connector.

Acceptance criteria:

- [x] Every enabled source has a documented personal-use path, $0 cost, attribution, direct-link, local retention, and refresh rules.
- [x] Every result preserves location-eligibility evidence and is labeled `Eligible here`, `Needs verification`, `Not eligible`, or `Unknown`; only explicit Italy/EU/EEA/Europe/worldwide eligibility counts as confirmed for the first profile.
- [x] The coverage report names excluded/under-review sources and does not claim completeness.

Validation:

- [x] Manual primary-source terms/API review for each enabled source.
- [x] Manually inspect representative source listings, Italy/Europe eligibility language, and original URLs.
- [x] Add offline connector tests for RemoteJobs.org parsing, host confinement, role-query limit/encoding, daily refresh suppression, source attribution, and links. Automated tests make no source network calls.

Documentation updates:

- [x] Update the source registry, source review, ADR 0003, and gate with the actual geography-specific evidence.

Applicable specialized skills: `context7-mcp` for current library/API documentation; recheck the source and TypeSafe documentation before live use with the owner's CV.

Expected Git checkpoint: implement, validate, commit, and push each source milestone directly to `main`. Do not create milestone branches or bypass repository protections; stop and report if a required check or push is rejected.

### M2 — Implement and validate a controlled Scrapling crawler

Goal: Implement the selected Scrapling adapter and validate it on a small set of documented public endpoints/pages with ordinary, identifiable requests. A transient technical sample may validate parsing where published API documentation supports public retrieval; it does not approve a board for scheduled ingestion, durable caching, or display. Keep such boards disabled in `Review` until those ongoing-use conditions are checked.

Subtasks:

- [x] Compare a documented Lever EU postings API response with static JSON-LD from the same public posting; separately record Greenhouse's ambiguous HTTP-200 detector signal without repeating the request. Prima and YLD remain disabled in `Review` pending ongoing-use checks.
- [x] Use Scrapling Spider for registered public pages; set `robots_txt_obey = True`, `concurrent_requests = 4`, `concurrent_requests_per_domain = 1`, and a base `download_delay = 2.0`.
- [x] Set an identifying User-Agent with ordinary request headers; rely on Scrapling's robots-aware delay for stricter `Crawl-delay` and `Request-rate` values.
- [x] Static API/JSON-LD was sufficient, so dynamic rendering was unnecessary. No stealth, proxies, or bypass were used.
- [x] Capture parse failures, 401/403/429/block signals, 404/not-found signals, expired postings, duplicate counts, response sizes, HTTP status, and last-seen timestamps in source/search records.

Affected areas: crawler adapter, source registry, normalized listing schema, source-health monitoring.

Dependencies: M1 source set and the owner's local computer; no paid compute or hosted crawl service.

Acceptance criteria:

- [x] Every result retains a canonical source URL, source ID, observed time, posted date when supplied, and source state.
- [x] Explicit source-denial/challenge and rate-limit signals stop the connector without an evasion attempt; offline tests distinguish ordinary CAPTCHA-related page text from explicit challenge messages. The earlier YLD signal came from the then-broad detector, is ambiguous, and was not retried.
- [x] Results marked “recently checked” meet the defined 24-hour freshness target; older results are labeled stale/unknown.
- [x] No non-TypeSafe spend was incurred.

Validation:

- [x] Manual transient parser comparison and source-link audit for the Prima Lever EU listing; YLD's earlier ambiguous detector observation was recorded without a repeat request. Both boards remain disabled in `Review` for ongoing use.
- [x] Document stale, 404/expired, and duplicate handling from the live sample plus offline fixtures; do not send live CVs.

Documentation updates:

- [x] Record parser coverage, source limitations, data retention, and crawl schedule in the source review and architecture.

Applicable specialized skills: `milestone-delivery`; verify local file, key, and source-data handling.

Expected Git checkpoint: implement, validate, commit, and push each crawler milestone directly to `main`. Do not create milestone branches or bypass repository protections; stop and report if a required check or push is rejected.

### M3 — Jev ranking validation and zero-cost local operation

Goal: Validate the scorer on synthetic job data, verify local controls, and record owner decisions about account-level spend and personal data. Deliver M3a and M3b as separate validated `main` checkpoints. M3c records the owner's account-check waiver; personal relevance calibration remains open.

#### M3a — Synthetic ranking benchmark

Goal: Compare Jev's bounded scores with a simple keyword baseline on a reproducible synthetic-only dataset, and verify hard filters and score evidence.

Subtasks:

- [x] Create one synthetic candidate and eight synthetic listings; send only the five hard-filter-eligible listings to Jev in one batch.
- [x] Compare fixed synthetic reference grades, keyword phrase counts, and Jev's weighted scores. Labels were authored for this scenario and are not the owner's personal relevance judgments.
- [x] Measure top-result relevance, confidence, filter false-pass/reject count, duplicate/stale records, canonical-link structure, and request cost.
- [x] Keep all candidate/job inputs synthetic and use a disposable local database that is removed after metrics are read.

Affected areas: evaluation runner, Jev score integration, deterministic filters, and evaluation evidence.

Dependencies: current Jev API key and an app-side budget reserve; no real CV or source listing.

Acceptance criteria:

- [x] The final benchmark run uses one API request, scores five listings, preserves four score dimensions/evidence, and reports confidence and cost.
- [x] Hard filters return all five expected examples with zero false passes and zero false rejects.
- [x] The Jev and keyword rankings are both compared to the synthetic relevance grades, with limitations documented.

Validation:

- [x] Offline suite tests dataset filters, metric bounds, duplicate/stale/link evidence, and one-batch temporary-ledger handling.
- [x] Final synthetic request: one Jev batch, five scored, no unscored results, `$0.000259434` app-ledger cost. A corrected preceding attempt lost its temporary usage record after the database directory was removed; the bound and correction are disclosed in `docs/evaluations/PLAN-001-M3-synthetic-jev.md`.
- [x] The exploratory first run is superseded: a fixture's negative sentence contained a required keyword and duplicate titles made its ranking ambiguous.

Documentation updates: `docs/evaluations/PLAN-001-M3-synthetic-jev.md`, architecture, roadmap, and readiness gate.

Expected Git checkpoint: one `main` commit for the benchmark code, tests, evidence, and source-of-truth updates; record and verify the remote SHA before starting M3b.

#### M3b — Local storage and backup behavior

Goal: Verify local deletion and a manual, zero-cost backup/restore path using synthetic data. Do not add an automatic/cloud backup service.

Subtasks:

- [x] Test copying a stopped app's `.data/` directory and restoring its database/profile/CV with synthetic data.
- [x] Verify `.env` and `.data/` remain Git-ignored; document that the key is not included in data backups.
- [x] Document that backups must use a user-selected encrypted offline destination and are not deleted by the in-app deletion action.
- [x] Confirm there is no recurring scheduler: source refresh and score orchestration run only after the user starts a search or scoring action. Jev remains separately budgeted; no other hosted or paid compute is added.

Acceptance criteria:

- [x] A synthetic copy can restore the local profile and CV; the existing delete test removes the active local profile, CV, history, jobs, and Jev ledger.
- [x] Backup limitations, encryption responsibility, key recovery, and deletion scope are visible in operating documentation.
- [x] No recurring non-TypeSafe cost or hosted backup path is introduced.

Expected Git checkpoint: separate validated M3b commit pushed directly to `main`.

#### M3c — Owner gate reconciliation and relevance follow-up

Goal: Record the owner's explicit scope choices without treating an unverified provider fact as validated evidence.

Owner decisions recorded on 2026-09-30:

- [x] Waive verification of the applicable TypeSafe Order, account credit conversion, refill toggle, account-wide spend, and provider terms for this single-user local project. No authenticated account or undocumented endpoint was inspected. These facts remain unknown, not confirmed.
- [x] Waive confirmation of device encryption for the local `.data/` directory and local backups. The project does not claim encryption or Windows permission evidence.
- [x] Keep the application-side Jev reserve at `$4` per rolling 30 days toward the owner's `$5` ceiling, with `$0` allocated to all other services. This controls only requests sent by Clue and does not prove an account-wide cap.
- [x] Keep raw CV files and direct contact fields out of Jev payloads. The app retains its data disclosure, opt-in, and explicit per-search scoring action; no real CV was sent during implementation.

Open owner choice:

- [ ] Review the synthetic relevance examples and provide personal judgments, or explicitly defer calibration. Until then, the benchmark remains integration evidence, not proof of personal usefulness or ranking quality.

The public model/API/legal research remains historical context in the M3a evaluation. The user waived further TypeSafe-side verification; this is a scope decision, not acceptance or validation of account-specific terms.

Expected Git progression: push this decision record with the current validated milestone checkpoint. Personal calibration can be closed by a later owner decision; no alternate model is permitted.

## Final integration validation

Source discovery and implementation are tracked separately: the local app is in PLAN-002. PLAN-001 M1 feed/API selection and M2's one-source API/page comparison are separately pushed and remote-verified on `main`; M2 SHA is `0ee104bd699645025980ee8874ebb590846ca3da`. M3a's synthetic Jev benchmark is pushed and remote-verified at `31c2479a593795f67a4cb67e6afebaefcb71f9b8`. M3b's manual backup/restore behavior is pushed and remote-verified at `9399ad81e0cd34ed244045d4ab52e70d0e4a7245`. M3c records the owner's waiver of TypeSafe account checks and device-encryption confirmation; account facts remain unverified, and personal relevance calibration is open. Do not fetch after an explicit denial or through a restricted access path.

## Rollback / recovery

Disable a connector if terms change, costs appear, rate limits are exceeded, or the source requests removal. Keep source adapters independently switchable. Delete cached postings within source terms and refresh source-state/coverage labels. Stop all Jev calls at the cap. If local execution or acceptable source terms cannot support the personal tool, stop that connector and use another source; do not add paid services.

## Progress

- Research, crawler constraints, candidate table, and gate definition were initially prepared on 2026-09-30.
- The initial approved set is Jobicy, RemoteJobs.org, Remote OK, Remote First Jobs, and Startup Jobs. M1 records terms, costs, limits, direct links, attribution, app refresh/retention, exclusions, and geography evidence in `docs/research/source-discovery-and-crawl-review.md`.
- One live request per existing feed was made through the bounded production fetcher: 200 Jobicy, 99 Remote OK, 100 Remote First Jobs role-feed, and 50 Startup Jobs records parsed. No jobs or CV data were persisted or sent to Jev.
- One RemoteJobs.org API page returned 50 records with pagination total 5,728: 13 were explicitly eligible by current location-language rules, 28 needed verification, and 9 were not eligible. The sample “Anywhere in the World” was linked directly; that detail page could not be fetched by the web research viewer.
- A second, synthetic `software engineer` request through the new production connector returned 50 listings: 8 explicitly eligible, 24 needing verification, and 18 not eligible. All 50 canonical links stayed on `remotejobs.org`; the temporary database recorded the query hash but no listing rows and was deleted after the smoke check.
- Representative official listings were reviewed: Jobicy Nash EAE UK/Europe (explicit Europe), Remote OK Sofia role (contradictory broad remote label and Bulgaria/relocation text), and Startup Jobs Smartcat EMEA (London and customer travel; not confirmed from Italy). No remote/EMEA label alone was promoted to confirmed eligibility.
- `remotejobs_api` was added with one daily 50-record request per role query, up to four queries, 14-day retention, exact visible credit, and direct listing links. Offline connector and UI attribution tests were added; full results are recorded below after validation.
- M1 validation in Conda `gen`: 44 tests passed, Ruff passed, and `compileall` passed. The one Starlette/AnyIO deprecation warning originates upstream and did not fail the run.
- PLAN-001 M1 was committed and pushed directly to `main` as `69f536ee00e3eadc50fd877d99c87371add387d5`; `git ls-remote` matched that SHA. No API key, CV, listing data, or local database entered Git.
- M2 live evidence is recorded in `docs/research/source-discovery-and-crawl-review.md`. The Prima EU API returned 90/90 parsed records in one request; its public page returned one JSON-LD posting with the same canonical URL, and the host's `robots.txt` allowed the request. YLD's API returned five postings; its public page returned HTTP 200 but Scrapling signaled a block, so it was not retried.
- M2 validation in Conda `gen`: 50 tests passed, Ruff passed after an import-order correction, byte-compilation passed, and `git diff --check` passed. Separate milestone commit `0ee104bd699645025980ee8874ebb590846ca3da` was pushed to `main`; `git ls-remote origin refs/heads/main` matched that SHA.
- No real CV, Jev request, app database, or job listing was persisted or sent to Jev during PLAN-001 M2. The public-source checks cost `$0`.
- PLAN-001 M3a adds a repeatable synthetic-only runner and records its one-request/five-listing results, comparison with the keyword baseline, methodology defects corrected during the run, and known cost uncertainty in `docs/evaluations/PLAN-001-M3-synthetic-jev.md`. The result is an integration check, not evidence of personal relevance or Jev superiority.
- PLAN-001 M3b's synthetic backup/restore and deletion tests passed in Conda `gen`; `.env` and `.data/` remain ignored. Operating limits are documented in `docs/operations/local-data-backup-and-deletion.md`. Refresh and score orchestration use request-triggered in-process tasks, with no recurring scheduler or extra hosted compute. Commit `9399ad81e0cd34ed244045d4ab52e70d0e4a7245` is pushed to and verified on `main`.
- PLAN-001 M3c records the owner waiver; personal relevance calibration remains open. PLAN-002 tracks spoken screen-reader review and the app's per-search Jev controls.

## Implementation discoveries / decisions

- Scrapling is selected. Its documented robots behavior is optional and off by default; set it on explicitly. The Spider also needs explicit global/per-domain concurrency and download-delay settings.
- Lever's public postings API has separate global and EU hosts. The connector now selects the host from the saved source region; otherwise an EU board such as Prima returns HTTP 404 from the global endpoint.
- The crawler captures response bytes/status, raw and parsed record counts, parser failures, not-found pages, source state, and duplicate merges. A 404 keeps cached listings stale; publisher `validThrough` and configured source-retention rules control expiry/removal.
- A direct job-detail URL is parsed from JSON-LD first and can use the bounded static HTML fallback. The pilot needed no browser rendering. Spider item logging is set to INFO so full descriptions are not echoed in local debug output.
- Scrapling's README advertises anti-bot bypass and proxy rotation. Those features are excluded from the product policy.
- The five enabled sources are the only currently approved app feeds/APIs. Adzuna and Jooble need owner-supplied registration keys; Remote Landers lacks descriptions for Jev and is metadata-only; EURES remains manual-only until an official vacancy API/reuse path is documented.
- Remote First Jobs' JSON API overlaps its RSS corpus and delays publication by 24 hours, so it is not enabled alongside the fresher RSS.
- We Work Remotely and Himalayas have public feed/API guidance that conflicts with broader terms; hold them while using clear alternatives.
- Remotive's public-feed page and general Terms have different apparent scopes; use other free feeds unless that ambiguity is resolved.
- USAJOBS is U.S.-specific and is not a priority for the Milan/Italy pilot.

## Completion evidence

- `docs/research/source-discovery-and-crawl-review.md`
- `docs/decisions/0003-bounded-public-company-crawling.md`
- `docs/readiness/definition-gate.md`
- `docs/evaluations/PLAN-001-M3-synthetic-jev.md`
- `docs/operations/local-data-backup-and-deletion.md`
