# UI/UX implementation review

**Reviewed:** 2026-09-30
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

- First run asks for a CV, then shows editable extracted profile fields before saving.
- Search controls separate what role/work the person wants and where they want to work. Work-authorized countries are stored as local reference; the app does not make a legal eligibility determination from them.
- A search starts a visible background source refresh for entries that are due, then shows the result set and which sources were checked or skipped.
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
- Responsive layout at narrow phone widths, desktop widths, and 200% zoom without horizontal page scrolling.
- Semantic headings, labels, form validation associations, status announcements, link names, and adequate contrast; aim for WCAG 2.2 AA.
- Loading, no sources, no matches, unscored, stale, source blocked, invalid CV, key missing, spend limit, and retryable network-error states.
- Reduced-motion preference; no remote font, image, tracker, or component dependency in the product UI.

## Implementation state

The FastAPI/Jinja interface has profile review, search criteria and weights, ranked results, saved/hidden listings, source controls, settings, and privacy/deletion views. Manual review confirmed visible keyboard focus on the skip link, the default Italy search input, and no page-width overflow at 320px, 640px, or 651px. The reduced-motion rule is present and disables transitions/animations. Full screen-reader review and actual browser zoom at 200% remain unverified.
