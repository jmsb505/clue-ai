# PLAN-020 — Per-application workspaces and local outreach handoff

Status: M1 and M2 implemented, focused-validated, and pushed to `main` at `e85eeaa`
Created: 2026-10-06 · Last updated: 2026-10-06
Related: [PLAN-019](PLAN-019-application-preparation-framework.md), [ADR 0024](../decisions/0024-application-workspaces-and-local-email-handoff.md)

## Objective

Give every individually prepared job a clear local workspace that keeps its generated files, versions, contact evidence, outreach draft, attachment choices, receipts, and owner-recorded progress together. Make the default outreach handoff a preview and copy/download flow inside Clue; Gmail authorization must not be required.

## Motivation

PLAN-019 already stores each preparation request and its generated files separately, but calls the workspace “Preparation,” displays only the newest packet's files, and leaves uploaded receipts in the outcomes area. That makes a growing collection of application materials hard to browse. The optional Gmail adapter also makes the external setup feel like part of the normal flow when a local preview is sufficient.

## Current state

- `/preparations` lists owner-triggered requests and reminders. `/preparations/{request_id}` is already one detail page per selected listing.
- Artifacts are kept locally by request and packet revision. The detail page shows only the latest packet, while older revisions remain on disk and in SQLite.
- Submission receipts are locally stored and hash-checked when downloaded, but the per-request detail page does not list them.
- Outreach previews already contain the proposed recipient name, subject, body, and cited contact source. Gmail is a separately gated optional route.

## Desired state

- An **Applications** index leads to one dossier for each owner-prepared listing. Existing preparation URLs remain compatible.
- Each dossier presents its opportunity and stage, all packet versions and generated files, receipt files, sourced contact information, the outreach preview, and relevant reminders/interview notes in one navigable page.
- A message preview shows a publicly verified recipient address when available, subject, body, contact provenance, and a checklist of actual files to attach. Copy controls and a ZIP containing only the selected packet artifacts support manual email composition.
- All records and downloads stay on this device. The owner reviews and manually sends messages and submits applications. Gmail connection remains optional and is not needed for the core workflow.

## Scope

- Add canonical `/applications` and `/applications/{request_id}` routes while preserving `/preparations` aliases.
- Present historical packet versions and locally stored submission receipts with their original filenames, hashes/versions, and safe download links.
- Add local outreach preview controls for copying recipient, subject, and body, plus a validated ZIP download for owner-selected artifacts in that packet.
- Keep the existing single-user SQLite and Jinja/CSS/vanilla-JS stack; do not add a component or archive dependency.
- Update product, architecture, decision, roadmap, and UI research records to describe the dossier and local-first email handoff.

## Out of scope

- Requiring, configuring, or authorizing Google OAuth for the local preview flow. The existing Gmail adapter may remain available as an optional separately triggered capability.
- Sending email, reading a mailbox, submitting application forms, or adding automatic application actions.
- Unverified or guessed recipient addresses, documents not present in the selected packet, synchronization to cloud storage, or another application-tracker database.
- In-place editing or saving a second owner-authored email version; owners can edit after copying into their email client.

## Source-of-truth impact

- This plan and ADR 0024 define the per-application local dossier and clarify that Google setup is optional.
- PLAN-019 remains authoritative for Jev/OpenAI generation gates, packet approval, the manual action boundary, and the optional Gmail adapter.
- Product definition, architecture overview, roadmap, documentation index, and UI research will describe the new application-workspace experience.
- Personal application documents, addresses, messages, receipts, and owner notes remain local and are not added to Git.

## Existing decisions and constraints

- Preserve the local single-user app, Jev matching authority, manual per-listing preparation trigger, and owner-controlled submission boundary.
- Use existing immutable packet records and local files; do not duplicate application identity in a new table.
- Only show a recipient email if contact research retained that address from a public source. Keep the contact's source link adjacent.
- Bundle downloads must resolve only artifact IDs that belong to the requested packet and verify safe storage paths and content hashes before including a file.
- Preserve access to the existing Gmail adapter for owners who already configure it, but never make it the default or a prerequisite.

## Supporting skills / tools

- `implementation-plan` and `milestone-delivery` for staged delivery and evidence.
- `ui-ux-research` and `frontend-design` for an application-specific, keyboard-accessible, responsive file workspace using the existing design system.
- `anti-slop` for new interface and documentation copy.
- Existing FastAPI, Jinja, SQLite, native browser APIs, and Python standard library only.

## Dependencies

- PLAN-019 application preparation models, artifact storage, receipt records, and manual stages.
- Existing database fixtures and application-workflow test harness.

## Risks and unknowns

- A selected ZIP could accidentally include an unrelated file if request/packet/artifact binding is loose; validate each ID, path, hash, and selection server-side.
- Old packet versions can be obsolete or invalidated; label them clearly and keep attachment selection bound to the current packet.
- Clipboard access may fail outside a secure browser context; keep the text selectable and give a clear copy status/error.
- Some packets may have no verified contact email or only one generated file; empty and partial states must remain useful.
- The existing optional Gmail path still uses a Google scope that can send; the local copy/download path avoids that authorization entirely.

## Milestones

### M1 — Application index and dossier file archive

Goal: make each owner-prepared listing easy to reopen as one organized application workspace.

Subtasks:

- [x] Add canonical Applications index and per-application dossier routes; keep old preparation URLs working.
- [x] Group every packet revision and its artifact downloads under the owning application.
- [x] Show locally uploaded receipt records and retain the existing safe receipt-download verification.
- [x] Organize the detail page into navigable sections for summary, files, research, and owner progress.

Affected areas: navigation, web routes, application-workflow data access, Jinja templates, CSS, workflow tests.

Dependencies: PLAN-019 M0–M5 local data model.

Acceptance criteria:

- [x] Every preparation request has one working `/applications/{request_id}` dossier; unknown IDs return 404.
- [x] The Applications index links to each dossier and shows its current preparation/application status.
- [x] Current and older packet files are visible under the correct version; receipts are listed only for their request and remain hash-checked.
- [x] Existing `/preparations` URLs and POST actions continue to work.
- [x] No personal data is moved into the repository or a new external service.

Validation:

- [x] Synthetic route/template tests cover current/older packet versions, submitted-with-receipt, compatible legacy routes, and unknown requests.
- [x] Receipt links and artifact links are request/packet-bound; tests confirm the historical artifact remains downloadable only through its packet route.
- [x] Browser review confirmed the dossier sections and narrow layout; the mobile navigation scrolls within itself without page-level horizontal overflow. Native section links, visible focus styles, and reduced-motion rules are retained.

Documentation updates:

- [ ] Update product definition, architecture overview, roadmap, documentation index, and this plan.

Applicable specialized skills: ui-ux-research, frontend-design, anti-slop, milestone-delivery.

Expected Git checkpoint: one validated M1 commit, pushed directly to `main` per the owner's delivery instruction.

### M2 — Local outreach preview and selected-attachment bundle

Goal: prepare an organized manual email handoff without requiring Google authorization.

Subtasks:

- [x] Show the sourced contact and verified public email, subject, and outreach body in the application dossier.
- [x] Add copy actions for recipient, subject, and body with keyboard-accessible status feedback and selectable-text fallback.
- [x] Add attachment choices from files that actually exist in the active packet, with clear names and artifact types.
- [x] Generate a local ZIP containing only selected artifacts from that packet after validating request ownership, safe paths, and SHA-256 hashes.
- [x] Keep the existing Gmail draft action separate and optional; do not call it from the local preview/copy/download controls.

Affected areas: artifact/packet helpers, FastAPI download route, dossier template, vanilla JS, CSS, security/workflow tests, docs.

Dependencies: M1 dossier and packet-version display.

Acceptance criteria:

- [x] No Gmail client ID, OAuth consent, or connection is needed to view/copy a draft or download selected files.
- [x] The preview never fabricates an email address and keeps its public source visible.
- [x] A missing or suppressed contact produces a clear no-address state without offering a misleading copy/send action.
- [x] ZIP membership contains only selected artifact IDs from the bound request/packet; forged, missing, modified, or cross-packet IDs fail safely.
- [x] Clue does not send the message or submit the application.

Validation:

- [x] Synthetic route tests cover the preview, no-address state, selected ZIP membership, path sanitization, tampered/missing files, and cross-request/cross-packet access. A Node VM check exercised clipboard success and failure with a stub, leaving the system clipboard untouched.
- [x] Browser review checked the rendered contact/source, message fields, attachment choices, and responsive layout; safe names were confirmed in the ZIP test. Keyboard status controls use native buttons and a polite live region.
- [x] Focused workflow tests, Ruff, JavaScript syntax, Python syntax, and diff checks pass.
- [ ] Full repository suite: attempted, but test collection stops because the active Python environment does not have the existing `scrapling` dependency required by `tests/test_company_sources.py`.

Documentation updates:

- [ ] Record local-first handoff behavior, file storage, and the optional status of Gmail in product, architecture, decision, roadmap, and UI research docs.

Applicable specialized skills: ui-ux-research, frontend-design, anti-slop, milestone-delivery.

Expected Git checkpoint: one validated M2 commit, pushed directly to `main` per the owner's delivery instruction.

## Final integration validation

Run the application/workflow test modules, `ruff check clue_ai tests`, Python byte-compilation, and the full repository suite. Exercise index-to-dossier navigation; current/older packet documents; receipt visibility/download; source provenance; copy controls; selected ZIP contents and all invalid artifact cases. Keep OpenAI credentials empty and use synthetic packet/contact/receipt fixtures only.

## Rollback / recovery

The dossier uses existing records and files. If the new routes or ZIP handoff fail, keep `/preparations` available, disable the bundle route, and leave packet/artifact/receipt rows untouched. No migration is planned.

## Progress

- [x] Confirmed the current app already stores per-request preparation packets, but the UI exposes only its latest revision and separates receipts.
- [x] Selected the existing Jinja/CSS/native-control stack; no new UI or ZIP package is needed.
- [x] Owner direction: prefer an in-app email mock-up and attachment checklist so Gmail setup is not required.
- [x] Complete M1.
- [x] Complete M2.

## Implementation discoveries / decisions

- Reuse `preparation_requests.id` as the stable dossier identity; a second application-record table would create unnecessary duplication.
- Keep Gmail authorization as an optional pre-existing adapter. Local preview, copy, and attachment bundle work without it.
- Keep packet versions immutable; copied text is editable in the owner's email client, while the packet remains a record of generated content.

## Completion evidence

Focused verification on 2026-10-06: `tests/test_application_workflow.py`, `tests/test_application_prep.py`, and `tests/test_application_email_handoff.py` — 26 passed; `ruff check --no-cache clue_ai tests` passed; `node --check clue_ai/static/app.js` passed; Python source parsing and `git diff --check` passed. An isolated Node VM stub exercised clipboard success and fallback without changing the system clipboard. A synthetic browser review verified the dossier and small-screen layout: the document fits the viewport and the navigation owns its horizontal scrolling. No real contact, application data, OpenAI call, Gmail authorization, email, or submission was used. A full-suite attempt stopped during collection because `scrapling` is absent from the active validation Python environment; no network installation was attempted. A prior PLAN-019 test run separately recorded an unrelated Jev scoring expectation failure.
