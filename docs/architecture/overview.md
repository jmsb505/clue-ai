# Architecture direction

**Status:** PLAN-001 M1 and M2 are pushed and remote-verified on `main` (M2 `0ee104bd699645025980ee8874ebb590846ca3da`); M3 remains active. PLAN-002 M1/M2 are pushed; TypeSafe account terms, real-CV choice, accessibility review, and ranking benchmark remain.
**Updated:** 2026-09-30

## Owner-set cost ceiling

This is a single-user local app, not a hosted service. Spend is capped at **$5 per rolling 30 days for TypeSafe Jev and $0 for every other component or source**. The app reserves against a $4 rolling 30-day inference limit, leaving $1 as an account, tax, or price buffer. This guard covers only requests Clue makes; it cannot cap other uses of the same key. TypeSafe currently lists $42 per billion input tokens and says output is free, but actual credit conversion, taxes, and Order terms must be confirmed. Disable automatic paid-credit refills. Keep the CV, profile, search settings, listing index, and results on the user's device; TypeSafe is the only planned external processing service.

## System boundary

The local app searches and ranks jobs for its owner. It keeps a candidate profile, search preferences, a local listing index, and fit results on the owner's device. Employers and job boards remain the authorities for whether a position is active and how to apply. TypeSafe Jev is the only planned external evaluator for bounded fit questions.

```mermaid
flowchart LR
    U[Owner] --> A[Local profile and preferences]
    A --> P[Local CV extraction and review]
    U --> Q[Search preferences]
    P --> S[Candidate profile]
    Q --> F[Search and hard filters]
    C[Free public job sources] --> I[Local ingestion and normalization]
    I --> D[Deduplication and freshness]
    D --> F
    S --> E[Jev fit evaluator]
    F --> E
    E --> R[Weighted rank and evidence]
    R --> V[Ranked results, save, hide]
    V --> O[Original job source]
```

The diagram describes the current local workflow. The implementation remains subject to offline validation and source-specific review.

## Component responsibilities

| Component | Responsibility | Boundary |
|---|---|---|
| Local profile and preferences | Save the owner's CV/profile, edits, search preferences, and delete controls on device | No login, account service, or multi-user access. Keep direct identifiers out of Jev payloads. |
| CV extraction | Read PDF and DOCX documents and produce a structured profile the user can review | The user reviews extraction before use. Do not treat a parser's omission as proof of missing capability. |
| Source registry and connectors | Fetch listings through $0 APIs, public feeds, public ATS boards, or ordinary public employer career pages | Each source records access/terms notes, geography, refresh rules, attribution, local cache/retention, limits, and data expiry. No blanket employer-by-employer opt-in; do not bypass login or access controls. |
| Listing normalization | Map different source fields to a common job record | Preserve original values and provenance; do not invent salary, remote, authorization, or posted-date data. |
| Quality and deduplication | Detect duplicates, expired/closed signals, invalid source URLs, and stale records | Preserve source IDs and canonical application pages so results can be traced. |
| Search filters | Apply exact user-controlled conditions and retrieve likely candidates | Missing values are `unknown`; only exclude unknowns when the user requested that behavior. |
| Jev adapter | Send bounded, minimal state and versioned questions to TypeSafe; retain typed result and uncertainty locally | Protect the API key in local configuration. Treat candidate-derived profile fields as personal data even after direct identifiers are removed. |
| Rank and evidence | Combine criterion results using user weights and attach CV/job evidence | Do not let the model decide permissions, apply, contact, or select a person for an employer. |
| Results UI | Show source, freshness, fit evidence, confidence, and user actions | User opens the original listing; the platform does not submit applications. |

## Data flow and controls

1. Store the original CV locally on the owner's device. Extract a structured profile, ask the user to correct it, and let them control whether it is retained for saved searches.
2. Keep direct contact details out of the fit request. For matching, send only relevant candidate qualifications/preferences and the normalized job description needed for evaluation.
3. A work history can identify a person even without name or contact details. The product must disclose TypeSafe as a processor, explain the data fields and U.S. processing, use the applicable DPA/transfer terms, and establish lawful notice and retention before live use.
4. Keep source provenance and freshness in the local listing index. Preserve the employer's posted date separately from first-seen and last-checked dates.
5. Make the local delete control cover profile, original CV, extracted data, preferences, saved/hidden jobs, fit results, search history, and owner-added sources. Preserve built-in source definitions, but clear personal role-feed cache hashes and refresh timestamps. Define local backup and TypeSafe deletion behavior before real-CV use.
6. Keep an audit trail for the scoring version and input snapshot without retaining more personal data than evaluation and support need.

## Search and scoring pipeline

1. Select connectors based on the user's country, query, enabled source rights, and zero-recurring-cost requirement.
2. Fetch from the local listing index and $0 feeds/APIs; do not launch an unbounded crawl for each individual search.
3. Normalize, filter obvious stale/closed records, deduplicate, and keep a direct source URL.
4. Apply hard user filters in deterministic code. Keep workplace type, where the person can work from, and work authorization separate. Preserve exact location-eligibility evidence; for the first Milan/Italy search, a generic “remote” label does not confirm the job can be done from Italy.
5. Send up to five filtered listings per Jev request with four versioned categorical `Choice` questions per listing: role alignment, skills evidence, experience/scope, and optional preferences. Each question can return `unknown`; missing evidence is not treated as a mismatch. Jev scoring is currently limited to reviewed profile text marked English and listings confidently identified as English.
6. Convert the returned 0–4 choice probabilities to a 0–1 fit signal and combine dimensions with the user's weights in code, renormalizing over dimensions with evidence. This is not a calibrated hiring probability.
7. Build reasons from matched profile facts and exact listing text; label absent evidence as unknown. Sort and display the best results and include the sources searched.

## Company-site ingestion and crawler guardrails

Use source-specific ingestion workers behind the source registry. Start with documented APIs/feeds. For company sites, seed from the employer's official careers link or an employer-provided URL, then stay within that career path and any linked public ATS board. Prefer job sitemaps, RSS/Atom, and `JobPosting` JSON-LD. Use HTML selectors as a bounded fallback. Do not brute-force employer or ATS identifiers, crawl unrelated site areas, scrape search-result pages, or begin crawling at user request time.

An ingestion worker can fetch only source-registry entries marked `Approved`: $0 at expected use, a public path suited to personal use, and known attribution/refresh/local-retention rules. Check `robots.txt` and source terms separately; RFC 9309 makes clear that robots rules are not access authorization. Use an honest crawler identity, no more than one request per domain concurrently, a conservative delay (2 seconds by default unless source terms or crawl directives require longer), conditional requests where available, and `Retry-After`. A 401/403/429, CAPTCHA/bot challenge, or explicit block pauses that connector. Never try to get around the block.

The default freshness target is a source check within 24 hours for a “recently checked” label. Source terms or rate limits may require slower refresh. In that case, show the actual last-check age or mark the listing stale/unknown; do not claim it is currently open. Keep publisher `datePosted`, publisher `validThrough`, ingestion time, and last verification as separate fields. A source check records response bytes/status, raw and parsed counts, parser failures, 404 signals, and duplicate merges in the local search history; each job-source link retains its observed/last-seen time and current source state. A 404 marks a check partial and leaves cached jobs stale; a publisher expiration or the source's retention rule controls removal.

Scrapling is the selected crawler for registered public HTML job and career pages, including employer and ATS pages. Use its `Spider` with `robots_txt_obey = True`, `concurrent_requests = 4`, `concurrent_requests_per_domain = 1`, and a base `download_delay = 2.0`; Scrapling applies stricter `Crawl-delay` and `Request-rate` directives by increasing the delay. Set an identifying project User-Agent through ordinary request headers, log at INFO to avoid echoing per-item descriptions, use static HTTP fetching first, and use browser rendering only when necessary and allowed by the source's published rules. A direct job-detail URL uses JSON-LD first and bounded static HTML fallback. Do not use stealth fetchers, proxy rotation, impersonation, anti-bot bypass, or CAPTCHA automation. Keep the crawler behind the connector boundary so it can be replaced if local validation finds a concrete problem. See the [source discovery review](../research/source-discovery-and-crawl-review.md) and [ADR 0003](../decisions/0003-bounded-public-company-crawling.md).

Scrapling automatically retries blocked requests unless configured otherwise. Set `max_blocked_retries = 0`: a `401`, `403`, `429`, challenge, or explicit block stops that source without retry. The five enabled private-app feeds/APIs and their attribution/refresh/retention constraints are recorded in the [source review](../research/source-discovery-and-crawl-review.md). RemoteJobs.org is limited to one page per role query per day, at most four role queries, and its requested “Powered by RemoteJobs.org” attribution is displayed on result, saved, and hidden listing cards.

## Chosen local implementation stack

The first increment uses FastAPI/Uvicorn on `127.0.0.1`, Jinja templates, semantic HTML, project-owned CSS and small vanilla JavaScript, and SQLite through Python's standard library. PDF and DOCX text extraction stays on-device with `pypdf` and `python-docx`. The local database and original CV live in ignored `.data/`; project configuration loads the TypeSafe key from the ignored `.env`. This keeps ingestion, storage, and fit evaluation in one local Python runtime without a separate frontend build, hosted database, or third-party UI service. See [ADR 0005](../decisions/0005-local-python-application.md).

Use TypeSafe's official Python SDK for `/v1/systemone`, with Jev pinned to `jev-1.13.0`. Configure `RetryPolicy(max_retries=0)`. Before each request, reserve an 80,000-token allowance at the current documented input price, then settle successful responses to returned `usage.input_tokens`; ambiguous failures retain the reservation. The app enforces a $4.00 inference cap over a rolling 30-day period, leaving $1.00 of the owner's $5 ceiling as a buffer. See [ADR 0006](../decisions/0006-jev-scoring-and-budget-guard.md).

The local implementation includes profile/CV review, source management, feed/ATS/Scrapling adapters, SQLite persistence, deterministic search, Jev scoring controls, results, saved/hidden views, and local deletion. PLAN-001 M2 transiently compared one public Prima Lever EU API response with its job page; the board remains disabled in `Review` until ongoing display, refresh, attribution, and retention conditions are checked. PLAN-002 M2 verified Jev with one synthetic live call; no CV or job listing was sent to Jev. No listing from the source comparison was persisted to `.data/`. Real-CV use remains gated on TypeSafe terms, local privacy controls, source review, and ranking evidence. See [PLAN-001](../plans/PLAN-001-free-local-source-discovery.md) and [PLAN-002](../plans/PLAN-002-local-first-job-search-app.md) for evidence and remaining gates.

## Provider and deployment choices still open

- Geography-specific source coverage beyond the initial Jobicy, RemoteJobs.org, Remote OK, Remote First Jobs, and Startup Jobs feeds; track additional sources in the registry.
- Per-company review and enablement for Greenhouse, Lever, SmartRecruiters, and Scrapling career-page connectors.
- Additional source-specific Scrapling parsers and schedules beyond the single Prima/YLD M2 pilot.
- Local deletion and backup behavior; TypeSafe telemetry, retention, deletion, and international transfer terms.
- TypeSafe account terms and billing settings, including the user's applicable DPA, privacy/retention conditions, credit/refill settings, actual request limits, and account availability.
- Additional languages and calibrated Jev rubrics; the first implementation only attempts English profile/listing pairs and still needs evaluation.
- Local usability target: WCAG 2.2 AA, a 24-hour freshness label, and 30-second p95 search response against an already indexed dataset.
- Measured Jev usage and score calibration on synthetic CV/listing pairs; the application reservation is not a substitute for provider billing controls.

## Operational constraints

- Do not run Jev over every indexed job on every search. Use metadata filtering and deduplication first.
- Do not claim live availability solely from `datePosted`. Use source status signals, expiration, and a recent check; display when last checked.
- Never fall back invisibly to a different AI model when Jev is unavailable. A search can still show listings with a “fit not evaluated” state.
- Version the question rubric and model ID; sample and review ranking changes before rollout.
- Add a source connector only after checking its public personal-use path, terms, supported geography, attribution, local retention, and $0 recurring cost at expected use.
