# ADR 0012 — Entry-level paid job criteria

**Status:** Accepted
**Date:** 2026-10-02
**Related:** [ADR 0010](0010-full-candidate-jev-assessment.md), [PLAN-011](../plans/PLAN-011-entry-level-paid-role-filters.md)

## Context

The owner clarified the target search population: junior roles and internships, with paid compensation required. The owner also needs a direct listing link for every surfaced position. Existing criteria do not represent seniority or paid status, and source links are currently shown only as small publisher links in the result footer.

ADR 0010 requires Jev to assess the complete active candidate set and retain matches, conflicts, unknowns, and unassessed listings. These new requirements therefore must not become pre-Jev retrieval filters that silently remove candidates.

## Decision

1. Every new search includes fixed `junior_or_intern` seniority and `paid_only` compensation criteria. These are product requirements, not client-editable checkboxes.
2. Jev assesses role level from the posting's title and responsibilities. Explicit junior/entry-level positions and internships are in scope. Explicit mid-level or senior-level roles conflict. Ambiguous seniority is `review`.
3. Paid means stated monetary compensation, such as salary, wages, a paid internship stipend, commission, or other explicit paid compensation. Equity-only compensation does not satisfy this requirement. Explicit unpaid or volunteer work conflicts. If the listing does not establish whether it is paid, Jev returns `review`; it must not claim the role matches the paid requirement. The optional minimum-salary unknown setting never changes this paid-only decision.
4. Keep every active, non-hidden candidate in the saved run regardless of these outcomes. Preserve ADR 0010's distinction between match, review, conflict, and unassessed.
5. Show an obvious external action for the specific job posting URL stored for each source observation. Keep publisher attribution and link-safety attributes. Never substitute a generic publisher homepage for a missing job URL.
6. Version the changed Jev assessment rubric as `fit-v1.2.0`. Keep existing saved run criteria and assessments as historical snapshots; do not silently rescore them under the new rules.

## Consequences

- Entry-level and pay requirements become part of the saved search state sent to Jev.
- Listings without pay or seniority evidence remain available for the owner's manual review and do not count as confirmed filter matches.
- New searches use the versioned filter rubric; earlier saved runs keep the criteria and decisions that were actually used.
- Result cards make the source posting easier to open directly. The source publisher remains the authority on whether the listing is still available.
- No database migration is needed because criteria are stored as JSON and the new fields have defaults.

## Alternatives considered

- **Remove listings with unclear level or pay before Jev:** Rejected because it violates ADR 0010 and can hide useful leads without evidence.
- **Treat omitted pay as paid:** Rejected because the owner explicitly requires paid jobs and an absent compensation statement does not establish that requirement.
- **Treat omitted pay as unpaid:** Rejected because absence of evidence is not proof of unpaid work; `review` preserves uncertainty.
- **Keep the existing unobtrusive source trail as the only route to the listing:** Rejected because the owner asked for a clear listing link for the positions.

## Evidence

- Current `SearchCriteria` has no career-level or paid-only fields; `job_sources.source_url` stores source-specific posting links.
- [PLAN-011](../plans/PLAN-011-entry-level-paid-role-filters.md) defines the implementation and validation checkpoint.
