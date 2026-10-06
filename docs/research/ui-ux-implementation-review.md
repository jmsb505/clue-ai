# UI/UX implementation review

**Reviewed:** 2026-10-01
**Decision scope:** First single-user local search/review interface

## Product fit

The main job of the interface is to help one person move from CV review to a current, evidence-backed list of jobs they can inspect. It should feel welcoming and direct like Jobbie's job-discovery experience, while making this product's source coverage, Italy eligibility, freshness, Jev status, and uncertainty unusually easy to understand. The interface does not apply for the user.

## UI foundation candidates

| Candidate | Evaluation | Decision |
|---|---|---|
| FastAPI + Jinja templates + semantic HTML/native controls + project-owned CSS/vanilla JS | Fits the Python ingestion runtime and local-only deployment. No remote design service, no Node build, small dependency footprint, direct control over the visual identity. Native forms and links provide familiar keyboard behavior; all custom interactions still need focus, zoom, screen-reader, and reduced-motion review. | **ADOPT.** |
| React component foundation such as shadcn/ui, Mantine, or Radix | Strong component/accessibility options, but introduces a second build/runtime path and more dependencies for a single-user local UI. Would require shaping the library defaults into the product's own identity. | **DEFER.** Revisit only if UI complexity or validated usability requires reusable interactive widgets. |
| Copy Jobbie's exact UI or use its brand/components | Jobbie is useful product context for friendly task-first search, but its private implementation is not needed and a direct copy would erase this product's source-evidence focus. | **REJECT.** Adapt the clear search and review flow; use original copy and visual design. |

## Interaction model

- First run starts with a CV upload. Clue parses and saves the profile locally, then begins searching; editable profile fields remain available afterward.
- Search controls separate what role/work the person wants and where they want to work. Work-authorized countries are stored as local reference; the app does not make a legal eligibility determination from them.
- A CV upload or repeat-search action starts a visible background search for entries that are due, then automatically checks eligible results with Jev when the one-time opt-in, key, language, and app-budget gates pass. Results remain visible with a clear reason when Jev is unavailable.
- Results expose source, original link, posted date/last checked, Italy-eligibility evidence, missing information, Jev status/confidence, and save/hide actions.
- A missing key, exhausted rolling 30-day reserve, denied source, empty feed, stale result, and failed parser each have a concrete next step; existing results remain available.
- Only source links open externally. The product never fills or submits an application.
- Deleting the local profile and job data requires a clear confirmation and removes data from SQLite and the stored CV.

## Visual plan

- **Palette:** midnight ink `#142326`, mineral teal `#147B71`, sharp citron `#D9EF68`, clean mist `#F1F5F3`, paper white `#FFFFFF`, and rust `#B5523B` for warnings.
- **Type:** platform UI sans for controls and body, a restrained system serif for section headlines, and monospaced utility text for timestamps/source IDs; no remote font requests.
- **Layout:** narrow dark navigation rail on wide screens, a light content canvas with search controls at the top, and a readable single-column stream of job cards; collapse navigation and filters into the document flow on mobile.
- **Signature:** a compact “source trail” along each result, visually tying its fit signal to the source checked, recency, and exact location evidence. It is informational, not decorative.
- **Motion:** short opacity/height changes only for opening filters and status updates; respect `prefers-reduced-motion` and do not hide essential content behind animation.

## Validation requirements

- Keyboard-only traversal through upload, profile edits, search filters, results, save/hide, sources, and deletion confirmation; visible focus at each stop.
- Responsive layout at narrow phone widths and desktop widths without horizontal page scrolling. The owner waived the 200% zoom check on 2026-09-30.
- Semantic headings, labels, form validation associations, status announcements, link names, and adequate contrast; aim for WCAG 2.2 AA.
- Loading, no sources, no matches, unscored, stale, source blocked, invalid CV, key missing, spend limit, and retryable network-error states.
- Reduced-motion preference; no remote font, image, tracker, or component dependency in the product UI.

## Implementation state

The FastAPI/Jinja interface has a CV-first upload-to-search path, an editable profile, search criteria and weights, ranked results, saved/hidden listings, source controls, settings, and privacy/deletion views. PLAN-004 M1 verifies upload, local parsing/persistence, immediate search startup, saved-preference reuse, automatic Jev behavior, and consent/key gates with synthetic CVs and mocked source/model responses. No real CV or live source/API call is used in those tests. Earlier browser accessibility-tree and keyboard-focus reviews covered onboarding, profile, search, synthetic results, and settings. Named navigation, current-page state, labeled form controls, descriptive Save/Hide actions, skip navigation, and visible focus were observed. The results poller runs only while a search is active. Reduced motion disables transitions/animations; layouts had no horizontal page overflow at 320px, 640px, or 651px. The owner waived the 200% zoom check. Actual spoken output was not verified because this browser session exposes the accessibility tree but has no system screen-reader playback control.

PLAN-003 adds an X-lead page in the existing Jinja/CSS system with labeled role/location controls, explicit external-link actions, a manual verification checklist, and a separate lead form. M1 route tests cover navigation and the link/import flow. The page does not automatically open X or a submitted job URL; a separate visual or spoken screen-reader review has not been recorded for this page.

## Application workspaces — 2026-10-06

**Purpose:** Keep each prepared role's files, contact evidence, email draft, and owner-recorded progress together without requiring Google authorization.

| Candidate | Product fit, accessibility, and maintenance | Decision |
|---|---|---|
| Reuse FastAPI/Jinja, native section links and forms, existing local packet records, and project CSS | Matches the single-user local product, keeps packet identity and file ownership unchanged, and avoids new services or UI dependencies. Native links/forms work with a keyboard; copy/download enhancements still need clear status feedback and narrow-layout checks. | **ADAPT.** Add an Applications index and a dossier route per existing preparation request. Group immutable packet revisions and receipts, then add a local copy-and-download email handoff. |
| Add a separate application CRM/database or cloud file store | Would duplicate the existing applied tracker or move personal packets outside local storage. No need for a second source of truth has been established. | **REJECT.** Keep the existing request ID and SQLite/file records as the dossier identity. |
| Require Gmail OAuth to prepare an outreach email | Adds a Google project and restricted-scope consent even though the owner only needs to review, copy, and send the message manually. | **REJECT as the default.** Keep the existing Gmail draft adapter optional; no Google setup is needed for the dossier or local handoff. |

**Layout:** The Applications index puts owner-set reminders first, followed by compact role cards with company, current preparation/application state, last update, and one clear “Open application” link. A dossier opens with the job identity and owner stage, then uses native anchors for **Overview**, **Files**, **Research**, **Outreach**, and **Progress**. File cards group the current packet first, older revisions below it, and receipts in their own row. Each email preview keeps the verified address next to its contact-source link.

**Visual direction:** Preserve the existing ink/teal/lime/paper palette and UI/body/serif/utility type roles. Use a quiet file-revision spine with explicit `Current`, `Older`, and `Receipt` labels as the page's signature. Keep motion to the existing short transitions; document sections and all essential content remain visible without animation.

**Validation:** Semantic headings, labeled links, current-page state, native section navigation, copy status live region, and selected-text fallback are present. Focused synthetic tests confirm dossier and ZIP request/packet binding; an isolated stubbed JS run confirmed copy success and fallback without touching the system clipboard. Browser review confirmed the sourced email, subject/body, attachments, and a narrow layout where horizontal scrolling stays within navigation. Existing reduced-motion behavior remains active. No remote fonts, image assets, component package, or external reference product was added.

## Full-candidate Jev results — 2026-10-02

**Purpose:** Make every collected listing Jev assessed discoverable without turning a thousand-card search into one enormous page.

| Candidate | Product fit, accessibility, and maintenance | Decision |
|---|---|---|
| Existing FastAPI/Jinja result page with status counts, native filter links, and 50-item pagination | Reuses the current route, semantic HTML, and project CSS. Link-based status tabs work by keyboard, preserve browser history, and avoid client-side state or a new dependency. Counts expose how many match, need review, conflict, or remain unassessed. | **ADAPT.** Keep the existing stack, add accessible status navigation and pagination, and label fit separately from filter compatibility. |
| Render every candidate card in one response | Simple initially, but a full local index is already over 1,100 active rows. A single page would be costly to load and difficult to navigate. | **REJECT.** Keep every result in the run but paginate it. |
| Add a React/data-table library | No existing React runtime; introduces another toolchain and visual defaults for a single-user local app. | **REJECT.** Use native links/forms and the installed Jinja/CSS stack. |

Status names and totals must remain available as text, not color alone. Keep focus visible, use a semantic `nav` with an accessible label and `aria-current`, preserve the current result card headings/links, and make pagination links identify the destination page. No animation or component dependency is needed.
