# ADR 0017 — AI engineering screening before Jev

Status: Accepted under the owner's 2026-10-03 request

## Context

The owner reports irrelevant jobs and unnecessary Jev spend. They explicitly request AI engineering and derived technical roles, junior/intern and paid, with local filtering before Jev. This replaces the earlier request to assess every active listing and treat AI only as a preference.

The attached CV and public portfolio support agent/LLM applications, model development, computer vision, and inference/deployment. Past reporting/analyst work is experience evidence, not the desired search target. Reviewed public references: [SmartOps-Agents](https://github.com/jmsb505/SmartOps-Agents), [FPGA_Inference](https://github.com/jmsb505/FPGA_Inference), [CNN2FPGA](https://github.com/jmsb505/CNN2FPGA), [nlp-polimillionaire](https://github.com/jmsb505/nlp-polimillionaire). Do not publish the CV or private repository contents.

## Decision

Use one deterministic local gate for normalized source/company ingestion, cached candidate selection and scoring retries. Accept direct technical AI/ML titles, data scientists (Jev verifies model-building scope), and adjacent technical roles with actual AI/model implementation evidence. Reject explicit senior titles without entry-level alternatives, explicit unpaid work and unrelated/non-engineering titles. Missing pay or level stays eligible for Jev. Do not require every CV skill or an exact requested title. Company name, company introduction or generic AI marketing cannot establish role relevance.

Report local exclusion counts/reasons separately from deduplications. A local rejection is not a Jev rating. Preserve cached records and historic results; new runs use the focused policy and old-run scoring retries skip out-of-focus candidates without inventing scores. Applied suppression remains in force.

Discovery titles omit unrelated CV prose/past job titles and include AI, machine learning, LLM and MLOps engineering alternatives. Himalayas queries alternatives separately within the existing 25-page total daily refresh budget rather than treating a comma-separated title list as one query. Publisher/source limits remain unchanged. AI-focused company ranking omits generic analytics/data-engineering signals derived solely from past SQL/BI work.

Default Jev weights: AI 50, role 25, skills 15, experience 5, preferences 5. Migrate former standard defaults, preserve custom values, and version revised fit instructions as `fit-v1.5.0`. No extra model call or service is introduced.

## Consequences and limitations

This is an inexpensive relevance heuristic, not proof of candidate fit or complete recall. Unusual sparse adjacent titles can be missed; direct AI technical titles and model-building titles remain permissive. Admitted jobs can still conflict on location/seniority/pay; Jev retains these checks. A smaller shortlist is not a confirmed match count. Existing scores are not recalculated automatically, and no paid run is started as part of implementation. No schema migration or local personal-data change is required. Rollback restores the previous selection behavior and retains the index/history/application state.

Supersedes ADR 0010's all-listings selection and ADR 0013's optional AI-only preference. Existing geography, application tracking, source boundaries and monthly spend decisions continue to apply.
