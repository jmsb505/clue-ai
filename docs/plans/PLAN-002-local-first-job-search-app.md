# PLAN-002 — First local job-search application

**Status:** M1 VALIDATED LOCALLY — direct push to `main` pending; M2 synthetic Jev check remains
**Created:** 2026-09-30
**Last updated:** 2026-09-30

## Objective

Deliver the first usable, single-user local app that lets its owner review a CV-derived profile, configure a job search, gather jobs through a transparent set of free sources, filter deterministically, evaluate fit with TypeSafe Jev when configured, and save or dismiss listings. Finish all local wiring before the first validation pass. Keep the Jev API key in a local ignored `.env` file; do not commit a credential.

## Motivation

The product definition and source research support a local feasibility increment. The owner wants the broadest practical search possible at $0 recurring cost outside Jev, with Scrapling available for registered public career pages. M1 is implemented and offline-validated on the local `main` checkout. The owner has directed milestone commits and pushes to `main`, with no new branches.

## Current state

- `main` contains the product, architecture, source-policy, and research baseline at `617f5c8`; `origin` points to `https://github.com/jmsb505/clue-ai.git`.
- The local checkout is on `main`, based on `617f5c8`. M1 implementation, docs, and offline tests pass; the main commit and push are the next delivery action.
- Each later milestone will be validated and pushed directly to `main` before work advances. Required protections/checks will be honored; a remote rejection will be reported without bypass.
- A local ignored `.env` exists with the owner's TypeSafe key configured; its value has not been displayed or staged. `.env.example` contains a blank `TYPESAFE_API_KEY=` placeholder. `.gitignore` excludes `.env`, `.data`, local uploads, databases, virtual environments, and test caches.
- The selected runtime is FastAPI/Uvicorn, Jinja, Python SQLite, pypdf/python-docx, Scrapling 0.4.15 with its `fetchers` extra, and the TypeSafe SDK. Scrapling's Python dependencies are installed; no browser binaries are used. TypeSafe documents the System One endpoint and Jev model; its legal page links to the account agreement, privacy policy, and DPA. Real-CV use remains gated until those applicable terms are reviewed.
- Current source review establishes four promising no-key discovery paths: Jobicy public API, Remote OK public JSON/RSS, Remote First Jobs RSS, and Startup Jobs RSS. Each requires source credit and original links; only the documented RSS/public paths are in scope. Company-specific ATS endpoints and career-page crawls remain per-source review items.

## Desired state

A browser-based app bound to localhost stores the CV, edited candidate profile, searches, job index, and saved/hidden state in a local SQLite database and local data directory. Its initial search defaults to fully remote work from Milan/Italy but keeps search geography editable. It fetches only approved sources whose refresh interval has elapsed, identifies every source checked, preserves canonical job links, and pauses a connector on denials, rate limits, or challenges. Jev remains optional until `TYPESAFE_API_KEY` is supplied, evaluates a bounded batch using typed questions, and does not receive direct contacts or the raw CV. An in-app rolling 30-day reserve stops app-initiated usage at $4.00, leaving $1.00 of the owner's $5 ceiling as a buffer; provider-side automatic refills must remain off. The UI supports profile review, search, transparent results, save/hide/open-source actions, source management, and local deletion.

## Scope

- Local Python application: FastAPI, server-rendered Jinja templates, semantic HTML, vanilla CSS/JavaScript, and SQLite through the Python standard library.
- Local PDF/DOCX text extraction and editable profile review using `pypdf` and `python-docx`; no CV text is sent before user review.
- Optional TypeSafe Python SDK adapter, pinned to the current stable Jev version (`jev-1.13.0`), with retries disabled for bounded spend, typed criteria, response parsing, and a persistent local usage ledger.
- Initial no-key connectors: Jobicy JSON API, Remote OK JSON feed, and the free RSS paths from Remote First Jobs and Startup Jobs. Keep source attribution and the canonical listing link. Refresh Jobicy no more than hourly; use conservative daily/few-times-daily intervals elsewhere.
- A source registry with `Approved`, `Review`, and `Blocked` states. Implement general Greenhouse, Lever, SmartRecruiters, and Scrapling public-page adapters behind this registry; seed them disabled until the specific source's use, caching, attribution, and refresh conditions have been reviewed.
- Normalized listings with provenance, posted/checked dates, workplace and location-eligibility evidence, source expiry, de-duplication, deterministic hard filters, and Jev fit ranking.
- Local profile and search persistence, saved/hidden listings, source controls, job details, and a single explicit local-data deletion action.
- Ignored local `.env` for the owner's API key, a committed `.env.example` with a blank key, and setup documentation.
- First validation only after the app paths are wired: local tests with synthetic CVs, fixture feeds/pages, and a mocked Jev client; no live feed/crawl or paid API requests during automated validation.

## Out of scope

- Public hosting, accounts, multi-user use, cloud data storage, analytics, email, or paid services.
- Automated applications, form filling, employer contact, or candidate-side inference of protected/sensitive traits.
- Scraping logged-in boards, search-engine results, LinkedIn, or a source in `Review`/`Blocked`; anti-bot bypass, proxies, stealth, browser impersonation, CAPTCHA handling, and retries around denials.
- Sending the owner's real CV or profile to Jev before the owner has reviewed the applicable TypeSafe account/DPA/privacy terms and the app's minimization and deletion behavior.
- Claims of complete internet-wide coverage or calibrated hiring probability.
- A live Jev request or live cost/accuracy claim before the owner supplies the key and approves a synthetic-only integration check.

## Source-of-truth impact

- Product requirements and score semantics: `docs/product-definition.md`
- Local system boundaries and privacy: `docs/architecture/overview.md`
- Current source evidence and default seed set: `docs/research/source-discovery-and-crawl-review.md`
- UI pattern evaluation: `docs/research/ui-ux-implementation-review.md`
- Architecture decisions: `docs/decisions/0005-local-python-application.md` and `docs/decisions/0006-jev-scoring-and-budget-guard.md`
- Progress and gates: `docs/roadmap.md`, `docs/readiness/definition-gate.md`, and `docs/plans/PLAN-001-free-local-source-discovery.md`
- User setup: `README.md` and `.env.example`

## Existing decisions and constraints

- Single-user, local-first app; no login or public service.
- User-selectable geography; first validation search is fully remote and explicitly Italy/EU/Europe/worldwide eligible from Milan.
- TypeSafe Jev is the required fit evaluator; the user supplies the API key.
- Recurring cost ceiling is $0 for every source/service except Jev, with a hard $5 per rolling 30-day owner ceiling. The app's $4.00 rolling inference reservation leaves a $1.00 margin for price/tax/account variation; automatic provider refills stay off.
- CVs and profile data remain local until an explicit Jev action. Contact fields and raw CV files are excluded from request payloads. Work history can still identify the candidate, so it remains personal data.
- Source use is per connector, not inferred from public access or `robots.txt` alone. Stop on block signals; no circumvention.
- No automatic application behavior.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, and `ponytail-balanced` for plan, delivery, and maintainability.
- `ui-ux-research` and `frontend-design` for the local search/review interface.
- Context7 documentation was consulted for FastAPI file/template handling, Scrapling Spider/robots/retry behavior, TypeSafe's Python SDK and typed questions, `pypdf`, and `python-docx`.
- Current TypeSafe model/API/legal references: `https://docs.typesafe.ai/models`, `https://docs.typesafe.ai/api`, `https://docs.typesafe.ai/sdk/python/api/clients/sync`, and `https://docs.typesafe.ai/legal`.
- Current free-source terms: `https://jobicy.com/jobs-rss-feed`, `https://remoteok.com/faq`, `https://remotefirstjobs.com/rss`, and `https://startup.jobs/api` plus `https://startup.jobs/terms`.

## Dependencies

- Python 3.10 or newer, as required by the current TypeSafe Python SDK docs.
- Local packages: FastAPI, Uvicorn, Jinja2, `python-multipart`, Scrapling, `typesafe-sdk`, `pypdf`, and `python-docx`.
- No startup secret is required. Live Jev requires the owner to add a TypeSafe API key to the local ignored `.env` after implementation.
- ATS sources require the owner to identify company board tokens/IDs and finish their per-source review before activation. The initial four remote-job sources require no key on the documented paths.
- TypeSafe account terms and billing settings remain a gate before real CV use.

## Risks and unknowns

- Feed terms and content schemas can change. Preserve source states and direct links; keep `Review` sources disabled; record source check time and parser errors.
- Generic `remote`, EMEA, or timezone language does not establish Italy work eligibility.
- CV extraction can fail on scanned PDFs or complex layouts. Make text review/editing explicit; do not silently assume the extracted profile is complete.
- The TypeSafe key may be unable to bill or the API may change. Missing key and API errors must leave results visible as unscored.
- API-reported token usage is known only after a successful response. Reserve 80,000 input tokens at current list price before each request, settle to actual input usage after success, and retain the reservation after ambiguous failures. The 80k accounting reserve exceeds the documented 64k model context and may stop scoring early.
- A local source refresh can take time or lose network access. Run it as a background operation with a visible state and preserve already indexed results.
- Locale, taxes, TypeSafe terms, retention, and account refills can affect total cost; application accounting cannot control unrelated calls using the same key.
- The selected Conda `gen` environment provides Python 3.10.21. Launch the app with `python -m clue_ai`; the app does not require Node or `uv`.

## Milestones

### M1 — Wire the complete local personal-search workflow

**Goal:** A coherent localhost app can ingest, normalize, filter, score (when configured), and review jobs while preserving local-data and source rules. All paths are wired before validation begins.

**Subtasks:**

- [x] Establish the Python project, runtime/config, SQLite schema, local data directory, localhost-only server, and HTML/CSS shell.
- [x] Build accessible onboarding/profile review with PDF/DOCX extraction, manual correction, local persistence, and deletion.
- [x] Implement source registry, seeded no-key feeds, source-specific refresh limits and attribution, standard ATS connectors in `Review`, and a bounded Scrapling adapter that never bypasses blocks.
- [x] Implement common job normalization, location-eligibility evidence, expiry/freshness, de-duplication, deterministic hard filters, and coverage reporting.
- [x] Implement TypeSafe client and versioned fit rubric, minimal payload, optional key behavior, cost ledger/reservation, explicit unscored states, and user-weighted rank.
- [x] Build results/detail/saved/hidden/source/settings views and forms. Make original source links the only application route.
- [x] Create `.env` as a local ignored key file and commit `.env.example` plus a key-setup guide without any secret.
- [x] Update README, architecture, ADRs, source research, roadmap, and readiness gates to describe the implementation and remaining real-CV/API gates.

**Affected areas:** application package, templates/static files, Python project metadata/dependencies, `.env.example`, `.gitignore`, and source-of-truth documentation.

**Dependencies:** Existing product definition; TypeSafe docs and source terms reviewed above; no Jev key or real CV required for implementation.

**Acceptance criteria:**

- [x] The app launches on localhost with no key, keeps all profile/job state in the local data directory, and never logs the key or candidate payload.
- [x] PDF/DOCX upload is validated and extracted locally; extracted facts are editable; Jev sends neither raw CV nor direct contact fields.
- [x] Initial no-key feeds are limited to Jobicy, Remote OK, Remote First Jobs, and Startup Jobs with source credits, original links, and documented refresh limits. No `Review`/`Blocked` source fetches by default.
- [x] Company ATS/page adapters are source-specific, require `Approved` state, use ordinary requests and Scrapling `robots_txt_obey=True`, set one request/domain and a conservative delay, and stop without retry on 401/403/429/challenge.
- [x] Listings preserve source, source ID, canonical URL, source-posted date when supplied, first-seen/last-check times, location eligibility evidence/status, and an unscored reason when appropriate.
- [x] Deterministic hard constraints run before Jev. Unknown location evidence remains unknown; the UI never treats a generic remote label as Italy eligibility.
- [x] With no Jev key, results remain visible with “fit not evaluated.” With a key, the SDK uses versioned typed questions, bounded batches, disabled retries, and a monthly reserve that stops before the $4.00 app inference cap.
- [x] Save/hide/open-source actions work; the delete flow removes CV, profile, searches/preferences, indexed/saved results, and usage history while preserving nonpersonal source definitions.
- [x] UI has visible keyboard focus, responsive forms/results, understandable empty/error states, and reduced-motion rules without third-party fonts or analytics. Keyboard focus and 320/640/651px layouts were manually inspected; actual 200% browser zoom and full screen-reader review remain unverified.
- [x] `.env` remains ignored; `.env.example` contains a blank `TYPESAFE_API_KEY=` placeholder; no key or CV is committed.
- [x] The offline validation suite passed with synthetic documents, fixtures, and a mocked Jev service. No live Jev/source call occurred during tests.

**Validation:** Run project tests, lints/type checks, and build/startup checks only after full workflow wiring; use fixtures/mocks and inspect the rendered UI. Manual live Jev/source checks are explicitly deferred to M2.

**Documentation updates:** README quick start/key setup, `.env.example`, architecture, source review, ADRs, readiness, and this plan.

**Applicable specialized skills:** `implementation-plan`, `milestone-delivery`, `ponytail-balanced`, `ui-ux-research`, `frontend-design`; Context7 for current library/API references.

**Expected Git checkpoint:** per the owner's explicit instruction, commit and push this validated M1 directly to `main`; do not create a branch. Honor required remote checks/protection and stop if GitHub rejects the push.

### M2 — Synthetic live Jev acceptance

**Goal:** With the owner-provided API key, prove the integration and budget guard on synthetic CV/listing data before any real CV is sent.

**Subtasks:**

- [ ] Review TypeSafe account terms, DPA/privacy, processing location/retention, and credit/refill settings before sending real CV-derived data; synthetic data may be used for technical acceptance.
- [x] The owner-configured key is present in the ignored `.env` and is untracked.
- [ ] After M1 offline checks pass, make one synthetic matching request and record usage and score output.
- [ ] Record actual token usage, cost ledger settlement, score response version/confidence, error handling, and one monthly-cap stop demonstration.
- [ ] Only after terms and local deletion/key controls are accepted should the owner decide whether to use their real CV.

**Affected areas:** local `.env` (never commit), live Jev client, readiness evidence, and operating instructions.

**Dependencies:** M1 complete; owner-supplied API key; review of provider terms and account billing settings.

**Acceptance criteria:**

- [ ] Synthetic request returns structured Jev scores and reports the answering version and billed input tokens.
- [ ] Missing/invalid key, 429/529, timeout, response-shape error, and cap exhaustion produce safe, visible unscored results without fallback model calls.
- [ ] No personal CV is sent in this milestone.

**Validation:** One explicitly authorized synthetic live request, plus local ledger verification; no real CV test.

**Documentation updates:** Record current live API/model evidence, measured costs, and terms gate state in the plan and readiness document.

**Expected Git checkpoint:** no API key, local database, or personal data enters Git. Push M1 first; deliver M2 evidence on `main` as a separate checkpoint. Do not create a branch.

## Final integration validation

After M1 wiring, validate the local end-to-end flow with synthetic files and source/API fixtures, a mocked TypeSafe response, no external network in automated tests, localhost-only listening, and deletion of the isolated temporary data directory. Inspect UI keyboard flow, responsive layout, errors and empty states, source attribution, location evidence, stale/unscored labels, cost reservation, and the Git diff. After M2, validate live Jev only with synthetic data and the owner's configured key. Real-CV use remains a distinct owner choice after TypeSafe terms are reviewed.

## Rollback / recovery

Keep local databases and uploads under ignored `.data/`; test data is temporary. Stop an individual source by setting its state to `Review` or `Blocked`. Stop all paid calls by removing the key or setting the local budget to zero. If a validated main checkpoint needs rollback, use a new corrective commit; never force-push or bypass failed remote checks.

## Progress

- [x] Confirmed `main` at `617f5c8`; after the owner clarified delivery, returned to `main` and will keep all milestone checkpoints there.
- [x] Read current project definition, architecture, source policy, and delivery/UX skills.
- [x] Retrieved current primary documentation for FastAPI, Scrapling, TypeSafe Jev/SDK, `pypdf`, and `python-docx`.
- [x] Record stack, privacy, ranking, UI, and source decisions and update source-of-truth docs.
- [x] Wire M1 application paths, including local profile/CV review, four default feeds, reviewed ATS/career sources, deterministic filters, Jev controls, results, saved/hidden views, and local deletion.
- [x] Run M1 validation after wiring is complete: 36 offline tests, Ruff, byte-compilation, localhost health/startup, no-key flow, and manual keyboard/responsive review passed.
- [ ] Commit and push the validated M1 milestone to `main`; verify the resulting remote SHA before starting M2.

## Implementation discoveries / decisions

- TypeSafe's current official model page identifies Jev 1.13.0 (`jev-1.13.0`), $42 per billion input tokens, free output, a 64k total request context, 32k state-plus-longest-question, and dynamic rate limits. The API returns input token usage. Pin the model and reserve 80,000 tokens for app-side cost accounting before each request (the reserve is not the request size); disable SDK retries to prevent automatic repeat charges.
- TypeSafe's official legal index says the DPA, Master Customer Agreement, and Privacy Policy govern processing and that zero-data-retention is offered to enterprise customers. A key alone does not clear the existing real-CV privacy gate.
- Scrapling Spider retries blocked requests by default. The implementation must set `max_blocked_retries=0`, `robots_txt_obey=True`, four concurrent requests overall, one per domain, and a two-second base delay.
- Jobicy's free public endpoint permits job-discovery products, requires attribution/canonical listing URLs, allows at most hourly polling, and has an optional direct ATS URL path that costs $0.01 per job; never call that paid path.
- Remote OK, Remote First Jobs, and Startup Jobs document free feeds and attribution/link requirements. Startup Jobs terms allow noncommercial reuse; the personal local app uses only its RSS feed and keeps the source link.
- TypeSafe input question content can be structured; the client can set `RetryPolicy(max_retries=0)`. Rubric `fit-v1.1.0` uses four `Choice` questions per listing with levels 0–4 and `unknown`. The app sends reviewed qualification fields and at most five jobs per request; no name/email/phone/raw CV.
- The selected Conda `gen` runtime is Python 3.10.21; launch with `python -m clue_ai` without requiring Node or `uv`.

## Completion evidence

- Main diff and final commit/push SHA.
- Passing local offline test/lint/startup output after all wiring is complete.
- Mocked integration evidence for feeds, ATS/page policy, Jev typed responses, monthly reservations, local persistence and deletion.
- Manual notes for visible focus, Italy default, reduced-motion rule, and no page overflow at 320/640/651px. Actual 200% browser zoom and full screen-reader review remain open.
- Updated README, source-of-truth docs, and this plan's progress/acceptance evidence.
- GitHub `main` push/check evidence before beginning M2.
