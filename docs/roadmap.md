# Roadmap

**Status:** PLAN-001 M1/M2 and M3a/M3b plus M3c owner-waiver record are pushed to `main`; personal relevance calibration remains. PLAN-002 M1/M2 and accessibility/privacy fixes are pushed. PLAN-003 M1 manual X leads is pushed. PLAN-004 M1 CV-first search is pushed to `main` at `ea2b73ab53580acee1558b56c2832d50cd4b4e8f`. PLAN-005 M1 local-origin form fix and Fetch Metadata follow-up are pushed to `main` at `b3b1bc56843866d0cffd8dc834fd93430956b217`. PLAN-007 M1 search history is in progress. PLAN-008 M1 crawling implementation is complete and statically validated; live coverage remains unmeasured.
**Updated:** 2026-10-02

## Definition gate

The project definition passes for a single-user local feasibility build. The owner waived TypeSafe account/terms checks and local device-encryption confirmation; account facts remain unverified, not proven safe or capped. The app reserves at most $4 per rolling 30 days for Jev toward the $5 owner ceiling and spends $0 on every other element. Source-specific terms still gate optional employer/ATS connectors. There is no public deployment or scale target.

## 1. Select a free source set for remote work from Italy

Use [PLAN-001](plans/PLAN-001-free-local-source-discovery.md) to inventory sources for fully remote work from Milan/Italy, including Europe/worldwide roles only when their eligibility statement includes Italy. Role queries come from the user's CV or search input. Record each source as `Approved`, `Review`, or `Blocked`; prioritize free APIs/feeds with explicit job-search use, then ordinary public employer pages.

**Acceptance:** Source list identifies geography, official endpoint, cost, usage rights, attribution, allowed cache/retention, refresh/rate limits, and original links. Coverage is reported honestly.

## 2. Validate a controlled company-site crawl

Use Scrapling as the replaceable crawl adapter with `robots.txt` `Disallow` ignored, eight global requests, two per domain, a one-second base delay, bounded public-page traversal, and dynamic rendering for discovered public career shells. Refresh fast feeds hourly, company pages every six hours, and publisher-daily APIs daily. A failed request receives a five-minute retry window instead of the normal success interval.

**Acceptance:** Listing provenance, last-check age, delisting/expiry, duplicates, source-link validity, parse success, blocks, and compute cost are measured. All non-TypeSafe costs remain $0.

## 3. Validate Jev ranking and free-tier operation

Use synthetic CV/listing pairs. Compare Jev's bounded criteria and user-weighted rank to owner judgments and a keyword baseline. The app's $4 request reserve is tested; provider-side refills and account-wide charges are unverified under the owner's waiver. Check local save, delete, and backup behavior with synthetic data. PLAN-001 M3a completed a five-item synthetic benchmark; M3b validated manual backup, restore, and deletion; M3c records the owner waiver and leaves personal relevance calibration open.

**Acceptance:** A written evaluation supports score labels and confidence display; hard constraints behave deterministically; all displayed jobs have source evidence; low-confidence/unvalidated-language results stay unscored; all non-TypeSafe recurring costs stay $0.

## 4. First local personal-use increment

Proceed for the single-user local scope with the app-side Jev reserve, in-app disclosure/opt-in, and approved $0 source connectors. The owner waived TypeSafe account checks and device-encryption confirmation; they remain unverified. Build local profile persistence, PDF/DOCX review, a local listing index, Jev scoring, accessible results, saved/hidden jobs, local deletion, and direct links. Keep applications external to the app.

**Acceptance:** Personal-use terms are reviewed per enabled source; local storage/key handling, app-side score accounting, scoring controls, accessibility, deletion, and freshness checks pass. The owner's TypeSafe account and encryption waivers are recorded as unverified scope decisions. No hosted account or service is required.

## Current implementation state

PLAN-002 M1 and M2 are pushed to `main`; M2 used one synthetic Jev request (1,574 input tokens; `$0.00006611` local ledger estimate). Accessibility/privacy fix `063ec584e5eae70e411aa255a8dd699097b76663` is on `main`; the full 65-test suite, Ruff, byte-compilation, and diff checks passed. PLAN-001 M1/M2, M3a/M3b, and M3c owner-waiver decisions are recorded on `main`; M3b `9399ad81e0cd34ed244045d4ab52e70d0e4a7245` contains backup/restore guidance and synthetic validation. M3a's five-item synthetic benchmark used one Jev request; Jev and the keyword baseline both achieved `nDCG@5 = 1.0` against assistant-authored labels, which is integration evidence rather than personal calibration. No real CV or live listing was sent to Jev. Personal relevance judgments, optional source-specific approvals, and spoken screen-reader review remain open. TypeSafe account charges and device encryption were waived as checks and remain unverified.

PLAN-003 M1 implemented a separate manual X search handoff and local lead intake. It does not use Scrapling on X, the X API, or automatic URL fetching. See [PLAN-003](plans/PLAN-003-x-manual-leads.md) and [ADR 0007](decisions/0007-x-manual-lead-discovery.md). PLAN-004 M1 is implemented and pushed to `main`: upload a CV, parse it locally, start a search, then automatically run Jev checks when enabled. See [PLAN-004](plans/PLAN-004-cv-first-automated-search.md).

## 7. Have Jev assess every collected listing

Implement [PLAN-009](plans/PLAN-009-full-candidate-jev-assessment.md) and [ADR 0010](decisions/0010-full-candidate-jev-assessment.md). Snapshot the full active, non-hidden index, pass all profile-safe search criteria to Jev, retain filter conflicts and unknowns in the per-run results, and show filter-match, review, conflict, and unassessed groups. Preserve the $4 rolling app reserve and avoid fuzzy fingerprint-only merges.

**Acceptance:** Jev evaluates every retained candidate against candidate fit and current user criteria; no role/location/date hard prefilter removes listings; all candidates remain paginated and reviewable; exhausted budget or provider errors leave clear unassessed states; strong identity dedupe and local static validation pass.

PLAN-009 M1 implementation is complete and statically validated. Live CV/TypeSafe validation remains an owner-run action.

## 8. Jev-coordinated application preparation

[PLAN-019](plans/PLAN-019-application-preparation-framework.md) and accepted [ADR 0023](decisions/0023-application-preparation-and-action-boundaries.md) record the implemented local flow and remaining enablement work. Jev remains the sole matching validator. After a single-listing **Prepare application** click, the local Clue harness passes its read-only, versioned result to GPT-6 Luna (`gpt-6-luna`, `reasoning.effort=max`) through the OpenAI Responses API. A separate Researcher directs bounded public contact research through the existing Scrapling crawler; the Diagnoser, Recruiter, and Rewriter generate evidence-grounded CV, cover-letter, answer, and outreach drafts. Hiring Manager practice is an additional owner-triggered action. The owner may select a base CV and preserve or improve its structure. Clue validates and renders versioned drafts locally; the owner reviews the complete packet once before any external action.

The implemented flow includes reviewed evidence, a durable queue, Jev-to-GPT snapshot handoff, structured stage outputs/tool allowlists, local rendering, separate API usage accounting and consent, bounded public contact research, suppression, owner feedback, and an exact-approval Gmail draft adapter. The API key remains empty in `.env.example`; API calls also require owner-configured monthly and per-opportunity caps, a current rate card, and separate data-sharing consent. The real provider pilot, Gmail authorization, current price/account verification, follow-up reminders, external tracker sync, and cohort analytics remain pending or deferred. Applications and sent outreach remain manual. The GPT agent has no Gmail or send tool. Clue needs its own Gmail authorization; Gmail's draft-creation scope also permits sending, so this permission trade-off must be accepted or use copy/paste instead. Jev's existing $4 rolling 30-day app reserve toward the $5 owner ceiling remains unchanged.

Search discovery, deduplication, deterministic hard filters, and Jev matching remain automatic. Mined or selected listings do not start research or generation. Each eligible listing waits for the owner to click **Prepare application** on that specific card; that click triggers the full bounded research and document packet for that job and reserves its OpenAI budget. No bulk or scheduled start is allowed. Mock interview practice is a separate optional trigger for that listing. M2's generated flow uses a separate GPT-6 Luna Researcher role (the only stage with bounded public-crawl tools), followed by Diagnoser, Recruiter, Rewriter, and optional Hiring Manager practice calls at `reasoning.effort=max`. The Diagnoser reports visible extraction/layout risks, not exact ATS outcomes; the Recruiter maps job criteria to evidence while Jev remains the only fit validator; the Rewriter applies the Google XYZ pattern only to verified facts and metrics; interview ratings remain practice feedback. See PLAN-019 and ADR 0023 for stage inputs, output contracts, and acceptance criteria.

## 9. Per-application workspace and manual email handoff

[PLAN-020](plans/PLAN-020-application-workspaces.md) and [ADR 0024](decisions/0024-application-workspaces-and-local-email-handoff.md) implement an Applications index and a dossier for every individually prepared listing. The dossier groups current and older generated files, contact research, owner-recorded stages, reminders, and saved submission receipts while keeping existing preparation URLs available. The local email preview shows the sourced recipient, subject, and message; copy controls and a ZIP of selected files support manual composition without Google OAuth. The existing Gmail draft adapter remains optional; Clue never sends the email or submits the application. Focused synthetic validation for M1 and M2 passes; the implementation record lists the exact checks.

## Delivery workflow

Use the `implementation-plan` and `milestone-delivery` workflows for each code milestone. Per the owner's explicit instruction, commit and push each validated milestone directly to `main`; do not create branches. Honor required checks and branch protection, and never bypass a rejection. Pair `ui-ux-research` with a frontend design skill for substantial interface work. Continue using Context7 for current SDK/API documentation. Revisit release-readiness only if public distribution enters scope. PLAN-020's focused synthetic tests and static checks pass. A full-suite attempt cannot collect `tests/test_company_sources.py` in the current Python environment because `scrapling` is not installed; a prior PLAN-019 test run also recorded an unrelated Jev scoring expectation failure. Do not report repository-wide validation as passing.
