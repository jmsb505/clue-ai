# Roadmap

**Status:** PLAN-001 M1/M2 and M3a/M3b plus M3c owner-waiver record are pushed to `main`; personal relevance calibration and actual spoken screen-reader review remain. PLAN-002 M1/M2 and accessibility/privacy fixes are pushed.
**Updated:** 2026-09-30

## Definition gate

The project definition passes for a single-user local feasibility build. The owner waived TypeSafe account/terms checks and local device-encryption confirmation; account facts remain unverified, not proven safe or capped. The app reserves at most $4 per rolling 30 days for Jev toward the $5 owner ceiling and spends $0 on every other element. Source-specific terms still gate optional employer/ATS connectors. There is no public deployment or scale target.

## 1. Select a free source set for remote work from Italy

Use [PLAN-001](plans/PLAN-001-free-local-source-discovery.md) to inventory sources for fully remote work from Milan/Italy, including Europe/worldwide roles only when their eligibility statement includes Italy. Role queries come from the user's CV or search input. Record each source as `Approved`, `Review`, or `Blocked`; prioritize free APIs/feeds with explicit job-search use, then ordinary public employer pages.

**Acceptance:** Source list identifies geography, official endpoint, cost, usage rights, attribution, allowed cache/retention, refresh/rate limits, and original links. Coverage is reported honestly.

## 2. Validate a controlled company-site crawl

On approved sources only, compare documented API/feed retrieval with sitemaps, `JobPosting` JSON-LD, and limited HTML parsing. Implement Scrapling as the replaceable crawl adapter with robots enabled, up to four requests overall and one per domain, a two-second base delay, no stealth/bypass, and no dynamic browser unless permitted and necessary.

**Acceptance:** Listing provenance, last-check age, delisting/expiry, duplicates, source-link validity, parse success, blocks, and compute cost are measured. All non-TypeSafe costs remain $0.

## 3. Validate Jev ranking and free-tier operation

Use synthetic CV/listing pairs. Compare Jev's bounded criteria and user-weighted rank to owner judgments and a keyword baseline. The app's $4 request reserve is tested; provider-side refills and account-wide charges are unverified under the owner's waiver. Check local save, delete, and backup behavior with synthetic data. PLAN-001 M3a completed a five-item synthetic benchmark; M3b validated manual backup, restore, and deletion; M3c records the owner waiver and leaves personal relevance calibration open.

**Acceptance:** A written evaluation supports score labels and confidence display; hard constraints behave deterministically; all displayed jobs have source evidence; low-confidence/unvalidated-language results stay unscored; all non-TypeSafe recurring costs stay $0.

## 4. First local personal-use increment

Proceed for the single-user local scope with the app-side Jev reserve, in-app disclosure/opt-in, and approved $0 source connectors. The owner waived TypeSafe account checks and device-encryption confirmation; they remain unverified. Build local profile persistence, PDF/DOCX review, a local listing index, Jev scoring, accessible results, saved/hidden jobs, local deletion, and direct links. Keep applications external to the app.

**Acceptance:** Personal-use terms are reviewed per enabled source; local storage/key handling, app-side score accounting, scoring controls, accessibility, deletion, and freshness checks pass. The owner's TypeSafe account and encryption waivers are recorded as unverified scope decisions. No hosted account or service is required.

## Current implementation state

PLAN-002 M1 and M2 are pushed to `main`; M2 used one synthetic Jev request (1,574 input tokens; `$0.00006611` local ledger estimate). Accessibility/privacy fix `063ec584e5eae70e411aa255a8dd699097b76663` is on `main`; the full 65-test suite, Ruff, byte-compilation, and diff checks passed. PLAN-001 M1/M2, M3a/M3b, and M3c owner-waiver decisions are recorded on `main`; M3b `9399ad81e0cd34ed244045d4ab52e70d0e4a7245` contains backup/restore guidance and synthetic validation. M3a's five-item synthetic benchmark used one Jev request; Jev and the keyword baseline both achieved `nDCG@5 = 1.0` against assistant-authored labels, which is integration evidence rather than personal calibration. No real CV or live listing was sent to Jev. Personal relevance judgments, optional source-specific approvals, and spoken screen-reader review remain open. TypeSafe account charges and device encryption were waived as checks and remain unverified.

## Delivery workflow

Use the `implementation-plan` and `milestone-delivery` workflows for each code milestone. Per the owner's explicit instruction, commit and push each validated milestone directly to `main`; do not create branches. Honor required checks and branch protection, and never bypass a rejection. Pair `ui-ux-research` with a frontend design skill for substantial interface work. Continue using Context7 for current SDK/API documentation. Revisit release-readiness only if public distribution enters scope.
