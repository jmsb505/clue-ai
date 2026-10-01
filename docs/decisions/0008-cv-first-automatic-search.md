# ADR 0008: CV-first automatic search and Jev review

**Status:** ACCEPTED and implemented in PLAN-004 M1
**Date:** 2026-10-01
**Supersedes:** The pre-save profile correction in ADR 0005 and the per-search Jev action in ADR 0006 for triggering the workflow. The Jev rubric, language gate, request limit, and local budget guard remain in force.

## Context

The original interface split CV upload, profile review/save, search setup, and Jev scoring across separate pages and actions. That is not the intended personal workflow. The owner wants to upload a CV, have Clue parse it locally, search immediately, and use Jev to evaluate the resulting matches. The user does not want automated applications.

## Decision

- A PDF/DOCX upload from Home is parsed locally, saved with an editable candidate profile, and immediately starts a search run. The user does not have to visit the profile editor or search form first.
- The parser extracts known CV sections, conservatively derives likely target roles from explicit target-role headings or position lines, and guesses English/Italian only when the text provides sufficient evidence. Ambiguous fields remain empty or `unknown`; the profile editor remains available.
- A first search uses inferred roles, remote work, and Italy. Later upload and repeat searches reuse the most recently saved search preferences; the user can change them from Search preferences.
- Existing approved sources, refresh schedules, hard filters, deduplication, result history, and provenance remain unchanged. A new search does not launch an unbounded crawl.
- After filtering, Clue automatically invokes the existing Jev path for searches. Jev makes no request unless the user has saved the one-time in-app opt-in, a key is configured, the profile/listing language is supported, and the app-side rolling reserve permits it.
- The Jev request includes bounded parsed job-related profile fields and selected listing details. It excludes the original CV, direct contacts, work authorization, and source URLs. A gate or service failure leaves the listings visible with an unscored reason.
- The settings page can revoke automatic Jev consent. The separate profile editor and advanced search preferences remain available after the first search.
- X discovery is not part of this workflow and is deferred from its primary navigation. This ADR does not change the existing manual X route or create X requests.
- Clue never applies for the user. Results link to the original listing for the user to review.

## Consequences

- Upload is the primary action and repeat searches can use the saved profile without choosing a file again.
- Role and language inference varies with CV layout. Weak inferences are visible/editable and cannot silently become an unsupported Jev score.
- The one-time Jev opt-in is required because parsed work history and listing content leave the device when the Jev gates pass. The API key and app-side budget reserve remain additional gates.
- Search still returns results if Jev is disabled, unavailable, over budget, or unable to evaluate a language pair.
- No new runtime dependency or database migration is needed.

## Validation

PLAN-004 M1 uses synthetic PDF/DOCX data, mocked job sources, and a mocked Jev client. It covers local CV persistence, inferred fields and first-run defaults, automatic scoring with opt-in/key, no-call behavior without opt-in, repeated searches with saved preferences, and rendered results. No real CV, listing source, or Jev request is required for implementation validation.

## References

- [PLAN-004: CV-first automated search and Jev validation](../plans/PLAN-004-cv-first-automated-search.md)
- [Product definition](../product-definition.md)
- [ADR 0006: Typed Jev fit scoring with a conservative local spend reserve](0006-jev-scoring-and-budget-guard.md)
