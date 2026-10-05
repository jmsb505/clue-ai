# ADR 0015 — Explicit geography and categorical Jev decisions

**Status:** Accepted; EMEA-only Italy eligibility is superseded in part by ADR 0022
**Date:** 2026-10-03
**Related:** [PLAN-015](../plans/PLAN-015-geography-and-jev-decisions.md), [ADR 0014](0014-practical-matching-and-clean-slate.md)

## Evidence

The owner's saved 908-listing run had zero aggregate matches although Jev returned four complete sets of supported checks. The application's uncalibrated 0.80 threshold downgraded all 440 additional-requirements matches to review. It also downgraded 373 location conflicts. Airtm's AI Automation Engineer had structured location LATAM but was shown as an opportunity for Italy because the parser lacked region membership and Jev returned review.

## Decision

1. Remove the numeric decision cutoff. Preserve valid categorical Jev answers, including low-confidence conflicts. Display confidence as model uncertainty rather than a calibrated eligibility probability. Missing checks stay unassessed; model review stays review; malformed/nonfinite confidence stays review. Missing pay evidence is not converted to paid work.
2. Keep fit rubric `fit-v1.4.0` because prompts and weighted fit dimensions are unchanged. Version the local interpretation separately as `filters-v1.5.0` on each requirement check.
3. Resolve explicit structured work-region labels and explicit remote-only/residency restrictions against bounded target-country membership. Recognize Europe, EU/EEA, EMEA, LATAM, North/South America, APAC, Asia, Africa, Middle East and worldwide, including alternatives. Unknown geography needs verification. Ignore headquarters/customers and timezone preferences as region restrictions. Check explicit wording throughout the bounded stored description. ADR 0022 narrows EMEA-only evidence for the default Italy profile to `needs_verification` unless Italy is explicitly named.
4. An explicit incompatible work region overrides an existing Jev location match/review to conflict after Jev assessment. Preserve `model_status`, confidence and model identity, and attribute the override to `listing_work_region` with source text. Never fabricate missing model answers or convert a location ambiguity into a match.
5. Preserve Jobicy's remote feed fact when its description omits workplace wording.
6. Repair the affected completed `fit-v1.4.0` saved results from retained answers with backup and a single transaction; record previous effective status, local policy and correction notice. Keep raw model answers, scores, ranking weights, profile, sources and spend. No paid request is made. Repair is idempotent and rejects active searches. Older composite results cannot be reconstructed and remain unchanged.

## Limits

All-supported filters do not establish strong candidate fit or live vacancy availability. This repair recovers four model-supported listings, two AI-related, with modest fit signals. The corrected corpus still includes useful review leads and many senior/location conflicts. Model quality, missing job facts and source breadth remain separate concerns; counting every scraped listing does not establish a suitable junior paid vacancy.
