# ADR 0031 — Public recruitment inboxes and draft integrity

- Status: Accepted
- Date: 2026-10-07
- Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [PLAN-019](../plans/PLAN-019-application-preparation-framework.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md)

## Context

The three-listing live evaluation found that the Researcher returned no contact for an IFOM posting that explicitly published a general application inbox. The prompt and validator required a named person's name and role, so a valid organization contact channel was discarded. The same evaluation also found that generated change summaries could describe edits that were not retained after Jev checks, and that GPT-generated document titles did not need to be trusted when Clue already had the authoritative listing title and company.

The initial IFOM packet passed Jev's final resume decision and document-quality checks, but its letter repeated abstract relevance bridges. A later prompt attempt produced a paragraph with an unapproved claim ID and another unresolved letter paragraph. Clue now omits out-of-snapshot blocks before Jev while retaining the minimum-letter gate. Prompt `.16` subsequently passed Jev support for both letter paragraphs on this listing; the CV still had no edits and the exact files have not been visually rendered.

## Decision

1. Permit the Researcher to return an organization-published general recruitment inbox in addition to named professionals. Require the exact public email to appear in both the source page and quoted evidence, require the quote to contain recruitment/application context and an action, and require the organization name to appear in the page. Clue normalizes the display label to `Recruitment team` / `General recruitment inbox`; it never presents the channel as a named person.
2. Preserve the existing public-source and owner-action boundaries. The Researcher has read-only bounded crawling only after a single-listing trigger. The address is stripped from later writing/JeV context, appears as a sourced contact in the local dossier, and may be used for an unsent draft only after the owner approves the complete packet and exact recipient/message. Clue never sends the message.
3. Derive the cover-letter title locally from the saved listing title and company. Derive the change summary from the content remaining after Jev's support check. Do not rely on generated metadata to describe changes that were omitted or to introduce unsupported role details.
4. Keep the categorical Jev support and final-resume gates unchanged. Prompt changes may improve evidence selection and voice, but an unresolved paragraph still blocks a complete letter. The active prompt is versioned at `.16` and remains subject to live evaluation; a high pass rate is not inferred from one packet.
5. Keep the Clue-local monthly OpenAI cap at `$0.30` and per-listing cap at `$0.15` for this bounded evaluation. This changes only Clue's local controls; no OpenAI or Jev provider-account setting or cap is changed.

## Consequences

- A directly published recruiting inbox can support a contact record and a candidate-reviewed draft even when no individual hiring manager is named.
- A generic inbox label cannot be misrepresented as a person, and an ordinary company info address is rejected without a source-backed application/recruitment instruction.
- Contact capture is not proof that an outreach message is appropriate; the packet remains gated by Jev and owner review.
- Deterministic titles and summaries are consistent with the saved listing and Jev-retained content.
- Across the three initial postings, only IFOM produced a review packet; two requests failed closed. Four IFOM retries produced one supported outreach draft and, on the latest `.16` attempt, one review packet with two Jev-supported letter paragraphs and an approved final CV. CV edits remained zero and later contact discovery was inconsistent. Writing quality, useful CV tailoring, exact-document visual inspection, and owner acceptance remain open.

## Validation

- Offline tests cover a valid official recruitment inbox, normalization away from a fabricated person, rejection of a general information address without recruitment context, email redaction from later model context, saved-listing title derivation, and post-Jev summary counts.
- The captured IFOM public page passed an offline replay through the new validator. Live research found the official inbox and produced one Jev-supported unsent outreach draft on a retest; subsequent attempts on the same page did not consistently recover a contact.
- Regression tests and live retries verify that unapproved evidence IDs are omitted before Jev, unresolved letter paragraphs still block artifacts, and prompt `.16` can produce a 2/2 supported letter and an explicitly approved final CV. Three initial manual triggers and four IFOM retries are recorded in the sanitized [PLAN-020 evaluation](../evaluations/PLAN-020-evaluation-results.md). No outreach or application was sent or submitted.
