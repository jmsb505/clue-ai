# ADR 0005: Local Python application and server-rendered UI

**Status:** ACCEPTED for the first local increment
**Date:** 2026-09-30

## Context

The product is a single-user desktop-local job search. Scraping, PDF/DOCX extraction, local indexing, and Jev calls are Python workflows. The repository previously left the UI/runtime and persistence format undecided. The app needs a friendly multi-page search/review interface without paid hosting, a separate account, analytics, or a large front-end dependency stack.

## Decision

- Implement the local application in Python with FastAPI and Uvicorn, bound to `127.0.0.1` only.
- Render views on the server with Jinja templates, semantic HTML forms, and project-owned CSS/vanilla JavaScript. Do not require Node for the app.
- Use SQLite through Python's standard library for profile, preferences, source registry, normalized listings, search runs, Jev usage, and save/hide state.
- Store the original CV and local database under an ignored `.data/` directory. Do not create cloud backups.
- Extract PDF/DOCX text locally with `pypdf` and `python-docx`; make extracted content editable before saving a candidate profile or sending any fields to Jev.
- Load simple `KEY=value` configuration from `.env` through project code, without overriding environment variables already supplied by the owner. Keep `.env` ignored and commit only `.env.example` with a blank key variable.
- Restrict request hosts/origins to the local app; do not load external fonts, trackers, or UI libraries.

## Alternatives considered

- **React/Vite or another SPA:** Rejected for the first increment. It adds a Node build, frontend state API, and dependency surface where native forms and server-rendered result views meet the single-user requirement.
- **Electron/Tauri desktop shell:** Deferred. A localhost web app is cheaper to build and run locally and can be wrapped later only if browser ergonomics demonstrate a real need.
- **Hosted SaaS or cloud database:** Rejected under the local-only and $0 service constraints.
- **Custom in-house PDF/DOCX parsing:** Rejected; complex document formats should use maintained parsers rather than a partial bespoke implementation.

## Consequences

- One Python process owns UI, local workflows, and database access; long-running source refreshes must run as visible background operations so the request path remains responsive.
- The app must bind only to loopback and validate local host/origin requests. This local-only design is not a multi-user security boundary.
- Jinja and native controls keep accessibility and keyboard behavior in the project's code, so those states require explicit validation.
- `.data/` and `.env` must stay ignored; the UI deletion action must remove personal rows and the CV while preserving non-personal source definitions.
- The existing Conda `gen` environment uses Python 3.10.21 and is within the TypeSafe SDK's documented Python >=3.10 requirement.

## Implementation state

The Python package, localhost server, SQLite schema/repository, local CV extraction, Jinja views, project-owned CSS/JavaScript, and ignored `.env` are implemented and passed M1 offline validation. The owner-configured key is local and is not part of the repository. M2's single live Jev request used synthetic data only; no CV or job-source data was sent.

## Reconsideration

Revisit the UI/runtime only if the owner chooses to distribute a desktop installer, needs offline browser support, or the server-rendered interface fails documented usability checks. Do not add cloud infrastructure without a new product decision.

## Evidence

- Owner's single-user local-use decision: [ADR 0004](0004-single-user-local-app.md)
- Current FastAPI template and upload docs: https://fastapi.tiangolo.com/advanced/templates and https://fastapi.tiangolo.com/tutorial/request-forms-and-files
- Current CV parser docs: https://pypdf.readthedocs.io/en/stable/user/extract-text.html and https://python-docx.readthedocs.io/en/latest/user/documents.html
- Implementation/UI evaluation: [UI/UX implementation review](../research/ui-ux-implementation-review.md)
- Build delivery: [PLAN-002](../plans/PLAN-002-local-first-job-search-app.md)

## Affected source-of-truth documents

- `docs/architecture/overview.md`
- `docs/roadmap.md`
- `docs/readiness/definition-gate.md`
- `README.md`
- `docs/plans/PLAN-002-local-first-job-search-app.md`
