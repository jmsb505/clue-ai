# ADR 0013 — AI-domain-weighted Jev ranking

**Status:** Accepted
**Date:** 2026-10-02
**Supersedes:** The four-fit-dimension requirement in ADR 0006. ADR 0006's data-minimization, consent, retry, model, and $4 app-reserve rules remain in force.
**Related:** [ADR 0010](0010-full-candidate-jev-assessment.md), [ADR 0012](0012-entry-level-paid-job-criteria.md), [PLAN-012](../plans/PLAN-012-ai-domain-weighted-ranking.md)

## Context

The owner wants AI/ML-related openings prioritized, while also seeing other roles the candidate can reasonably apply to based on their profile. Treating AI as a hard filter would hide relevant adjacent opportunities and conflict with the full-candidate retention rule in ADR 0010. Folding domain relevance into role alignment would also make the signal and its influence hard to inspect.

## Decision

1. Add an independent `ai_relevance` Jev fit dimension. Assess the role responsibilities and explicit product/work context in the listing: `4` when AI/ML work is central; `3` when the role directly builds, evaluates, deploys, or supports AI/ML systems or products; `2` when AI/ML work is a meaningful adjacent part; `1` when the role is broadly transferable but has little direct AI/ML evidence; `0` only when the listing clearly establishes an unrelated role; and `unknown` when evidence is insufficient. Do not infer domain fit from a company name or generic AI claim alone.
2. Use these default weights: AI/ML relevance `35`, role alignment `25`, skills `25`, experience `10`, and preferences `5`. The application combines the independently assessed dimensions locally. These are relative fit signals, not probabilities of hiring.
3. Treat AI/ML relevance as a weighted preference, never a pre-Jev filter. Keep all retained listings, including profile-fit jobs outside AI, and leave explicit hard-filter status, uncertainty, and source eligibility rules unchanged.
4. Preserve the existing saved dimensions and weights for explicit user customizations. When loading a pre-ADR-0013 saved search that has only the former default weights, transition its next scoring/search-form view to the new AI-focused defaults. If it has custom legacy weights, retain them and give AI relevance the next-highest default share where the 0–100 input range allows.
5. An unknown AI relevance answer is omitted from the weighted denominator; it is not a negative score. Keep the assessment confidence and evidence status visible.
6. Version the fit rubric as `fit-v1.3.0`. Do not silently rescore completed historical results. A later manual retry of unscored listings uses the current rubric and must remain visibly versioned.
7. Keep the app-side `$4` rolling reserve and one-request-per-batch behavior. The extra Jev question increases payload size and may increase per-listing cost; no live TypeSafe request or crawl is part of implementing this change.

## Consequences

- AI/ML domain relevance is visible beside role, skills, experience, and optional-preference scores.
- AI roles should rise when their listing evidence supports the domain score, while non-AI roles can still rank well from strong candidate fit.
- Evidence-poor listings are not penalized as unrelated; the domain score remains unknown and the remaining assessed dimensions are normalized over their applicable weights.
- The fifth fit question adds request content. Existing reserve, monthly app-side limit, TypeSafe consent, and non-TypeSafe `$0` cost constraints continue to apply.
- New assessments use rubric `fit-v1.3.0`; completed stored rankings remain unchanged.

## Alternatives considered

- **Hard-filter to AI/ML jobs:** Rejected because it would remove useful matches outside AI before full Jev assessment.
- **Blend AI relevance into role alignment:** Rejected because the user cannot inspect or adjust the domain preference independently.
- **Treat missing AI evidence as unrelated:** Rejected because missing listing detail is uncertainty, not contradictory evidence.
- **Replace Jev with a keyword search or another model:** Rejected; Jev remains the fit evaluator, and keyword evidence alone is not a reliable domain judgment.

## Evidence

- The full candidate set is retained by [ADR 0010](0010-full-candidate-jev-assessment.md).
- The scoring and UI implementation, compatibility behavior, and static validation are recorded in [PLAN-012](../plans/PLAN-012-ai-domain-weighted-ranking.md).
