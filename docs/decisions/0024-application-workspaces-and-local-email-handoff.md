# ADR 0024 — Per-application workspaces and local email handoff

- Status: Accepted and implemented
- Date: 2026-10-06
- Related: [PLAN-020](../plans/PLAN-020-application-workspaces.md), [PLAN-019](../plans/PLAN-019-application-preparation-framework.md), [ADR 0016](0016-durable-applied-tracker.md), [ADR 0023](0023-application-preparation-and-action-boundaries.md)

## Context

The owner wants a page for each prepared job so that files, sourced contacts, outreach drafts, and later receipts are easy to find together. Google OAuth adds setup work and is unnecessary for preparing an email that the owner will send manually.

The current app already stores a durable preparation request per owner-selected listing and versioned files under that request. Its detail page shows only the latest packet, while older versions and receipts are not collected into one file view. The page also presents Gmail as a supported next step after exact packet approval.

## Decision

1. Make `/applications` the main index for owner-prepared listings, and provide one `/applications/{request_id}` dossier for each request. Existing `/preparations` paths stay as compatible aliases during the UI transition.
2. Reuse the preparation request as dossier identity. Do not create a second tracker or duplicate packet records.
3. Show all generated packet versions, their files, local receipt evidence, contact provenance, current stage/reminders, and the related outreach preview together. Keep old or invalidated versions labeled so they are not mistaken for current approved material.
4. Make the in-app recipient/subject/body preview, copy controls, and selected-file bundle the normal email handoff. Contact addresses must retain public source provenance; Clue must not guess them.
5. Keep the existing Gmail adapter optional and separately triggered for owners who configure it. The application workspace must not require Google credentials. The owner remains responsible for sending messages and submitting applications.
6. Keep all files and records local. Validate every requested artifact against its packet, storage root, and recorded content hash before packaging it.

## Consequences

- Users can prepare and organize application materials even when Gmail is disconnected.
- Application content remains grouped by the exact owner-triggered opportunity and packet version.
- A ZIP file is a convenience download, not a submission; its members must be selected from verified files already in the current packet.
- The API credential scope used by the optional Gmail adapter is unchanged. It can technically send, but Clue's adapter still exposes draft creation only. Owners who do not accept that authorization can ignore it and use the local preview.
- The selected-files ZIP can contain personal data and is downloaded only to the owner's device; it is not written into Git or uploaded elsewhere.

## Validation evidence

PLAN-020 M1/M2 implementation passed focused synthetic validation on 2026-10-06: 26 application workflow/preparation/email-handoff tests, Ruff, JavaScript and Python syntax checks, and `git diff --check`. The selected-file ZIP tests cover path sanitization, current-packet membership, tampered or missing content, and cross-request/packet rejection. A stubbed Node VM check covered clipboard success and selectable-text fallback without touching the system clipboard. A synthetic browser review checked the dossier, source attribution, and narrow layout. No live provider, Gmail, or external application action was used.
