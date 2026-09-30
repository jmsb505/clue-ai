# Roadmap

**Status:** M1 IMPLEMENTED AND LOCALLY VALIDATED — M2 synthetic Jev acceptance is next
**Updated:** 2026-09-30

## Definition gate

The project definition passes for a single-user local feasibility build. Before real CV use, verify TypeSafe's applicable data/billing terms, local file and backup controls, and the approved $0 source set. The owner-set spend cap is $5/month for TypeSafe Jev and $0 for every other element. There is no public deployment or scale target.

## 1. Select a free source set for remote work from Italy

Use [PLAN-001](plans/PLAN-001-free-local-source-discovery.md) to inventory sources for fully remote work from Milan/Italy, including Europe/worldwide roles only when their eligibility statement includes Italy. Role queries come from the user's CV or search input. Record each source as `Approved`, `Review`, or `Blocked`; prioritize free APIs/feeds with explicit job-search use, then ordinary public employer pages.

**Acceptance:** Source list identifies geography, official endpoint, cost, usage rights, attribution, allowed cache/retention, refresh/rate limits, and original links. Coverage is reported honestly.

## 2. Validate a controlled company-site crawl

On approved sources only, compare documented API/feed retrieval with sitemaps, `JobPosting` JSON-LD, and limited HTML parsing. Implement Scrapling as the replaceable crawl adapter with robots enabled, up to four requests overall and one per domain, a two-second base delay, no stealth/bypass, and no dynamic browser unless permitted and necessary.

**Acceptance:** Listing provenance, last-check age, delisting/expiry, duplicates, source-link validity, parse success, blocks, and compute cost are measured. All non-TypeSafe costs remain $0.

## 3. Validate Jev ranking and free-tier operation

Use synthetic CV/listing pairs. Compare Jev's bounded criteria and user-weighted rank to personal judgments and a keyword baseline. Verify the $5/month all-in hard stop and disable automatic paid-credit refills. Check local save, delete, and backup behavior with synthetic data.

**Acceptance:** A written evaluation supports score labels and confidence display; hard constraints behave deterministically; all displayed jobs have source evidence; low-confidence/unvalidated-language results stay unscored; all non-TypeSafe recurring costs stay $0.

## 4. First local personal-use increment

Proceed after TypeSafe and source conditions in [the definition gate](readiness/definition-gate.md) are checked. Build local profile persistence, PDF/DOCX review, approved $0 source connectors, a local listing index, Jev scoring, accessible results, saved/hidden jobs, local deletion, and direct links. Keep applications external to the app.

**Acceptance:** Personal-use source terms, TypeSafe terms and cap, local storage/key handling, score evaluation, accessibility, deletion, and freshness checks pass. Record evidence; no hosted account or service is required.

## Current implementation state

PLAN-002's M1 implementation is locally validated: the localhost FastAPI/Jinja app, local profile and CV review, SQLite repository, four free feed connectors, approved-only ATS and Scrapling paths, deterministic filters, Jev adapter and reserve, and search/source/settings views. The 36-test offline suite, Ruff, byte-compilation, no-key startup, and keyboard/responsive review passed. One synthetic live Jev acceptance request remains for M2; no real CV is in scope.

## Delivery workflow

Use the `implementation-plan` and `milestone-delivery` workflows for each code milestone. Per the owner's explicit instruction, commit and push each validated milestone directly to `main`; do not create branches. Honor required checks and branch protection, and never bypass a rejection. Pair `ui-ux-research` with a frontend design skill for substantial interface work. Continue using Context7 for current SDK/API documentation. Revisit release-readiness only if public distribution enters scope.
