# Architecture direction

**Status:** PLAN-001 M1/M2 and M3a/M3b plus owner-waiver decisions are pushed to `main`; PLAN-002 M1/M2 and accessibility/privacy fixes are pushed. PLAN-003 M1 manual X lead flow is pushed. PLAN-004 M1 CV-first automated workflow is pushed to `main` at `ea2b73ab53580acee1558b56c2832d50cd4b4e8f`. PLAN-005 M1 local-origin form fix is pushed to `main` at `d2c0a499a62612ad63eece941d0c2289cd6042ee`. TypeSafe account facts and device encryption remain unverified under owner waiver; personal relevance calibration remains open.
**Updated:** 2026-10-01

## Owner-set cost ceiling

This is a single-user local app, not a hosted service. The owner allocates at most **$5 per rolling 30 days to TypeSafe Jev and $0 to every other component or source**. The app reserves against a $4 rolling 30-day request limit, leaving $1 as a planned buffer. This guard covers only requests Clue makes; it cannot cap other uses of the same key or establish account-wide charges. On 2026-09-30 the owner waived TypeSafe account/terms/refill verification; those facts remain unknown and were not inspected. Keep the CV, profile, search settings, listing index, and results on the user's device; after a one-time opt-in, TypeSafe receives selected profile and listing fields automatically after searches when other scoring gates pass.

## System boundary

The local app searches and ranks jobs for its owner. It keeps a candidate profile, search preferences, a local listing index, and fit results on the owner's device. Employers and job boards remain the authorities for whether a position is active and how to apply. TypeSafe Jev is the only planned external evaluator for bounded fit questions.

```mermaid
flowchart LR
    U[Owner] --> A[Local profile and preferences]
    A --> P[Local CV extraction and editable profile]
    U --> Q[Search preferences]
    U --> X[Manual X search and review in owner's browser]
    X --> M[Owner-entered listing and post provenance]
    P --> S[Candidate profile]
    Q --> F[Search and hard filters]
    C[Free public job sources] --> I[Local ingestion and normalization]
    I --> D[Deduplication and freshness]
    D --> F
    M --> D
    S --> E[Jev fit evaluator]
    F --> E
    E --> R[Weighted rank and evidence]
    R --> V[Ranked results, save, hide]
    V --> O[Original job source]
```

The diagram describes the connector-fed local workflow. X leads use a separate manual handoff: the user opens X, reviews an employer listing, and adds it locally. The implementation remains subject to offline validation and source-specific review.

## Component responsibilities

| Component | Responsibility | Boundary |
|---|---|---|
| Local profile and preferences | Save the owner's CV/profile, edits, search preferences, and delete controls on device | No login, account service, or multi-user access. Keep direct identifiers out of Jev payloads. |
| CV extraction | Read PDF and DOCX documents locally, derive profile fields and likely roles, save them, and start a search | Keep the resulting profile editable. Be conservative when inferring roles or language; do not treat an omission as proof of missing capability. |
| Source registry and connectors | Fetch listings through $0 APIs, public feeds, public ATS boards, or ordinary public employer career pages | Each connector records access/terms notes, geography, refresh rules, attribution, local cache/retention, limits, and data expiry. No blanket employer-by-employer opt-in; do not bypass login or access controls. X is manual-only and is never scheduled or fetched. |
| Manual X lead handoff | Build a role/location search link and accept an owner-reviewed X post permalink, employer/ATS URL, and job details | The app makes no X API/site request and never fetches, expands, previews, or automatically opens submitted URLs. Display the destination host and preserve the post URL separately from the job URL. |
| Listing normalization | Map different source fields to a common job record | Preserve original values and provenance; do not invent salary, remote, authorization, or posted-date data. |
| Quality and deduplication | Detect duplicates, expired/closed signals, invalid source URLs, and stale records | Preserve source IDs and canonical application pages so results can be traced. |
| Search filters | Apply exact user-controlled conditions and retrieve likely candidates | Missing values are `unknown`; only exclude unknowns when the user requested that behavior. |
| Jev adapter | Send bounded, minimal state and versioned questions to TypeSafe; retain typed result and uncertainty locally | Protect the API key in local configuration. Treat candidate-derived profile fields as personal data even after direct identifiers are removed. |
| Rank and evidence | Combine criterion results using user weights and attach CV/job evidence | Do not let the model decide permissions, apply, contact, or select a person for an employer. |
| Results UI | Show source, freshness, fit evidence, confidence, and user actions | User opens the original listing; the platform does not submit applications. |

## Data flow and controls

1. Store the original CV locally on the owner's device. Extract a structured, editable profile and start a search from the upload action. The user can correct it later without re-uploading.
2. Keep direct contact details out of the fit request. For matching, send only relevant candidate qualifications/preferences and the normalized job description needed for evaluation.
3. A work history can identify a person even without name or contact details. The app discloses the exact fields sent and requires a one-time opt-in; when enabled, Jev runs automatically after a search if the key, language, and app-side budget gates pass. The owner waived provider-side terms and retention verification for this personal local scope; those details remain unverified.
4. Keep source provenance and freshness in the local listing index. Preserve the employer's posted date separately from first-seen and last-checked dates.
5. For X, keep discovery in the owner's browser. Add only a user-reviewed lead to the local index; label it manually added and do not present the entry time as a live availability check. Do not send X post text to Jev.
6. Make the local delete control cover profile, original CV, extracted data, preferences, saved/hidden jobs, fit results, search history, and owner-added sources. Preserve built-in source definitions, but clear personal role-feed cache hashes and refresh timestamps. Manual backup/restore and local deletion are tested; the owner waived device-encryption confirmation. Deletion cannot affect data already processed by TypeSafe.
7. Keep an audit trail for the scoring version and input snapshot without retaining more personal data than evaluation and support need.

## Search and scoring pipeline

1. Select connectors based on the user's country, query, enabled source rights, and zero-recurring-cost requirement.
2. Fetch from the local listing index and $0 feeds/APIs; do not launch an unbounded crawl for each individual search.
3. Normalize, filter obvious stale/closed records, deduplicate, and keep a direct source URL.
   For a manual X lead, the owner supplies the direct listing URL and the separate X post URL. Clue validates their shape, displays the job-link hostname, and does not make any request to either URL.
4. Apply hard user filters in deterministic code. Keep workplace type, where the person can work from, and work authorization separate. Preserve exact location-eligibility evidence; for the first Milan/Italy search, a generic “remote” label does not confirm the job can be done from Italy.
5. Automatically send up to five filtered listings per Jev request when enabled, with four versioned categorical `Choice` questions per listing: role alignment, skills evidence, experience/scope, and optional preferences. Each question can return `unknown`; missing evidence is not treated as a mismatch. Treat profile and listing fields as untrusted evidence, never as instructions. Jev scoring is currently limited to profile text marked English and listings confidently identified as English. Without opt-in, a key, supported language, or available budget, keep listings visible and explain why they are unscored.
6. Convert the returned 0–4 choice probabilities to a 0–1 fit signal and combine dimensions with the user's weights in code, renormalizing over dimensions with evidence. This is not a calibrated hiring probability.
7. Build reasons from matched profile facts and exact listing text; label absent evidence as unknown. Sort and display the best results and include the sources searched.

## Company-site ingestion and crawler guardrails

Use source-specific ingestion workers behind the source registry. Start with documented APIs/feeds. For company sites, seed from the employer's official careers link or an employer-provided URL, then stay within that career path and any linked public ATS board. Prefer job sitemaps, RSS/Atom, and `JobPosting` JSON-LD. Use HTML selectors as a bounded fallback. Do not brute-force employer or ATS identifiers, crawl unrelated site areas, scrape search-result pages, or begin crawling at user request time.

An ingestion worker can fetch only source-registry entries marked `Approved`: $0 at expected use, a public path suited to personal use, and known attribution/refresh/local-retention rules. Check `robots.txt` and source terms separately; RFC 9309 makes clear that robots rules are not access authorization. Use an honest crawler identity, no more than one request per domain concurrently, a conservative delay (2 seconds by default unless source terms or crawl directives require longer), conditional requests where available, and `Retry-After`. A 401/403/429, CAPTCHA/bot challenge, or explicit block pauses that connector. Never try to get around the block.

The default freshness target is a source check within 24 hours for a “recently checked” label. Source terms or rate limits may require slower refresh. In that case, show the actual last-check age or mark the listing stale/unknown; do not claim it is currently open. Keep publisher `datePosted`, publisher `validThrough`, ingestion time, and last verification as separate fields. A source check records response bytes/status, raw and parsed counts, parser failures, 404 signals, and duplicate merges in the local search history; each job-source link retains its observed/last-seen time and current source state. A 404 marks a check partial and leaves cached jobs stale; a publisher expiration or the source's retention rule controls removal.

Scrapling is the selected crawler for registered public HTML job and career pages, including employer and ATS pages. Use its `Spider` with `robots_txt_obey = True`, `concurrent_requests = 4`, `concurrent_requests_per_domain = 1`, and a base `download_delay = 2.0`; Scrapling applies stricter `Crawl-delay` and `Request-rate` directives by increasing the delay. Set an identifying project User-Agent through ordinary request headers, log at INFO to avoid echoing per-item descriptions, use static HTTP fetching first, and use browser rendering only when necessary and allowed by the source's published rules. A direct job-detail URL uses JSON-LD first and bounded static HTML fallback. Do not use stealth fetchers, proxy rotation, impersonation, anti-bot bypass, or CAPTCHA automation. Keep the crawler behind the connector boundary so it can be replaced if local validation finds a concrete problem. See the [source discovery review](../research/source-discovery-and-crawl-review.md) and [ADR 0003](../decisions/0003-bounded-public-company-crawling.md).

Scrapling automatically retries blocked requests unless configured otherwise. Set `max_blocked_retries = 0`: a `401`, `403`, `429`, challenge, or explicit block stops that source without retry. The five enabled private-app feeds/APIs and their attribution/refresh/retention constraints are recorded in the [source review](../research/source-discovery-and-crawl-review.md). RemoteJobs.org is limited to one page per role query per day, at most four role queries, and its requested “Powered by RemoteJobs.org” attribution is displayed on result, saved, and hidden listing cards.

## Chosen local implementation stack

The first increment uses FastAPI/Uvicorn on `127.0.0.1`, Jinja templates, semantic HTML, project-owned CSS and small vanilla JavaScript, and SQLite through Python's standard library. PDF and DOCX text extraction stays on-device with `pypdf` and `python-docx`. The local database and original CV live in ignored `.data/`; project configuration loads the TypeSafe key from the ignored `.env`. The request boundary accepts `127.0.0.1`, `localhost`, and `::1` as local aliases only when the form origin uses the same scheme and effective port; it rejects external origins. This keeps ingestion, storage, and fit evaluation in one local Python runtime without a separate frontend build, hosted database, or third-party UI service. See [ADR 0005](../decisions/0005-local-python-application.md).

Use TypeSafe's official Python SDK for `/v1/systemone`, with Jev pinned to `jev-1.13.0`. Configure `RetryPolicy(max_retries=0)`. Before each request, reserve an 80,000-token allowance at the current documented input price, then settle successful responses to returned `usage.input_tokens`; ambiguous failures retain the reservation. The app enforces a $4.00 inference cap over a rolling 30-day period, leaving $1.00 of the owner's $5 ceiling as a buffer. See [ADR 0006](../decisions/0006-jev-scoring-and-budget-guard.md).

The local implementation includes profile/CV management, source management, feed/ATS/Scrapling adapters, SQLite persistence, deterministic search, Jev scoring, results, saved/hidden views, and local deletion. PLAN-001 M2 transiently compared one public Prima Lever EU API response with its job page; the board remains disabled in `Review` until ongoing display, refresh, attribution, and retention conditions are checked. PLAN-002 M2 and PLAN-001 M3a used synthetic Jev inputs only; no real CV or live job listing was sent to Jev. M3a's five-item benchmark scored `nDCG@5 = 1.0` for Jev and the keyword baseline on assistant-authored labels, so it confirms the evaluation path but not personal relevance or Jev's advantage. M3b tested local backup/restore and deletion with synthetic data; see the [backup and deletion guide](../operations/local-data-backup-and-deletion.md). The owner waived TypeSafe account verification and device-encryption checks; neither is claimed as verified. The app now requires one-time disclosure/opt-in and automatically checks eligible results after searches. Source-by-source review and personal relevance remain open. PLAN-004 records the CV-first workflow.

## Provider and deployment choices still open

- Geography-specific source coverage beyond the initial Jobicy, RemoteJobs.org, Remote OK, Remote First Jobs, and Startup Jobs feeds; track additional sources in the registry.
- Per-company review and enablement for Greenhouse, Lever, SmartRecruiters, and Scrapling career-page connectors.
- Additional source-specific Scrapling parsers and schedules beyond the single Prima/YLD M2 pilot.
- Per-company source terms, plus display, attribution, refresh, and retention approval before enabling each optional ATS/career source.
- Additional languages and calibrated Jev rubrics; the first implementation only attempts English profile/listing pairs and still needs evaluation.
- Local usability target: WCAG 2.2 AA, a 24-hour freshness label, and 30-second p95 search response against an already indexed dataset.
- Personal relevance calibration; the synthetic benchmark ties the keyword baseline and is not evidence of Jev superiority. The app reserve does not verify or cap account-wide charges.
- Spoken screen-reader review; browser accessibility-tree and keyboard checks are recorded in PLAN-002, while no speech-reader playback control was available.

## Operational constraints

- Do not run Jev over every indexed job on every search. Use metadata filtering and deduplication first.
- Do not claim live availability solely from `datePosted`. Use source status signals, expiration, and a recent check; display when last checked.
- Never fall back invisibly to a different AI model when Jev is unavailable. A search can still show listings with a “fit not evaluated” state.
- Version the question rubric and model ID; sample and review ranking changes before rollout.
- Add a source connector only after checking its public personal-use path, terms, supported geography, attribution, local retention, and $0 recurring cost at expected use.
