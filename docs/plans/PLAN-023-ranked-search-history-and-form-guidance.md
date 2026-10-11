# PLAN-023 — Ranked search history and application-form guidance

Status: M1 and M2 implemented and locally validated on `codex/ranked-search-history-form-guide`; PR validation pending
Created: 2026-10-11 · Last updated: 2026-10-11
Related: [PLAN-019](PLAN-019-application-preparation-framework.md), [PLAN-022](PLAN-022-application-workspaces.md), [ADR 0023](../decisions/0023-application-preparation-and-action-boundaries.md)

## Objective

Make prior search results easy to revisit in rank order, make each eligible listing's external application page and manual preparation action obvious, and add source-backed guidance about public application-form fields to the owner-triggered application dossier.

## Motivation

Results already link to a `/searches` history page, but that route is missing. Listing cards call their external action “Open listing” and place preparation behind eligibility/profile conditions. The existing selected-listing preparation crawl is bounded and read-only, but avoids application pages and does not report their visible field structure. The owner needs to know which application page to open, which role to prepare, and how to approach fields exposed on a public employer form before manually completing it.

## Current state

- Each search snapshot persists ranked results in `search_results`; `get_run_results` orders scored rows by Jev fit signal and retains each run's rank.
- `list_search_runs` already reads saved searches and counts but no `/searches` route or template uses it.
- Cards link to the source listing and conditionally expose a single-listing preparation form.
- Saving a role is durable and navigable through `/saved`; no background preparation starts from save.
- Preparation Researcher uses a four-page public crawler, avoids application forms, and returns company findings and contacts only. The packet Rewriter currently receives no application questions.
- Clue never signs into, fills, or submits an employer form; all preparation starts manually for one listing.

## Desired state

- A named **Search history** navigation tab lists completed and interrupted prior searches, with each run's opportunities surfaced in Jev-ranked order and links to its complete paginated snapshot.
- Each ranked result has clear actions to open its external application/listing page, save it to the existing Saved roles shortlist, or explicitly trigger preparation for that listing when eligibility/profile gates pass. Clicking save remains local and does not crawl or generate.
- The selected preparation can inspect a public employer application page when the owner supplies it or the bounded Researcher discovers it from an allowed employer page. It records only visibly supported field/question labels, control types/options when available, source URLs and crawl observations.
- The generated packet may include draft answers for extracted public text questions. Every answer uses the current evidence/grounding checks and remains a draft for the owner. Missing, dynamic, login-only, or unreadable form details are called out as unknown.
- The owner opens the external page and manually enters/submits all information. Clue never authenticates, writes to a form, or submits.

## Scope

- Add `/searches` history route/template and primary navigation; reuse existing saved runs and result snapshots.
- Aggregate historical positions across retained search runs without allowing an older/lower score to silently replace a newer score for the same canonical job. Clearly show the run date and score provenance; retain each run's own ranked-results link.
- Clarify card actions and expose a distinct external **Open application page** action plus a visible local **Save for later** action. Preserve the current individual **Prepare application** trigger and its Jev/profile/location gates.
- Extend the existing bounded Researcher/crawler result contract to capture public form labels, input types, required state and visible select choices from explicitly public employer pages. Keep crawl limits, HTTPS/public-network checks, source provenance, and form non-interaction.
- Pass only validated public text questions to Rewriter; render form-field reconnaissance and grounded draft answers in the application dossier.
- Update product/architecture/roadmap/UI research, this plan, and one decision record.

## Out of scope

- Any browser automation, login, clicking, typing, form submission, CAPTCHA bypass, or automated application.
- Hidden/private form fields, inferred questions/options, or fabricated answers. No form answer becomes a career fact or modifies Jev matching.
- Bulk or automatic preparation, background crawl from saving, a new CRM/database, cloud sync, or changes to Jev fit/ranking policy.
- New UI or scraping dependencies.

## Source-of-truth impact

- PLAN-023 and a new ADR define history ordering, per-listing action semantics, the bounded read-only form-inspection contract, and answer provenance.
- PLAN-019 remains authoritative for Jev/OpenAI approval and owner action boundaries; PLAN-022 remains authoritative for dossiers and local files.
- Product definition, architecture overview, roadmap, documentation index, and UI research will describe the visible navigation and form-guidance behavior.
- Candidate data and generated answers remain in local application storage and are not committed.

## Existing decisions and constraints

- Jev remains the match validator. The saved match is immutable during preparation.
- One explicit listing action starts research and generation; save/history navigation has no provider side effects.
- Public crawler pages are untrusted data; a source excerpt is not an instruction. Do not bypass authentication or crawler denial.
- Form reconnaissance is an observation, not an application state, submission, or guarantee that the form remains unchanged.
- Keep the Jinja, semantic HTML, vanilla JS, SQLite, and Scrapling stack.

## Supporting skills / tools

- `implementation-plan`, `milestone-delivery`, `ui-ux-research`, `frontend-design`, and `anti-slop`.
- Existing FastAPI, Jinja, native forms/links, SQLite, Scrapling, GPT-6 Luna/Clue harness, and Jev evidence gates.
- Context7 documentation for Scrapling extraction APIs if implementation depends on library-specific selectors.

## Dependencies

- Search snapshot storage and `get_run_results` / `list_search_runs` from the discovery repository.
- Existing application request snapshot, bounded Researcher allowlist, structured output validation, answer grounding, and application dossier.

## Risks and unknowns

- Many employer forms are rendered client-side, login-gated, or not linked from job pages; the UI must explain what could not be observed.
- Public form pages can include personal-data collection fields. Capture labels and visible options only; do not store entered values or submit anything.
- The same listing can occur across multiple search snapshots with changed rank/score. History needs an explicit, inspectable score source and must preserve each run's ordering.
- Additional crawled pages remain bounded by the existing four-page limit; form discovery may compete with contact and employer-research pages.

## Milestones

### M1 — Search history and clear listing actions

Goal: let the owner reopen ranked historical positions and choose a safe next action per listing.

Subtasks:

- [x] Implement `/searches` as paginated unique-position history sorted by latest saved Jev fit score, with run provenance.
- [x] Add navigation tab and preserve clear path from history to each saved run snapshot.
- [x] Label external source opening, local save, and selected preparation actions distinctly.
- [x] Keep Saved roles as the local preparation shortlist; save has no research/generation side effect and prepare remains gated and individually triggered.

Affected areas: repository query helpers, FastAPI route, base/results templates, new search-history template, CSS, route tests, documentation.

Dependencies: retained search run/result records.

Acceptance criteria:

- [x] `/searches` renders historical runs without error, including a useful empty state and active-run state.
- [x] Each run preview is ordered by persisted Jev fit/rank and links to its full saved snapshot; history exposes its timestamp and result counts.
- [x] A job seen in multiple runs has an unambiguous run/score provenance and does not erase historical rank ordering.
- [x] Cards expose a direct external application/listing link when available and separately show Save for later and gated Prepare application actions.
- [x] Save/history clicks do not call provider, crawler, or generation functions.

Validation:

- [x] Synthetic route/repository cases cover empty, active, failed, scored/unscored, repeated-job, and ranked history cases.
- [x] Keyboard/accessibility and narrow viewport review cover the tab, run links, external link, and per-card actions.

Documentation updates:

- [x] Update UI research and this plan with implemented routing/actions and validation evidence.

Applicable specialized skills: ui-ux-research, frontend-design, anti-slop, milestone-delivery.

Expected Git checkpoint: validated M1 commit on the feature branch; advance through PR only after required checks pass.

### M2 — Public application-form reconnaissance and answer drafts

Goal: use the selected listing's bounded public research to describe visible employer form fields and draft evidence-backed responses without interacting with the form.

Subtasks:

- [x] Extend the public crawler to extract static user-facing labels, control type, required flag, and visible select choices, with fixed field and option caps.
- [x] Update Researcher instructions to read linked public forms; derive observations from crawler extraction rather than model-generated labels.
- [x] Identify application links from exact Apply/application anchor text on supplied or crawled pages without clicks, login, or submission.
- [x] Feed exact open-question labels into the Rewriter; validate answer labels and source URLs, then retain Jev candidate-claim grounding.
- [x] Display application links, dated field observations, source links, answer drafts, and unobserved/dynamic limitations in the local dossier.
- [x] Record form changes and access limits in the dossier and source-of-truth docs.

Affected areas: crawler, Researcher schema/prompt/validation, preparation workflow, dossier template/CSS, workflow/crawler/evaluation tests, ADR and product docs.

Dependencies: M1 actions/history; existing bounded Researcher, Rewriter answers, Jev grounding, packet persistence.

Acceptance criteria:

- [x] Only a per-listing manual preparation trigger can start form reconnaissance.
- [x] An allowlisted public HTTPS employer page can yield bounded, source-attributed visible fields; unrelated hosts, denied pages, and over-limit pages remain blocked.
- [x] Inputs, dropdown choices, and required flags are extracted without sending form values, browser interaction, or network writes.
- [x] Only exact extracted public text questions can receive draft answers; each answer passes existing Jev support and writing validation before packet inclusion.
- [x] Login-only, JavaScript-hidden, or uncrawlable fields are explicitly marked not observed; Clue does not guess requirements or answers.
- [x] The dossier distinguishes page observations from verified job facts and retains the crawl timestamp/source URL.

Validation:

- [x] Synthetic crawler fixtures cover label association, input types, required flags, select options, hostile/instructional page text, missing/dynamic controls, cap enforcement, and blocked/login pages.
- [x] Workflow tests verify exact-question gating, answer grounding, no-form/no-answer and inaccessible states, no provider work on ordinary history/save actions, and no mutation/submission route.
- [x] Ruff, focused tests, full test suite, Python syntax, diff checks, and manual responsive/keyboard review pass. JavaScript syntax was unchanged and no new JavaScript was added.

Documentation updates:

- [x] Add an ADR; update PLAN-019/PLAN-022 references, product definition, architecture overview, roadmap, docs index, UI research, and this plan.

Applicable specialized skills: ui-ux-research, frontend-design, milestone-delivery, anti-slop.

Expected Git checkpoint: validate and merge this milestone through the normal repository PR path.

## Final integration validation

The automated suite covers the selected-listing trigger, crawler, answer grounding, dossier output, empty/unscored/conflict/repeated history behavior, and manual action boundary. A separate local browser review covered the history page and its ranked job actions with an isolated synthetic database at desktop and mobile widths. No live employer form or external research/generation provider was invoked in this validation.

## Rollback / recovery

Remove the history route/navigation link to restore the prior search-result entry path. Disable form-field extraction in Researcher output while keeping job/contact research and existing answer validation intact. No new schema or remote service is required. Existing search snapshots, saved roles, packets, and files remain intact.

## Progress

- [x] Confirmed the `/searches` UI link targets a missing history route.
- [x] Confirmed single-listing preparation already provides the correct manual trigger and saved roles already provide a durable shortlist.
- [x] Complete M1 implementation and local automated/browser validation.
- [x] Complete M2 implementation and local automated validation.

## Implementation discoveries / decisions

- Keep Saved roles as the existing “save for later” shortlist; do not create a duplicate preparation-queue table.
- Keep external page opening an ordinary user-controlled link. Research begins only after an explicit Prepare action.
- Form reconnaissance may parse a public page's static visible form metadata; it may not interact with that form.
- Use window ordering to select the latest run per job for the cross-search list; every card retains its run ID/rank so scores stay attached to their source snapshot.
- Parse only labels and visible select option text. Do not retain input values, raw names/IDs, hidden/password controls, or textarea contents. Bound form metadata to 40 fields and 100 options per selected preparation.

## Completion evidence

- Focused matching, preparation, and workflow checks passed: 162 tests.
- Full regression suite passed: 370 tests, 1 upstream Starlette/AnyIO deprecation warning.
- `ruff check clue_ai tests`, Python `compileall`, and `git diff --check` passed.
- Local browser review used an isolated temporary database with synthetic roles: the Search history tab and saved ranked card rendered at 1440 px and 375 px with no horizontal overflow; the page exposed the original posting, snapshot link, and Save for later action. Keyboard Tab reached the visible skip link with a focus outline. No provider or external crawl was invoked.
- Browser console showed a missing `/favicon.ico` (404), an existing app-wide resource and unrelated to the history route; no other browser console warnings were observed.
- No live employer crawl or external provider run is represented by this validation; public-page limits and workflow behavior are covered by synthetic tests.
- GitHub branch protection/CI and PR review remain pending; this is not yet merged to `main`.
