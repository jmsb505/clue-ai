# ADR 0014 — Practical matching and clean-slate searches

**Status:** Accepted; confidence cutoff and saved-correction policy superseded by [ADR 0015](0015-explicit-geography-and-jev-decisions.md)
**Date:** 2026-10-02
**Related:** [PLAN-014](../plans/PLAN-014-clean-slate-and-practical-matching.md), [ADR 0010](0010-full-candidate-jev-assessment.md), [ADR 0012](0012-entry-level-paid-job-criteria.md), [ADR 0013](0013-ai-domain-weighted-jev-ranking.md)

## Context

The owner requested a clean slate and broader matching after zero confirmed matches among 1,342 assessed listings. The composite filter question mixed job-related ranking with eligibility, and CV title inference admitted an action sentence. Unknown pay or level remains useful for discovery but cannot establish a confirmed paid junior role. A single returned status made exclusions difficult to inspect.

## Decision

1. Target role titles are alternative discovery and ranking preferences. Related roles and transferable skills stay in scope. AI relevance retains the largest individual default ranking weight; neither exact job-title wording nor AI terminology is a hard exclusion.
2. Keep the paid junior/intern focus. Graduate, trainee, associate and accessible entry-level responsibilities may establish junior scope without a literal junior title. Preferred experience affects fit. Mandatory experienced/senior scope, explicit unpaid/volunteer/equity-only work and explicit incompatible location/workplace requirements remain conflicts. Missing pay or level evidence stays review, not confirmed match.
3. Replace the composite filter question with five independent Jev checks: seniority, monetary compensation, location/authorization/sponsorship, workplace and additional requirements/availability. The same batch also contains five fit dimensions. Use existing SDK typed Choice requests, batching, redaction, consent, retry and spend controls; no extra API round trips per batch.
4. For additional requirements, equivalent must-have wording counts; missing evidence remains review. Optional employment types are alternatives. Posting age beyond the requested window remains review unless closure or expiry is established; an old date alone does not prove the vacancy is closed. Explicit unknown exclusions and comparable salary floors remain requirements. Candidate skills and nice-to-have terms are not hard requirements.
5. Preserve each reported filter choice and confidence in the result's dimension JSON. A match/conflict decision below 0.8 model confidence becomes review. This threshold is a conservative, uncalibrated heuristic, not a probability. No incomplete set of checks can become a confirmed match. The aggregate is conflict if any complete check set contains a confident conflict, review if any check needs verification, otherwise match; missing answers remain unassessed.
6. Default the result view to Potential opportunities when any match/review results exist. Rank those two classes together by weighted candidate fit. Labels continue to distinguish confirmed filter matches from jobs needing verification. Keep All, Match, Review, Conflict and Not assessed views, source attribution and direct posting links. Empty/unassessed runs fall back to All.
7. Preserve normalized sponsorship facts and the complete bounded job description in Jev input, up to the existing 9,000-character description limit. This avoids losing pay or requirement details solely because they appear late in the description.
8. Reject action sentences when inferring CV target roles. Clean the known contaminated saved target-role list without changing the remaining profile fields.
9. `clue.ps1 reset` stops the app and crawler tree, creates an ignored local SQLite backup and atomically clears searches, results, listings, saved/hidden state, query caches and crawl timestamps. Keep profile/CV, consent/API settings, source configurations, tracked-company choices and actual Jev spend. Charges cannot be reset by deleting local results. The app remains stopped.
10. Version the new rubric as `fit-v1.4.0`. Schema stays unchanged; existing saved snapshots keep their original assessments unless the owner explicitly resets them.

## Consequences and limits

More useful but uncertain leads are visible without inventing confirmed pay or eligibility. Per-requirement decisions support diagnosis; they are model judgments, not quoted evidence or proof. Independent checks increase typed questions per listing from six to ten and may increase input-token cost within the unchanged app budget. Synthetic validation covers aggregation, input retention, persistence, ranking, pagination, rendering and reset integrity. Actual relevance on the owner's next live search remains unverified.

This decision amends ADR 0010's composite assessment and ADR 0012's interpretation of entry level. It preserves their full-candidate retention, paid-only intent and direct listing links.
