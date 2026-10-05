# ADR 0022 — Strict Europe-or-Milan location gate

- Status: Accepted
- Date: 2026-10-05
- Decision owners: Clue owner

## Context

The remote-preferred policy added the Milan exception, but location eligibility was only attached as evidence. The search pipeline still sent known out-of-region and ambiguous listings to Jev, and unknown workplace types bypassed the Milan-city check. In addition, the geography classifier treated the broad EMEA region as eligible for an Italy-based search even though EMEA includes countries outside Europe.

## Decision

1. The default `remote_preferred` profile is a strict scope before Jev and before saving run results. A remote job must have explicit evidence that work from the selected country is permitted. For the current Italy profile, explicit Italy, Europe, EU, EEA, or worldwide eligibility is accepted. Known incompatible regions are excluded.
2. Broad EMEA, timezone overlap, an unqualified remote label, or missing remote geography is unverified. It is excluded under the default profile unless the posting separately names the selected country.
3. Hybrid/on-site jobs are eligible only when the selected local city is explicit (Milan by default). An unknown workplace type is accepted only when the listing identifies that local city. Other-city and unknown-city physical roles are excluded.
4. The `include_unknown_location` option does not bypass the strict default. It remains available for broader workplace modes. Coverage reports the number of excluded listings by reason.
5. Source indexes remain intact, so future source refreshes can discover changed listings. Historical run snapshots are preserved and are not rewritten by this filtering change.

## Consequences

- Fewer irrelevant or geographically ambiguous listings enter the Jev batch and current result snapshots.
- Search coverage shows counts removed for out-of-region remote eligibility, unverified remote geography, non-Milan physical location, or missing city/workplace evidence.
- A connector that mislabels a work arrangement or location can still affect screening. The location evidence and original listing link remain visible for retained roles; the publisher is authoritative.
- Strict remote-preferred mode may omit a valid job when the publisher does not state its hiring region or work arrangement clearly. Broader workplace modes remain available when the owner intentionally wants uncertain locations included.

## Validation evidence

Static compilation, Ruff, template compilation, whitespace checks, and source-path inspection. No app session, live crawl, Jev request, or test suite during this milestone.
