# ADR 0004: Single-user local personal app

**Status:** ACCEPTED  
**Date:** 2026-09-30

## Context

The owner clarified that this app is for personal use on their own machine and is not being scaled or offered to other people. The project had previously carried an account-backed profile choice, but a hosted account system is unnecessary for this scope. The first search focus is remote work that can be performed from Milan/Italy, while search geography remains changeable.

## Decision

- Build a single-user local app; no registration, cloud account, public deployment, multi-user support, or scale target is in the current scope.
- Store the owner's CV, reviewed profile, preferences, cached listings, and fit results on the local device. Provide one clear control to delete this data.
- Run CV parsing, source indexing, filtering, and result display locally. TypeSafe Jev is the only planned external processing service; send only the minimum candidate and listing data needed for a fit judgment.
- Keep the recurring budget at $0 for every component and source other than TypeSafe Jev, capped at $5/month.
- Use Milan/Italy and fully remote work as the initial validation profile. Include EU/EEA, Europe, or worldwide jobs only where the employer explicitly states that the location is eligible. Keep work authorization as a separate user input.
- Revisit this decision only if the owner decides to make the app available to other users.

## Consequences

- No hosted authentication, multi-tenant data isolation, cloud database, email service, or shared job index is needed.
- The app must protect local files and the Jev API key, and its deletion control must cover the CV, parsed profile, search settings, cached jobs, saved results, and local backups the app creates.
- Track source attribution, refresh limits, and local caching rules for each connector; use another source when its published rules do not fit the local app.
- The app can be designed around a single local job index and manual source links without promising broad or complete coverage.

## Evidence

- Owner clarification in project conversation, 2026-09-30: “this platform is for me, for my own personal use … just meant to be a local thing.”
- Product and architecture updates: [`product-definition.md`](../product-definition.md), [`overview.md`](../architecture/overview.md), and [`definition-gate.md`](../readiness/definition-gate.md).

## Affected source-of-truth documents

- `docs/product-definition.md`
- `docs/architecture/overview.md`
- `docs/research/source-discovery-and-crawl-review.md`
- `docs/plans/PLAN-001-free-local-source-discovery.md`
- `docs/readiness/definition-gate.md`
- `docs/roadmap.md`
