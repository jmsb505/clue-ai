# ADR 0042 — Owner-acknowledged preparation and email-application handoff

- Status: Accepted — implementation and local validation passed; PR checks pending
- Date: 2026-10-12
- Related: [PLAN-025](../plans/PLAN-025-preparation-overrides-and-application-email.md), [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0040](0040-ranked-search-history-and-public-form-guidance.md), [ADR 0041](0041-lean-task-first-interface.md)

## Context

The listing cards hid packet generation whenever Jev reported a conflict or did not confirm an eligible location. The same states were rejected by the preparation service, leaving no user action to resolve the message. The Researcher already received the saved role description and could inspect a linked public application page, and the Rewriter already supported grounded answers for observed open questions. The dossier had a local email preview and selectable packet attachments, but generation did not distinguish an explicit application-by-email instruction from ordinary outreach.

## Decision

1. Keep Jev as the only match authority. Allow the owner to start preparation for a completed scored Jev conflict and/or a non-eligible or unconfirmed location only after separately acknowledging each status on that specific listing. Bind the acknowledgements to the immutable preparation snapshot and show the original Jev result and warning in the dossier. This action permits research and drafting; it never converts a conflict to a match or changes saved Jev fields.
2. Keep no-score/unassessed, inactive, hidden, already-applied, missing-CV, and missing-evidence/profile conditions blocked. Retain candidate-content Jev support, final tailored-CV Jev approval, writing and source checks, packet review, and every manual action boundary.
3. Preserve one explicit **Generate packet** action on result, history, and saved-role cards. Use separate required checkboxes for each currently applicable blocker; do not add a global setting or bulk action.
4. On the individual owner trigger, give the Researcher the full saved job description and bounded access to the linked public role/application pages. It may record static field labels, exact open-question labels, and explicit email-application instructions. Dynamic, authenticated, or inaccessible fields remain unknown. Never sign in, fill, upload, send, or submit.
5. Pass exact observed questions and the validated application-email instruction to the existing Rewriter. It may prepare source-bound answers and, only when the role text or crawled public application page explicitly asks applicants to apply by email, one unsent application email. A plain recruitment email address or a request to contact someone does not qualify.
6. Populate the application email recipient only from the explicit instruction or an exact public recruitment inbox that passed source validation. If no unique address is verified, retain a useful draft with an empty address and tell the owner to verify it. Keep the selected packet files available as owner-chosen attachments in the local dossier; never claim they have been attached or sent.
7. Leave optional Gmail draft creation behind its separate existing owner action after packet approval. Do not expose Gmail or submission tools to the model, and do not change provider settings or local usage controls.

## Consequences

- A user can deliberately prepare a scored warning-state listing while seeing that the warning remains real and unchanged.
- Open questions and application email requirements can be discovered from the public Apply path and included in the same selected-role packet.
- Automated research/drafting stays distinct from external application actions. The owner reviews content, chooses attachments, enters form answers, and sends/submits manually.
- Public pages may change or omit dynamic fields. Each observed field, answer, and instruction remains source-bound and must be checked against the live employer page before use.

## Validation

The project `.venv` ran all **386 tests** successfully (80.47 seconds; one upstream Starlette/AnyIO deprecation warning). The application-preparation and workflow suites passed **155 tests**. Synthetic coverage confirms conflict/location acknowledgements with unchanged saved Jev values, visible controls on result/history/saved routes, public Apply-page crawling, exact question-answer generation, explicit email instructions from the listing and linked page with and without a verified address, writer-context email redaction, contact-only negative cases, dossier/attachment rendering, and no application submission. Ruff, Python byte-compilation, and `git diff --check` passed. No live API, employer, Gmail, or OpenAI request was used; PR checks remain pending.
