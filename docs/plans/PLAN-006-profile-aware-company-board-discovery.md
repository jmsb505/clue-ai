# PLAN-006 — Profile-aware company board discovery and Scrapling coverage

**Status:** M1 pushed; M2 directory and tracking are implemented; M3–M4 not started.
**Created:** 2026-10-01  
**Last updated:** 2026-10-01

## Objective

Make Clue's CV-first search discover AI/ML, applied AI, data, ML-platform, and AI-product vacancies from a broad directory of official company boards, with Scrapling driving company/career-site discovery and public ATS connectors supplying complete vacancy evidence. Keep the app local, single-user, Italy/Milan focused, and free except for the existing Jev allowance.

## Motivation

The user wants a broad search that finds real roles at companies in their field, not a handful of remote-job aggregator results. The user has a saved CV/profile and wants upload → profile parsing → broad search → automatic Jev fit validation. The app currently has five broad feed/API sources plus a Scrapling adapter, but the adapter is not the broad discovery workflow the product requires.

## Current state

- `run_search()` checks only registry sources that are enabled, approved, and due.
- Current registered source set is five remote-job feed/API connectors and a manual-only X lead source.
- `crawl_career_page()` starts at one already-known URL, allows one hostname, parses JobPosting JSON-LD and a bounded HTML fallback, follows at most 25 same-host links with a fixed URL pattern, and has no sitemap, source-directory discovery, ATS-host traversal, or multi-company batch discovery.
- Separate official ATS hosts are only fetched if the user has already identified and registered the ATS board independently. User-facing source setup asks for company-specific ATS tokens and requires source review confirmations.
- Thus Scrapling is installed and used, but company discovery and company-board coverage are absent.
- The user saved roles/skills match AI/ML engineering, applied AI/LLM work, data analysis, data engineering, ML platform, and technical product delivery. This scope is derived from profile role/skill fields only; do not read the source CV for this research.

## Desired state

1. A Companies page shows a broad, profile-aware directory of official company boards and explains which listings it searched.
2. Clue resolves official careers links and hosted ATS boards automatically; the owner does not need to search for or enter board tokens.
3. CV upload starts broad search over existing free feeds and profile-relevant official boards.
4. Scrapling handles batched company/career discovery with scoped sitemaps, link rules, adaptive selectors where useful, optional ordinary browser rendering for genuinely JS-only pages, and incremental result streaming.
5. Public ATS connectors (Greenhouse, Lever, Ashby public job-board feed, SmartRecruiters public GET, Personio public XML where available) provide full listing descriptions and direct canonical job links.
6. The app checks exact job-level country eligibility and freshness before Jev; remote work in the US, UK-only, or another non-Italy region is not treated as Italy eligible.
7. Search progress and source coverage make clear how many boards were resolved, checked, skipped, and returned usable jobs.

## Scope

- Company seed research and a first broad catalog for AI, ML, applied AI, data, and engineering roles.
- Profile-aware company catalog UI and local selection/tracking of official boards.
- Scrapling company/career link discovery, sitemap and link crawling, HTML/JobPosting parsing, incremental refresh/streaming, progress reporting, and domain-level bounded behavior.
- Free official public ATS/feeds with provider-specific parsing and official source URLs.
- Italy/Europe remote eligibility evidence, current/stale labels, and source coverage metrics.
- Documentation and records that explain source types, limitations, and the exact meaning of the JEV score.

## Out of scope

- Automated applications, form submissions, or employer contact.
- X scraping, API access, URL resolving, or automated preview; X remains a manual lead route.
- Paid commercial job databases, paid crawl proxies, hosted scraping, paid browser services, or additional recurring spend beyond Jev.
- Authenticated ATS API use, hidden endpoints, search-result-page scraping, stealth, impersonation, proxy rotation, CAPTCHA solving, or retrying around a block.
- A claim of complete coverage of the internet, every employer, or every vacancy.
- Hosted user accounts, a cloud CV, public republishing, or multi-user operation.

## Source-of-truth impact

- Add [profile-aware company-board discovery research](../research/profile-aware-company-board-discovery.md).
- Update product definition and architecture to put the company catalog and broad Scrapling discovery at the center of sourcing.
- Add an ADR for company discovery, board resolution, and crawler boundaries.
- Update this plan at each milestone with source/catalog decisions, validation evidence, and direct-to-main commit SHA.
- No CHANGELOG exists in the repository; do not introduce one solely for planning.

## Existing decisions and constraints

- The owner explicitly authorized progress directly on `main` and wants each validated milestone committed/pushed separately; do not create a feature branch.
- Use the existing Conda `gen` environment. Install a needed package there only if current dependencies lack the capability.
- Local single-user application; no encryption verification prerequisite and no TypeSafe account verification prerequisite. The user also waived a 200% zoom review.
- Geography is a user input. Current priority is remote from Milan/Italy and roles explicitly available to a worker living in Italy.
- No automatic apply. Existing JEV disclosure, consent, token budget, and per-month spending cap remain in effect.
- Existing public-feed attribution and refresh/retention details continue to apply to the five current feed sources.
- Scrapling 0.4.15 is already pinned. Use its ordinary public crawling capabilities; never use stealth, proxy rotation, impersonation, or anti-bot bypass.
- No server should be left running when work completes.

## Supporting skills / tools

- `implementation-plan` and `milestone-delivery` for staged scope and direct-to-main validation.
- `ui-ux-research` for the company-directory information architecture and search coverage states.
- `ponytail-balanced` for implementing the smallest design that integrates with the current FastAPI/Jinja/SQLite app.
- Scrapling official documentation via Context7; Scrapling docs/GitHub for current Spider, sitemap, LinkExtractor, session, selector, and fetcher APIs.
- Official Greenhouse, Lever, Ashby, SmartRecruiters, Personio, and Google JobPosting documentation.
- Conda `gen`, existing Ruff/Pytest checks, `git diff --check`, and the local run/stop command. The app server must be shut down at the end.

## Dependencies

- Existing profile fields, registry, normalized job model, source-check history, and local index.
- Current Scrapling dependency and Conda environment.
- Public official company career pages/ATS boards and current machine-readable documentation.
- No paid feeds, new remote services, or account credentials beyond the existing Jev key.

## Risks and unknowns

- Company ecosystem lists are incomplete, may be updated yearly or through non-machine-readable formats, and do not indicate whether an employer is hiring.
- Thousands of AI adopters exist in Italy; a seed list must expand over time and represent both AI-native companies and employers with AI teams.
- Many official career pages link to a different ATS hostname or render via JavaScript; current crawler will miss these without discovery and multi-host handling.
- Public ATS routes vary in completeness, schema, and authentication; use only documented public posting paths, not customer/admin APIs.
- More boards improve recall but raise startup-search latency and parser maintenance. Batch requests across separate hosts, cache source checks, show progress, and refresh incrementally.
- “Remote” is not a location. Country eligibility may be absent or described in free text; uncertain cases must remain uncertain pending owner review.
- Current source terms and feed conditions can change. Source-level failures should not prevent checking other boards.

## Milestones

### M1 — Broad source research and field target definition

**Goal:** Replace the vague sourcing definition with a researched, profile-aware company/board map and a concrete Scrapling design.

**Subtasks:**

- [x] Trace the current registry/search/crawler gap.
- [x] Research European AI-company discovery lists and Italian AI/data employment evidence.
- [x] Verify official careers-board and ATS examples, including current Italy/Europe location evidence.
- [x] Compare official public ATS and structured-data paths.
- [x] Define the Company catalog, Scrapling crawler, location eligibility, and coverage metrics.

**Affected areas:**

- `docs/research/profile-aware-company-board-discovery.md`
- `docs/product-definition.md`
- `docs/architecture/overview.md`
- `docs/decisions/0008-profile-aware-company-board-discovery.md`

**Dependencies:** None.

**Acceptance criteria:**

- [x] Research includes more than remote aggregators: distinct company-discovery sources, company board examples, ATS providers, and employer career page paths.
- [x] Research connects the user's target role families and Italy/Milan constraint to the search strategy.
- [x] Current Scrapling limitation is stated accurately.
- [x] Product source-of-truth and an ADR document the chosen direction and current boundaries.
- [x] No CV contents were opened or transmitted for the research.

**Validation:**

- [x] Current crawler/search source and existing architecture/source review inspected.
- [x] Current primary source documentation and official company board pages verified via web research.
- [x] `git diff --check` and final documentation/link review.

**Documentation updates:** Research report, source-of-truth product and architecture, ADR, and plan.

**Applicable specialized skills:** `implementation-plan`, `ui-ux-research`.

**Expected Git checkpoint:** Commit the completed definition/research milestone directly on `main`, then push and verify the remote main SHA.

### M2 — Profile-aware company board catalog

**Goal:** Put a useful company/board directory in the app so the user can see and control where broad searches will look.

**Subtasks:**

- [x] Add a curated local catalog with discovery provenance, official company/careers URLs, role-family tags, and detected ATS details only when directly verified.
- [x] Add a Companies page with local profile-ranked filters, role-family categories, company/careers links, board-discovery state, last check, and listing count.
- [x] Allow the owner to track/untrack candidates without typing an ATS identifier; persist choices locally. M3 wires those choices into CV-first searches.
- [x] Display that catalog entries are candidate employers, not a claim of a live vacancy or Italy eligibility.
- [x] Keep the catalog source records and tracking state local and reset tracking through user-controlled deletion.

**Affected areas:**

- `clue_ai/company_catalog.py` or tracked catalog data file
- `clue_ai/web.py`, templates, CSS, and repository functions
- source-of-truth product and architecture docs
- unit/integration tests for profile filters and tracking actions

**Dependencies:** M1.

**Acceptance criteria:**

- [x] The app displays a broad 80+ seed list spanning Italian AI/data employers, European AI startups, global AI/data platforms, and large technology employers.
- [x] The active profile target roles/skills filter and sort the local catalog without sending the CV to third parties.
- [x] Every direct careers/board link has traceable company provenance; unverified ATS slugs are never guessed.
- [x] The owner can open the official company/career/known-board link, track or untrack the lead, and see its current discovery state.
- [ ] Keyboard navigation, semantic headings/forms, focus visibility, and narrow layouts remain usable. The owner waived 200% zoom review.
- [ ] Existing CV-first and search preference workflows remain available.

**Validation:**

- [x] Add focused catalog and route tests, including tracking reset on local-data deletion.
- [x] Run the full test suite, Ruff, Python compilation, and `git diff --check` in Conda `gen`.
- [x] Check the rendered page with FastAPI TestClient and inspect narrow-layout rules; no server was left running.

**Documentation updates:** Catalog sourcing, user actions, and local deletion behavior.

**Applicable specialized skills:** `milestone-delivery`, `ui-ux-research`, `ponytail-balanced`.

**Expected Git checkpoint:** Validated M2 commit pushed directly to `main` before crawler work begins.

### M3 — Multi-company Scrapling discovery and crawl

**Goal:** Resolve employer careers/ATS pages and collect current listings from many profile-matched companies in a single search run.

**Subtasks:**

- [ ] Replace the one-start-URL crawl path with an async batch Spider over due official company sources.
- [ ] Discover career and ATS links from official employer sites; retain path provenance and only permit ATS hosts linked from the official source.
- [ ] Use `SitemapSpider`/sitemap discovery, `LinkExtractor` rules, JSON-LD, public feeds, and bounded HTML fallbacks.
- [ ] Add or extend public connector types for Ashby board feeds and Personio XML if no existing parser covers them; fix and document SmartRecruiters' no-auth public path; preserve Greenhouse and regional Lever support.
- [ ] Use selector adaptation for repeat site templates only when needed; use ordinary dynamic rendering only where static HTML/feed routes cannot provide listings.
- [ ] Stream normalized items into existing dedupe/upsert, cache conditional responses where supported, and report per-domain crawl metrics.
- [ ] Keep a user-facing source status for available, skipped, stale, partial, blocked, and error cases; continue the run when one source fails.

**Affected areas:**

- `clue_ai/sources.py` and provider adapters
- `clue_ai/services.py` search orchestration/progress
- source/board persistence and tests
- source help, architecture, product definition, and crawler research

**Dependencies:** M2, Scrapling API guidance confirmed in Context7, official current ATS docs.

**Acceptance criteria:**

- [ ] One search refreshes a profile-matched set of company boards across separate domains without one Spider per company run serially.
- [ ] At least 20 initial curated boards resolve to the official board or a clear unavailable state; target at least 50 in the broader catalog.
- [ ] A deterministic synthetic profile/corpus smoke scenario parses listings from a public ATS adapter and at least one plain company career page, including detail descriptions and canonical URL.
- [ ] Page/host caps, request budgets, robots handling, delay, and no-retry-on-block behavior are covered.
- [ ] A denial/challenge/rate limit stops only that source; there is no stealth or retry workaround.
- [ ] Streaming preserves parsed records when another board fails; repeated runs deduplicate listings.
- [ ] User sees source coverage and Italy eligibility evidence before Jev scoring.

**Validation:**

- [ ] Run tests for each connector/crawl behavior plus full existing tests, Ruff, compilation, `git diff --check`.
- [ ] Run bounded live source smoke checks on selected public career boards with synthetic profile data only; no CV or Jev.
- [ ] Verify per-source requests, response bytes, result counts, runtime, duplicates, and no live server remains running.

**Documentation updates:** Connector inventory, exact crawl bounds, ATS auth/public-path notes, troubleshooting, and coverage limits.

**Applicable specialized skills:** `milestone-delivery`, `ponytail-balanced`, Scrapling docs via Context7.

**Expected Git checkpoint:** Validated M3 commit pushed to `main`; don't combine with later relevance calibration.

### M4 — Italy eligibility, Jev ranking, and coverage calibration

**Goal:** Ensure broad collection results in useful, accurate ranked jobs that can actually be worked from Italy.

**Subtasks:**

- [ ] Treat Italy/Europe/worldwide eligibility, workplace type, employer location, and remote region as distinct fields.
- [ ] Keep roles that are skill-fit but geographically unconfirmed in a separate verify state; exclude explicitly ineligible locations under current hard filters.
- [ ] Run Jev on eligible complete listings using existing consent, language, and budget controls.
- [ ] Capture local keep/hide feedback and build a field-specific relevance evaluation set from synthetic/owner-approved examples.
- [ ] Show evidence, gaps, confidence, source and last-check state in result cards.

**Affected areas:**

- location normalizers, filters, Jev evidence/ranking, result UI, local feedback persistence
- location/remote research, product definition, architecture, and tests

**Dependencies:** M3.

**Acceptance criteria:**

- [ ] A North-America-only remote listing is not counted as work-from-Italy eligible.
- [ ] A clearly Italy/Europe-eligible AI/ML listing survives hard filters and is scored with exact posting evidence.
- [ ] Unknown location status is visible and not silently upgraded to eligible.
- [ ] JEV remains a fit-evidence model, not a hiring probability; user can inspect the original listing.
- [ ] Local evaluation demonstrates target-relevant results and separates precision, recall, and uncertain location cases.

**Validation:**

- [ ] Run focused geography/score tests and full suite plus Ruff/compile/diff checks.
- [ ] Use synthetic examples or explicit owner approval before any real CV-derived profile fields are sent to Jev.
- [ ] Confirm the configured JEV monthly limit, usage display, and no server remains running.

**Documentation updates:** Evaluation evidence, personal relevance limits, and current source coverage.

**Applicable specialized skills:** `milestone-delivery`, `ponytail-balanced`.

**Expected Git checkpoint:** Validated M4 commit pushed directly to `main`.

## Final integration validation

- Validate CV upload → local extraction/profile → broad source discovery → per-board crawl status → location filtering → automatic Jev eligibility/scoring → ranked results → open original posting.
- Use Conda `gen`. Use synthetic CV/profile data for automated/live connector checks; never send a real CV unless the owner explicitly asks to validate that particular flow.
- Run test suite, Ruff, compilation, `git diff --check`, source coverage smoke, location evidence check, and local port 8000 clean shutdown.
- Verify each validated milestone is committed and pushed directly to `main`; verify `git ls-remote origin refs/heads/main` matches local HEAD.

## Rollback / recovery

- Each milestone is a separate direct-to-main commit. Revert a faulty milestone by a new revert commit; do not force-push.
- Catalog changes are tracked text data and can be corrected without DB migration.
- Keep database changes additive and idempotent. Provide reversible migration or preserve existing source/job records before any schema alteration.
- Stop an individual source through the existing pause state; a blocked source never auto-re-enables.

## Progress

- 2026-10-01: Inspected the current search worker, source registry, Scrapling Spider, product definition, source research, and architecture. Confirmed that the present 25-link, single-host crawl is not broad company discovery.
- 2026-10-01: Researched Sifted AI 100, AIxIA's Italian ecosystem map, the Politecnico di Milano AI market report, official ATS documentation, and official company career pages with live Italy/Europe examples.
- 2026-10-01: M1 research and target definition recorded in the research report, product definition, architecture, and ADR, then pushed to `main` at `470ad084c2ddcd4d9ff17d4c92038a5dcd994d95`.
- 2026-10-01: M2 added an 80+ employer catalog, local profile-role sorting, group/name filters, tracking controls, verified board links, and deletion/reset behavior. Full Conda `gen` validation passed: 107 tests, Ruff, Python compilation, and whitespace check.

## Implementation discoveries / decisions

- The user needs a local company directory and automatic board resolution; requiring the owner to look up ATS slugs is the wrong interface.
- European AI startup directories and Italian AI ecosystem research should seed the directory; they are not vacancy feeds.
- The official employer/ATS source should supply listing data. Aggregator feeds remain supplements.
- Italian AI job demand exists across broader sectors, so the target seed set must include AI-native companies and Italian enterprises with AI/data hiring.
- Italy work eligibility is vacancy-specific. Remote, EMEA, and Europe labels require exact country evidence.
- M1 is pushed. M2 is implemented and validated in the working tree; push its checkpoint before beginning M3. M3 crawler integration and M4 eligibility calibration remain separate milestones.

## Completion evidence

M1 research sources and direct-board examples are linked throughout [the research report](../research/profile-aware-company-board-discovery.md). This M1 checkpoint contains no code change and makes no claim that the expanded crawler is already implemented.

M2 adds the local `Companies` page backed by the seeded catalog in `clue_ai/company_catalog.py` and the additive SQLite `companies` table. The directory shows 80+ employer leads across five groups. Search and role-family ordering use locally saved profile fields; company tracking persists locally and resets during user-controlled data deletion. Only directly observed official career/ATS links are prefilled; other board identifiers remain empty for M3 resolution. The full test suite passes in Conda `gen` (107 tests), Ruff passes, and Python compilation succeeds. M2 does not yet connect tracked companies to the live search worker; that is the M3 task.
