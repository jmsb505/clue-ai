# ADR 0010 — Jev assesses the full candidate set

**Status:** Accepted
**Date:** 2026-10-02
**Supersedes:** The live-search rule “after hard filters” in the Jev section of the Product Definition and the eligible-only scoring flow in ADR 0006. ADR 0006's $4 rolling budget, consent, minimization, and no-fallback rules remain in force.

## Context

The owner requires Jev to evaluate every collected listing against the candidate profile and current search criteria. In the observed local database, a completed crawl parsed 437 listing records, while deterministic filters saved only two per-run results for Jev. The same two job identities appeared in all eight saved runs. The current Jev request also omits several filters and listing fields, so those two scores do not demonstrate that Jev assessed all collected jobs against the intended search.

Automatic deduplication also falls back to a fingerprint composed of title, company, location, and posted date. When dates are absent, distinct openings can share the same fingerprint and be merged before assessment.

## Decision

1. After source refresh and the existing expiry cleanup, each run snapshots every active, non-hidden indexed listing. User role, location, workplace, employment, salary, sponsorship, freshness, and skill criteria do not discard a listing before Jev.
2. Each Jev batch receives minimized candidate facts, the complete current search criteria, and each listing's relevant location, workplace, employment, salary, sponsorship, and date facts.
3. Jev returns the existing weighted candidate-fit dimensions and a separate structured search-filter compatibility status: `match`, `review`, or `conflict`. Missing or ambiguous evidence maps to `review`, not a false rejection. If Jev cannot assess a candidate, use `unassessed` and retain the listing.
4. Every candidate stays available in its run. Sort and filter by Jev status and fit for convenience, but do not remove conflicts, uncertain items, or budget-skipped items from the run.
5. Preserve the one-time Jev consent, contact redaction, one model, zero automatic retries, and $4 rolling app reserve under the owner's $5/month ceiling. If a batch cannot be reserved or evaluated, label affected listings and leave them visible.
6. Merge only when canonical URL or the same source's stable external ID identifies the same posting. Keep fuzzy fingerprint similarity for display or review only; do not use it to discard a listing.
7. Treat all listing/profile/criteria text as untrusted content. Jev may assess stated work-location evidence but must not infer citizenship, work authorization, or hiring probability.

## Consequences

- Results now represent all current indexed candidates, not only prefiltered matches. The interface must separate total candidates from Jev-scored, filter-match, review, conflict, and unassessed counts.
- More candidates create more requests and longer runs; the existing batching, progress reporting, and budget ledger stay authoritative.
- Fuzzy duplicate merges already present in the local SQLite index cannot be split reliably without source records. New source observations will stop making fingerprint-only merges.
- A Jev filter label is evidence for the user's review, not a legal determination or proof that an employer is still hiring.

## Alternatives considered

- **Keep hard filters and only score matching rows:** Rejected because it repeats the observed gap and makes Jev unable to assess listings excluded by ordinary string/location logic.
- **Score all, then delete filter conflicts from results:** Rejected because the owner asked Jev to assess all listings; conflicts and uncertainty must remain inspectable.
- **Merge all similar title/company/location/date records:** Rejected because similarity is not stable identity, especially when posting dates are absent.
- **Add a separate paid ranking service or raise the app cap:** Rejected under the existing owner budget and single-model decision.

## Evidence

- TypeSafe System One accepts a structured state and a map of typed questions; questions using the same state can be evaluated together. The existing five-listing batch can carry the fit and filter assessments. See the official [Python SDK](https://github.com/typesafe-ai/typesafe-sdk-python) and [System One API](https://docs.typesafe.ai/api).
- Implementation sequencing and validation: [PLAN-009](../plans/PLAN-009-full-candidate-jev-assessment.md).
