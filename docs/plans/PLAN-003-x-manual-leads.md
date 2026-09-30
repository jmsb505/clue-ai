# PLAN-003: X.com manual job leads

**Status:** M1 pushed to `main` and remote-verified (`bdcf5c970b605cf90d9e9904002f6b56f39de608`)
**Created:** 2026-09-30
**Last updated:** 2026-10-01

## Objective

Add X.com as a no-cost, manual job-lead discovery path for this single-user local app. Let the owner search X in their own browser, inspect a post and its employer or ATS listing, enter the verified listing facts into Clue, and use the existing local filters and explicit Jev scoring action.

## Motivation

The owner finds job leads in X posts that link to vacancies. An automated X connector would conflict with the current $0 source budget and X's published warning against scripting its website. A manual handoff preserves the useful discovery path without adding API spend, Scrapling access to X, or unattended link navigation.

## Current state

Clue indexes listings from five enabled, no-key feeds/APIs and owner-approved public ATS/career sources. Its normal search filters the local index, and Jev scoring is a separate explicit action. There is no manual external-lead intake.

## Desired state

The app offers a role/location query builder that creates an explicit link to X search. The owner opens X, checks the post and original employer/ATS page, and pastes an X status permalink, the final HTTPS job page URL, and reviewed role details into Clue. Clue performs no X API request, X page scrape, URL resolution, redirect, preview, or automatic external navigation. The saved job uses the existing index, source trail, filters, result cards, and Jev flow. Clue labels it as a manually added lead and does not claim that it rechecked availability.

## Scope

- Add an X manual-lead page and navigation entry.
- Build an X search link from owner-entered role and work-location terms; require an explicit user click to open it.
- Accept only an X/Twitter status permalink plus a final public HTTPS job-page URL; reject malformed, credential-bearing, local/private/IP and known shortened destination URLs.
- Show the decoded hostname beside an external listing link. Never fetch, unfurl, resolve, or follow either URL in Clue.
- Let the owner paste reviewed job details and confirm they inspected the post and destination. Store only those fields and the two URLs locally; do not store X post text.
- Add the lead to the existing listing index as `X.com · manual lead`, where the existing filters and explicit Jev action can evaluate it.
- Treat listing content as untrusted data in Jev instructions; ignore instructions embedded inside candidate/listing fields.
- Keep X manual-only in the source registry; exclude it from scheduled refresh, source enablement, and source-coverage claims.
- Document this acquisition and link-safety decision.

## Out of scope

- X API integration, API keys, API reads, X scraping, authenticated-session automation, page inspection, scheduled search, or automated post collection.
- Automatically validating whether a vacancy is still open, verifying employer identity, following redirects, crawling the employer URL, or applying.
- Automatic Jev scoring during import or sending X post text to Jev.
- A public/multi-user deployment.

## Source-of-truth impact

- Update `docs/product-definition.md`, `docs/architecture/overview.md`, `docs/readiness/definition-gate.md`, and `docs/roadmap.md`.
- Add current X rules, price evidence, and the manual-only source path to `docs/research/source-discovery-and-crawl-review.md`.
- Record the product choice in ADR 0007 and this plan; update `docs/README.md` and `README.md`.

## Existing decisions and constraints

- Personal single-user local app; no account service or hosting.
- TypeSafe Jev is the only paid service, with the owner's $5/month ceiling and current app-side $4 cap.
- Every other service/source must remain $0.
- Scrapling is for approved public employer/ATS pages. X's own automation rules warn against scripting the X website; X API post reads are currently billed per returned post.
- The owner opens an original posting and decides what to do; Clue never applies.
- No extra TypeSafe account, encryption, or 200% zoom review is introduced by this feature.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, `ponytail-balanced`
- `ui-ux-research` with the existing frontend design system
- Context7 documentation for X API search/pricing was consulted for feasibility; official X and OWASP material was checked for policy and link-handling context.
- Conda `gen` for any local validation.

## Dependencies

- Existing FastAPI/Jinja/SQLite app and source registry.
- Existing `NormalizedJob` persistence, local filters, and opt-in/explicit Jev scoring flow.
- No added package, external account, API key, or network service.

## Risks and unknowns

- X search behavior, query syntax, rules, and prices can change; the owner searches directly in X and can edit the generated query there.
- A user-entered listing URL or copied description can still be misleading. URL validation and hostname display reduce common mistakes but do not certify a site or job.
- A manually added lead's availability is not rechecked by Clue. The UI must say so clearly and show the date it was added.
- External page content can include prompt-injection text; Jev instructions must explicitly treat all profile and listing fields as untrusted evidence, not instructions.

## Milestones

### M1 — Manual X search and local lead review

Goal: discover promising X posts through the owner's browser, add reviewed employer/ATS job links as local leads, and make them available to normal search and Jev review.

Subtasks:

- [x] Add a role/location search-link builder and manual X lead intake page.
- [x] Validate X status links and final HTTPS destination links without making network requests.
- [x] Store manual lead provenance separately from the employer listing URL and integrate with existing search results.
- [x] Keep X permanently out of fetch scheduling and automated source toggles.
- [x] Harden Jev question instructions against instructions embedded in user/listing text.
- [x] Add tests for safe URL handling, import persistence, non-fetch behavior, and Jev input boundaries.

Affected areas:

- `clue_ai/database.py`, `domain.py`, `repository.py`, `sources.py`, `jev.py`, `web.py`
- Jinja navigation, X lead page, results/source views, and project CSS
- `tests/test_sources.py`, `tests/test_storage.py`, `tests/test_jev.py`, `tests/test_web_flow.py`
- Project documentation and ADR 0007

Dependencies: None.

Acceptance criteria:

- [x] The search builder only exposes an explicit X.com search link; no request to X is made by the app.
- [x] X status links must be HTTPS links to a supported X/Twitter status path; arbitrary X-host lookalikes are rejected.
- [x] Job links must be HTTPS links on a public-looking domain, contain no credentials, and not use a known URL shortener. Clue never requests or resolves them.
- [x] A manually confirmed lead is saved locally with an X post link and a distinct employer/ATS listing URL, then appears in ordinary results when it passes the user's filters.
- [x] Results identify manual leads, display destination hostnames, and say Clue did not recheck live availability.
- [x] Jev remains opt-in and user-triggered; X post content is not sent, and listing text is explicitly treated as untrusted data.
- [x] No scheduled or direct source-fetch path can fetch X; the manual source cannot be enabled from Sources.
- [x] All project-local validation passes in Conda `gen`, with no external calls or Jev usage.
- [x] Documentation and this plan record the decision, implementation, evidence, and limitations.

Validation:

- [x] `conda run -n gen python -m pytest -q` — 84 passed; one third-party Starlette deprecation warning.
- [x] `conda run -n gen ruff check .` — all checks passed.
- [x] `conda run -n gen python -m compileall -q clue_ai` — passed.
- [x] Local TestClient route flow built an X search link, rejected `t.co`, stored a lead locally, exposed it in filtered results with separate employer and X links, and made no external/TypeSafe calls.
- [x] `git diff --check` — passed (Git reported expected CRLF-normalization notices for working files).
- [x] Commit and push the validated milestone directly to `main` under the owner's standing instruction; verify remote `main` at `bdcf5c970b605cf90d9e9904002f6b56f39de608`.

Documentation updates:

- [x] Product definition, architecture, source review, definition gate, README, roadmap, docs index, ADR 0007, and this plan.

Applicable specialized skills:

- `ui-ux-research`, `frontend-design`, `ponytail-balanced`

Expected Git checkpoint: one coherent M1 commit on `main` after all applicable local validation passes.

## Final integration validation

The existing search path must still fetch only enabled approved connectors, display the X manual source separately from fetched-source coverage, and keep Jev behind consent and the explicit Score with Jev action. All validation uses local fixtures and a temporary SQLite database; no X API, X site, external job URL, or Jev network call is part of validation.

## Rollback / recovery

Revert the M1 commit to remove the X route, UI, and migration helper. Preserve the additive `job_sources.context_url` SQLite column; older app code ignores it. X leads can also be removed with the existing local-data deletion action.

## Progress

- 2026-09-30: Reviewed X's official API pricing, automation rules, link guidance, and search help. Selected a manual-only flow to stay within the $0 source budget and avoid site scripting.
- 2026-10-01: M1 implemented, locally validated in Conda `gen`, pushed to `main` as `bdcf5c9`, and verified against `origin/main` at `bdcf5c970b605cf90d9e9904002f6b56f39de608`.

## Implementation discoveries / decisions

- X post reads are currently listed at $0.005 per returned post, so an X API search feed would introduce a paid source.
- X's published automation rules say not to use non-API-based automation such as scripting the X website. Scrapling must not be used against X.
- A user-clicked search link plus manual lead entry gives X discovery value without an X connector making requests.
- Manual leads deduplicate by the final canonical listing URL; they skip fuzzy title/company/location merging so two separate openings with the same title remain distinct.
- User-submitted URLs are never fetched server-side, which prevents URL preview/import behavior from turning a pasted link into server-side request forgery.

## Completion evidence

Local validation passed: 84 pytest cases, Ruff, byte-compilation, diff check, and a TestClient end-to-end lead/search flow. No X, employer URL, or Jev network request was made. `origin/main` was verified at `bdcf5c970b605cf90d9e9904002f6b56f39de608`.
