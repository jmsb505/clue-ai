# ADR 0041 — Lean task-first interface

- Status: Accepted — implementation and local validation passed; pull-request checks/merge pending
- Date: 2026-10-12
- Related: [PLAN-024](../plans/PLAN-024-lean-task-first-ui.md), [PLAN-022](../plans/PLAN-022-application-workspaces.md), [PLAN-023](../plans/PLAN-023-ranked-search-history-and-form-guidance.md)

## Context

The interface grew to expose search, profile/evidence setup, six result views, source and company controls, settings, saved/hidden/applied roles, outcomes, and application dossiers at the same time. Search criteria are expanded by default, and the per-listing preparation action is labeled differently across result, history, and saved views. The resulting navigation and content density obscure the central task: deliberately select one role and prepare a reviewable packet for it.

## Options considered

| Option | Evaluation | Decision |
|---|---|---|
| Keep every route and control visible | Avoids clicks but produces long navigation, dense forms, and repeated explanations. It does not help users distinguish the core job path from setup and diagnostic tools. | Reject |
| Remove secondary routes and technical evidence | Reduces visible content but would discard privacy, data-management, evidence, sourcing, and Jev explanation capabilities. | Reject |
| Group secondary destinations and progressively disclose less-used controls while standardizing the selected-job action | Uses existing semantic HTML and CSS, keeps every function available, and reduces initial decision load without changing workflow behavior. | Adopt |

## Decision

1. Keep four primary destinations: **Find jobs**, **Search history**, **Saved roles**, and **Applications**. Put profile/evidence, applied/hidden/outcomes, company/source management, settings, and privacy links in a secondary disclosure. Open that disclosure when a secondary page is active.
2. Show only the role, work-from location, workplace style, and local city as default search fields. Put secondary criteria and ranking weights in **Advanced filters**; retain submitted values while closed.
3. Replace the result-view tab row with a labelled native selector while preserving the existing six views and their counts.
4. Label the selected-job preparation trigger **Generate packet** wherever it appears. Explain that it researches and drafts materials for that one listing, retains selected-CV choice, and keeps the optional application URL secondary.
5. Lead the dossier with current packet files and the next owner action. Put detailed evidence and optional tooling behind disclosures, but leave decision-affecting Jev warnings, grounding outcomes, source links, and manual action boundaries prominent.
6. Preserve all automatic discovery/matching behavior, per-listing manual preparation, the human review/approval gate, and manual application/outreach actions.

## Consequences

- The main navigation is smaller and the user can still reach every existing feature.
- Users can submit a search with a short set of meaningful fields; specialized criteria remain available without dominating the page.
- Packet generation has one consistent label and explanation.
- The dossier opens with deliverables while retaining technical evidence and audit detail on demand.
- This is a presentation change; it does not alter Jev scoring, packet contents, crawler policy, consent, or external actions.

## Validation

PLAN-024 M4 passed locally. The full pytest suite passed (371 passed, one upstream Starlette/AnyIO deprecation warning); Ruff, Python byte-compilation, and `git diff --check` passed. A synthetic local Chromium review at 1440, 390, and 320 CSS pixels confirmed four primary destinations, collapsed Advanced filters, a visible and enabled **Generate packet** action, keyboard reachability with a 3px focus outline, and no horizontal overflow. The preview used an isolated temporary database, synthetic role/CV/claim data, and empty provider keys. No live profile, crawler, or external service was used. Pull-request checks and merge remain pending.
