# ADR 0040 — Ranked search history and public application-form guidance

- Status: Accepted; implementation validated locally, PR checks pending
- Date: 2026-10-11
- Related: [PLAN-023](../plans/PLAN-023-ranked-search-history-and-form-guidance.md), [PLAN-019](../plans/PLAN-019-application-preparation-framework.md), [PLAN-022](../plans/PLAN-022-application-workspaces.md), [ADR 0016](0016-durable-applied-tracker.md), [ADR 0023](0023-application-preparation-and-action-boundaries.md)

## Context

Ranked result pages linked to a missing `/searches` index. The database already retained run-specific snapshots and Jev ranks. The owner also needs a clear way to open the original posting, keep a role for later preparation, and understand the public form before personally applying.

The application workflow already has a per-listing manual trigger and a bounded, read-only public crawler. It previously stopped at job/company pages and did not inspect application-form controls. Employer forms can be login-gated, dynamic, or change after inspection, so any form report must preserve exact source and time, avoid candidate-entered values, and remain guidance rather than submission.

## Decision

1. Add a **Search history** tab over retained search snapshots. Show unique visible/unapplied positions ordered by the latest saved Jev score, with score, rank, and the source run/date visible. Each run keeps its own original result page and rank order. Do not combine score records into Jev matching or infer score equivalence beyond the saved job's latest run.
2. Keep **Save for later** as the existing local shortlist action. It must not call a provider, crawl a page, or create a preparation request. The Saved roles page may start preparation only when the user triggers that specific eligible scored listing.
3. Keep the per-listing **Prepare application** / **Prepare for review** action as the only start for research and document generation. The trigger may include a direct public job or application page URL.
4. The Researcher may follow a clearly labeled public application link and read static page markup within the existing crawl limits, only after the owner triggers that listing. Extract user-facing labels, control types, required markers, and displayed option labels. Discard field values, hidden/password controls, raw field names/IDs, and entered content.
5. Use only exact extracted open-ended question labels for answer drafting. Bind answer source URLs to the observed page for that question, and retain the existing evidence/JeV checks. Do not draft plain contact data, attestations, authorization, compensation, availability, or consent without owner-provided answers/evidence.
6. Show discovered application links and the dated form snapshot in the local dossier. Mark missing/unreadable/dynamic fields as not observed. The user opens the external page, enters all values, and submits it manually. Clue never signs in, fills, uploads, or submits.
7. Reuse the current Jinja/SQLite/Scrapling stack and saved-role state; do not add a queue table or another UI dependency.

## Consequences

- The `/searches` link now has a durable destination and positions can be sorted by the latest saved fit signal while preserving run provenance.
- Saved roles become a practical preparation shortlist without creating automatic work or a duplicate state store.
- Public form research can reduce uncertainty about field labels and supported answer drafts. It cannot establish that the employer still uses those fields or that a posting remains open.
- Dynamic/authenticated pages remain unobserved; owner review and manual entry remain required.

## Validation

PLAN-023 M1/M2 implementation validation: 162 focused matching/preparation/workflow tests and 370 full-suite tests passed (one upstream Starlette/AnyIO deprecation warning). Ruff, Python compileall, and `git diff --check` passed. The populated history page was checked in a local browser at 1440 px and 375 px using only an isolated temporary database with synthetic roles; neither viewport had horizontal overflow, and the page exposed snapshot, source-posting, and save actions. Keyboard focus was visible. Synthetic tests cover the bounded form parser, source binding, answer validation, and manual-only preparation trigger. No live employer page or external provider was used. GitHub CI/PR validation remains pending.
