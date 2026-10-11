# PLAN-024 — Lean task-first interface and packet generation

- Status: Complete — implementation and local validation passed; delivered in PR #8
- Date: 2026-10-12
- Related: [PLAN-022](PLAN-022-application-workspaces.md), [PLAN-023](PLAN-023-ranked-search-history-and-form-guidance.md), [ADR 0041](../decisions/0041-lean-task-first-interface.md)

## Goal

Reduce the amount of interface shown at once and make the owner-triggered **Generate packet** action easy to find for one selected job. Keep existing research, Jev decisions, safety boundaries, and secondary capabilities intact.

## User path

1. Find jobs or reopen a ranked search.
2. Choose one eligible listing.
3. Select **Generate packet** to start research and tailored-file generation for that listing only.
4. Review the files and supporting evidence in that role's application folder.

Search discovery and Jev matching retain their current behavior. Saving a role does not start packet work. Clue does not submit applications or send outreach.

## Milestones

### M1 — Reduce global navigation and home-page noise — complete

- Keep the primary navigation to Find jobs, Search history, Saved roles, and Applications.
- Move profile/evidence, applied/hidden/outcomes, company/source controls, settings, and privacy into a compact secondary navigation disclosure; automatically reveal it when one of its pages is active.
- Remove decorative home artwork, duplicate workspace metrics, and the source inventory from the main landing view.
- Preserve CV upload/replacement, consent, first/repeat search, latest results, and links to edit search preferences.

**Acceptance:** all existing destinations remain reachable; the active secondary destination is visible and announced; home still supports first upload and repeat search.

### M2 — Make search and results progressive — complete

- Keep role, work-from location, workplace style, and local city visible as the core search controls.
- Put sponsorship, employment type, recency, uncertain-location/reviewed toggles, must/nice-have terms, salary, and Jev weights in a closed-by-default **Advanced filters** disclosure.
- Replace six always-visible assessment tabs with one labelled view selector that preserves counts and the current view.
- Keep source coverage collapsed after completion, remove duplicate notices, and retain all original listing/evidence links and pagination.

**Acceptance:** closed advanced controls retain their values and are submitted; the selector preserves all six views and their counts; no result status or evidence is removed.

### M3 — Make packet generation and review obvious — complete

- Use **Generate packet** on eligible listings in results, search history, and saved roles.
- Explain that the action researches one selected job and prepares files for owner review; keep CV selection available and place the optional public application URL behind a disclosure.
- Provide an obvious route from an empty Applications page to a role list.
- On each dossier, prioritize current files, packet status, and the next required owner action. Collapse detailed snapshot metadata, technical diagnostics, research evidence, form-field inventory, older revisions, and optional feedback/practice unless the owner opens them.
- Keep Jev review warnings, source evidence, claim-support results, contact suppression, packet approval, and manual-submission boundaries visible when they affect a decision.

**Acceptance:** the same explicit action appears wherever an eligible job can start generation; review/approval safety checks remain in the first relevant view; secondary evidence remains available in the same application folder.

### M4 — Validate and record the shipped behavior — complete locally

- Update the UX review, product documentation index, roadmap, and this plan/decision record.
- Run relevant template/route tests, the full suite if practical, Ruff, Python byte-compilation, and whitespace checks.
- Inspect desktop and narrow layouts in the local app using synthetic data; check navigation, packet-generation visibility, focus, and overflow.
- Commit on a feature branch and merge through a pull request after validation.

**Acceptance:** implementation evidence and any limitations are recorded here; all required checks pass before merge.

## Design constraints

- Reuse FastAPI, Jinja, semantic HTML, native controls, and the existing CSS system.
- Preserve the ink/teal/lime/paper palette, keyboard focus, and mobile behavior.
- Simplify the default view by progressive disclosure, not by removing capabilities or changing workflow automation.
- Keep each packet start as a deliberate manual action for one listing.

## Evaluation evidence

| Measure | Before | Target |
|---|---:|---:|
| Always-visible primary destinations | 14 links | 4 destinations plus one secondary disclosure |
| Search view groups | 3 expanded panels | 1 concise core panel plus Advanced filters |
| Always-visible result assessment views | 6 links | 1 selector with the same 6 views |
| Packet-generation label consistency | Prepare application / Prepare for review | Generate packet |
| Application-folder decision path | Long dossier before current packet review | Current files and required owner action first |

## Implementation and validation record

- **M1:** Four primary links remain visible. All secondary destinations are grouped under **More**, which opens automatically on secondary pages. Home keeps upload, consent, search, preference-edit, and latest-search paths while removing decorative art, repeated counts, and the source inventory.
- **M2:** Core search fields stay open and the remaining filters are in closed-by-default **Advanced filters**. Results use a labeled view selector with all six original choices/counts; search coverage and Jev/usage metrics share one collapsed details panel, with repeated snapshot/count lines removed.
- **M3:** Eligible result, history, and saved-role actions consistently say **Generate packet**. The selected CV and optional employer URL remain available. Applications opens with current files and owner decisions first; supporting evidence remains in disclosures.
- **Automated validation:** `371 passed, 1 warning` in the full pytest suite; `ruff check clue_ai tests`, `python -m compileall -q clue_ai`, and `git diff --check` passed. The remaining warning is upstream: Starlette's TestClient imports AnyIO's deprecated `BlockingPortal` alias.
- **Browser validation:** FastAPI pages rendered in headless Chromium from a temporary database containing one synthetic AI Engineer listing, synthetic CV, and synthetic approved claim. Jev/OpenAI keys were empty; no crawler, live profile, or external service was used. At 1440, 390, and 320 CSS pixels, there was no horizontal overflow; the packet button was visible, enabled, and within the viewport. Four primary links appeared, Advanced filters stayed collapsed by default, and the home search action was present. Keyboard traversal reached the skip link and **Generate packet**; the action showed a 3px focus outline.
- **Delivery:** Changes are on `codex/lean-task-first-ui` in [PR #8](https://github.com/jmsb505/clue-ai/pull/8).
