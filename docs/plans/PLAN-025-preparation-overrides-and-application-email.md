# PLAN-025 — Preparation overrides and application email drafts

Status: Complete locally — all acceptance tests passed
Created: 2026-10-12 · Last updated: 2026-10-12
Related: [PLAN-019](PLAN-019-application-preparation-framework.md), [PLAN-023](PLAN-023-ranked-search-history-and-form-guidance.md), [PLAN-024](PLAN-024-lean-task-first-ui.md), [ADR 0023](../decisions/0023-application-preparation-and-action-boundaries.md), [ADR 0041](../decisions/0041-lean-task-first-interface.md), [ADR 0042](../decisions/0042-owner-acknowledged-preparation-and-email-application.md)

## Objective

Let the owner deliberately generate a review packet when a completed Jev assessment reports an acknowledged conflict or the listing's work-location eligibility is uncertain, while retaining Jev's original result and all packet-quality gates. Ensure an explicit application-by-email instruction produces a distinct application email draft through the existing Rewriter and evidence checks, with the generated application files available for manual attachment. Keep the existing selected-listing public form reconnaissance and grounded answer drafts visible and usable.

## Motivation

Before this change, search history hid **Generate packet** unless Jev reported `match` or `review` and location eligibility was already `eligible`; the service independently rejected those cases. The existing Researcher received the saved job description, could read a bounded public application page, and extracted visible open questions for grounded Rewriter answers. The dossier already offered sourced email previews and a selected-attachment ZIP, but did not distinguish explicit application-by-email instructions from ordinary outreach.

## Baseline before implementation

- Preparation requires a completed scored Jev result, an active visible unapplied listing, a permitted CV, and candidate evidence or a permitted technical profile. A scored Jev conflict and/or unconfirmed/ineligible location requires a separate per-listing acknowledgement.
- Search results, history, and saved-role cards expose the same trigger and status-specific acknowledgement. Readiness checks match service acceptance of approved claims or a permitted technical profile.
- The saved Jev match and eligibility fields are immutable inputs to a preparation snapshot. Jev separately reviews factual support and the tailored CV before document artifacts are created.
- The Researcher reads the full saved role context and up to four bounded public pages, may follow a public Apply link, and observes static user-facing form fields without interacting with them. Exact observed open-question labels are passed to the Rewriter and answers pass existing candidate-evidence and Jev support checks.
- The Rewriter currently creates a verified-contact outreach draft when supported. The dossier previews To/Subject/Body and lets the owner select packet attachments. It does not label or draft a separate application-by-email message when the listing explicitly instructs the owner to email application materials.

## Desired state

- A completed scored `conflict` or an unconfirmed location can expose a clear, per-listing owner confirmation to start preparation. Each confirmation states the exact Jev/location finding being acknowledged and is persisted with the immutable preparation snapshot.
- `unassessed`/unscored, inactive, hidden, or already-applied listings remain blocked; an override never changes Jev's saved fit, filter, or eligibility result and never bypasses evidence, Jev support, final tailored-CV approval, writing quality, or owner review.
- The same scoped trigger and status explanation appear in search results, search history, and saved roles. Setup links appear whenever the local preparation service would accept the available candidate evidence.
- If the saved listing text or a crawled public application page explicitly directs applicants to submit by email, the Rewriter creates an application-specific unsent email draft. Its recipient is populated only from an exact, verified public address; otherwise the To field remains blank and the dossier states that the owner must verify it. The approved tailored CV and cover letter remain selectable attachments.
- Existing static public form reconnaissance and exact-question answer drafting continue through the same selected-listing Researcher/Rewriter workflow, with source and Jev checks intact. Clue never signs in, fills, uploads, sends, or submits.

## Implemented behavior

- Result, Search history, and Saved roles use the same **Generate packet** control. A scored conflict and a non-eligible/unconfirmed location each show a required per-listing acknowledgement; the service rejects missing confirmations and still rejects unassessed/no-score or invalid listing states.
- The immutable request snapshot records each original Jev status and the owner's acknowledgements. The dossier displays both. Jev's score, filter, and eligibility records are unchanged, and final Jev content/CV checks still run.
- The Researcher receives the saved role description and may follow the bounded public Apply path. Static questions and field details are recorded with exact page URLs and observation times; the Rewriter answers only observed open questions. Dynamic or inaccessible fields remain unknown.
- An exact explicit email-application instruction may come from the saved description or a crawled public page. The same Rewriter prepares the unsent body; the local harness resolves a verified recipient or leaves it blank. The dossier shows the instruction/source, message, and approved packet files. Application emails stay in local preview/copy/ZIP handoff; no Gmail draft is created for this path.
- Ordinary outreach remains separate. The Rewriter receives public contact verification state but not raw email addresses; Clue assigns any locally verified address after the draft passes evidence checks.

## Scope

- Add owner acknowledgements for a saved Jev conflict and/or non-eligible/unverified location to the selected listing trigger.
- Keep the trigger gated on a completed Jev run and on listing state; bind acknowledgements and the original statuses/evidence into the request snapshot and dossier.
- Align readiness checks and trigger availability across result, history, and saved-role cards.
- Detect explicit email-application directions from the saved role description or an observed public application page, direct the existing Rewriter to write an application message for that channel, retain strict address/source/evidence checks, and label/render the draft with the existing manual attachment handoff.
- Add targeted service, route, template, Researcher/Rewriter, and grounding tests; update product and architecture documentation, this plan, and a decision record.

## Out of scope

- Changing or rewriting the saved Jev fit/filter/eligibility decision, adding an automatic Jev override, or allowing preparation before Jev completes scoring.
- Bypassing Jev factual support, final tailored-CV approval, cover-letter quality, source binding, profile consent, or packet owner review.
- Form authentication, browser interaction, form entry, file upload, application submission, outbound email, or automatic attachment sending.
- Sending any email or changing any external account/provider cap.

## Source-of-truth impact

Update `docs/product-definition.md`, `docs/architecture/overview.md`, this plan, and a new ADR. Update `docs/roadmap.md` only if its current next-step status directly describes these gates. The repository has no changelog file.

## Existing decisions and constraints

- Jev is the only job-fit authority and saved matching decisions remain read-only in packet work (ADR 0023); Jev also must approve the final tailored CV (ADR 0025).
- Only an explicit per-listing owner action starts research or generation. Public form fields can be observed, never manipulated (ADR 0040 / PLAN-023).
- The owner performs all application and outreach actions. Email previews and selected attachment bundles are local handoff tools (PLAN-022).
- Preserve the existing lean, task-first page structure (ADR 0041); do not add a settings page, workflow dashboard, new dependency, or global bypass switch.
- User instruction: ignore app-local spending allowance caps; external provider caps are managed externally. Keep existing usage accounting and consent, but do not change caps.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, `ponytail-balanced`.
- `ui-ux-research` and `frontend-design` for a small, accessible extension to the existing listing action. Candidate evaluation: **adapt** the current semantic inline form and design tokens; reject a global settings toggle because the acknowledgement must bind to a specific listing and Jev evidence; reject a modal/new UI library because native labelled checkboxes and the existing warning pattern suffice.
- Existing pytest suite and local synthetic providers/crawler fixtures. No live API, account, or browser interaction is required for acceptance.

## Dependencies

- Existing preparation snapshot/idempotency, bounded Researcher, question answer support, outreach draft validation, packet renderer, and application attachment ZIP.
- No schema migration is expected; owner acknowledgements and explicit email instructions can be stored in the already versioned JSON snapshot/output.

## Risks and unknowns

- An override can be mistaken for Jev approval. Mitigation: name each acknowledged status, show it in the dossier and packet, and leave the saved Jev result unchanged.
- The full application page may be dynamic/login-gated or inaccessible. Mitigation: keep current “not observed” reporting and never guess fields or answers.
- A page may mention email without requesting email submission. Mitigation: use conservative explicit-instruction matching and test ordinary contact/outreach wording as a negative case.
- Some explicit email instructions omit a public recipient address. Mitigation: retain the draft with an empty To field; never infer or fabricate an address.

## Milestones

### M1 — Owner-resolved preparation blockers

Goal: expose and persist a deliberate per-listing override for an already-scored Jev conflict or uncertain location without mutating the saved assessment or weakening downstream validation.

Subtasks:

- [x] Identify and report each blocker separately on all listing entry points.
- [x] Require a separate owner acknowledgement for each current blocker at the service boundary.
- [x] Keep no-score/unassessed, inactive, hidden, and applied listings blocked.
- [x] Bind the acknowledged status/evidence into the preparation snapshot and show the immutable Jev result plus override in the dossier.
- [x] Align profile/evidence readiness copy with service acceptance of approved claims or a permitted technical profile.

Affected areas: preparation service, web routes, result/history/saved/dossier templates, existing preparation tests, product/architecture docs, ADR.

Dependencies: none.

Acceptance criteria:

- [x] Match/review + eligible keeps the ordinary **Generate packet** action without an override.
- [x] A scored conflict and/or unconfirmed location exposes the exact required checkbox(es) and can start only when every current blocker is acknowledged.
- [x] The snapshot and dossier retain original Jev status/evidence and explicit acknowledgements; the saved search result is unchanged.
- [x] Missing score, unassessed Jev state, inactive, hidden, and applied listings cannot be started, even by a forged POST.
- [x] The action renders when a permitted technical profile exists even if there are no approved candidate claims, consistent with service rules.
- [x] Final Jev support/CV approval, content quality, packet review, manual form entry, and send/submit boundaries remain enforced.

Validation:

- [x] Parameterized service tests for both blockers, combined blockers, missing acknowledgements, invalid saved states, snapshot binding, and idempotency.
- [x] TestClient checks of result/history/saved views and exact per-status UI copy.
- [x] Dossier test proves owner override and original Jev values are both visible.
- [x] Ruff, focused tests, full suite, Python compile, and `git diff --check`.

Documentation updates:

- [x] ADR and source-of-truth gate descriptions; progress and evidence in this plan.

Applicable specialized skills: `ui-ux-research`, `frontend-design`, `milestone-delivery`.

Expected Git checkpoint: one validated commit on this feature branch; advance only through the repository PR/CI path.

### M2 — Role-specific application email and verified form drafts

Goal: use the existing selected-listing research and writing agents to prepare the materials explicitly requested by the role, including application-email copy and public open-question answers, with evidence-backed files ready for owner handoff.

Subtasks:

- [x] Bind an exact application-by-email instruction from the saved role description or validated public application page; do not classify ordinary recruiter contact details as an application instruction.
- [x] Prompt the existing Rewriter to draft an application message only for that channel, while resolving a recipient locally from exact verified sources or leaving it blank.
- [x] Preserve existing Jev-supported answers for exact static public form questions and report dynamic/unavailable questions as unknown.
- [x] Render a clearly labelled application email preview, verified/blank recipient state, and the approved tailored CV/cover letter attachment choices through the existing local handoff.
- [x] Keep ordinary outreach behavior separate and unchanged when no application-email instruction exists.

Affected areas: application snapshot/prompt/validation workflow, dossier template, workflow tests, architecture/product docs, this plan, ADR.

Dependencies: M1; existing Researcher form extraction, Rewriter answer schema, Jev support checks, packet artifact/attachment flow.

Acceptance criteria:

- [x] An explicit “email your CV/application/materials” instruction in the selected role or public application page produces an application email draft, distinct in UI and content from unsolicited outreach.
- [x] “Contact us by email” or a plain recruitment address without an application instruction does not activate the application-email path.
- [x] Recipient values can only come from a source-verified public address; missing or ambiguous address leaves To blank and does not erase the supported draft.
- [x] Every factual statement in the draft retains existing candidate evidence and Jev support; application answers match exact observed public questions and pass existing checks.
- [x] The local dossier offers generated packet files as selectable attachments and preserves owner review; no send, form entry, upload, or submission occurs.
- [x] Existing outreach drafts, static question drafts, and empty/inaccessible form handling pass regression tests.

Validation:

- [x] Synthetic positive/negative instruction fixtures, with and without a verified recipient, plus exact-question and inaccessible-form workflow fixtures.
- [x] Verify rendered attachment options refer only to artifacts in the approved packet; no external Gmail/send API call is invoked.
- [x] Ruff, focused tests, full suite, Python compile, and `git diff --check`.

Documentation updates:

- [x] Update product/architecture flow, decision record, roadmap, and this plan with implementation/test evidence.

Applicable specialized skills: `milestone-delivery`, `ponytail-balanced`.

Expected Git checkpoint: one validated commit on this feature branch; advance only through the repository PR/CI path.

## Final integration validation

Exercise one synthetic conflict override and one unverified-location override end to end; assert the stored Jev result is unchanged. Exercise an explicit application-by-email case with public form questions, verify exact answer and email evidence gates, review the rendered dossier and attachment choices, and confirm a contact-only negative case does not become an application email. Run all project checks required by both milestones.

## Rollback / recovery

Remove the override checkbox branches and associated service arguments to restore strict preparation availability while retaining saved snapshots and Jev decisions. Disable the application-specific label/prompt branch to return to ordinary outreach handling; existing form-question drafting and artifacts remain independent. No database migration or external state change is introduced.

## Progress

- [x] Traced the generic blocker to both the search-history action gate and the service query; found equivalent gates on results and saved roles.
- [x] Confirmed public form reconnaissance, exact-question answers, local email preview, and attachment selection already exist; found that explicit application-by-email instructions are not distinguished from outreach.
- [x] Complete M1 and capture acceptance evidence.
- [x] Complete M2 and capture acceptance evidence.

## Implementation discoveries / decisions

- Keep Jev's saved fit, filter, and eligibility decision immutable. An owner override authorizes packet preparation only and does not erase or relabel the Jev result.
- Unassessed/no-score and job-state blockers remain non-overridable because they lack a completed, current Jev decision or a valid active listing to bind.
- Reuse the existing verified-contact and attachment-preview flow for application-by-email; no new mail integration or UI library.
- Keep OpenAI/Jev usage caps and provider settings unchanged.

## Completion evidence

Local acceptance completed 2026-10-12. The project `.venv` ran all **386 tests** successfully (80.47 seconds; one upstream Starlette/AnyIO deprecation warning). Ruff passed, Python byte-compilation passed, and `git diff --check` passed. Focused blocker, form-question, and email workflow validation passed **32 tests**. Full-suite coverage includes synthetic conflict/location acknowledgement, unchanged Jev rows, public Apply-page discovery, exact question-answer generation, explicit application-email drafts from both the saved job description and linked page (with and without a public recipient), writer-context email redaction, dossier rendering, and no application submission. No live OpenAI, Jev, employer, or Gmail request was used.
