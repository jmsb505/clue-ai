# PLAN-001 M3a — Synthetic Jev ranking benchmark

**Run date:** 2026-09-30
**Status:** Corrected one-batch evaluation passed; personal relevance calibration remains open

## Method

The repeatable runner is `conda run -n gen python -m clue_ai.evaluation --live`. It creates a temporary SQLite database, uses one authored synthetic candidate and eight synthetic job records, filters them locally, sends only the five expected-to-pass listings to Jev, reads the result and usage ledger, and deletes the temporary directory. It does not read the saved profile or job index in `.data/`. Without `--live`, the command makes no API request.

The synthetic profile is a mid-career data analyst with SQL, Python, dbt, and Power BI skills. Five graded examples span close analytics roles and less-aligned reporting/operations roles. Three additional examples exercise deterministic exclusions: an on-site role, a U.S.-only role, and a role missing the required Python skill. Reference grades were assigned for this constructed scenario; they are not the owner's personal relevance judgments.

The baseline counts exact matches for seven fixed role/skill phrases and sorts by that count. Jev's rubric is `fit-v1.1.0`; it evaluates role, skills, experience, and preferences. Both rankings use the app's displayed order. `nDCG@5` is reported against the fixed synthetic grades.

## Corrected run

| Measure | Result |
|---|---:|
| Candidate/job pairs sent to Jev | 5 |
| Jev requests | 1 |
| Listings scored / left unscored | 5 / 0 |
| Human-reference grade of top result | 4 / 4 |
| Jev `nDCG@5` | 1.000 |
| Exact-keyword baseline `nDCG@5` | 1.000 |
| Jev confidence range | 0.503–0.851 |
| Explicit location and must-have filters | 5 expected pass; 5 passed; 0 false pass; 0 false reject |
| Duplicate fixture detected | 1 |
| Stale indexed result labeled | 1 of 5 |
| Canonical links structurally valid | 5 of 5 |
| App-ledger cost for corrected request | `$0.000259434` |

The corrected Jev order was: Analytics Engineer (fit `0.9657`, confidence `0.8506`); Data Analyst (`0.8661`, `0.6145`); Business Intelligence Analyst (`0.7857`, `0.5272`); Customer Insights Analyst (`0.6685`, `0.5033`); Sales Operations Analyst (`0.4808`, `0.5425`, labeled stale). The keyword baseline also achieved `nDCG@5 = 1.000`, so this small constructed set shows no Jev advantage over exact phrase counts. It checks integration, deterministic exclusions, evidence plumbing, and result labeling; it does not establish personal fit calibration, broad ranking quality, or hiring probability.

Link validation checked HTTPS, host presence, credentials, and canonical URL normalization only. The benchmark URLs are synthetic; no job URL was fetched.

## Run accounting and correction history

The first exploratory run exposed two fixture defects: one excluded example repeated the required word `Python` in a negative sentence, which correctly passed the app's literal must-have matcher, and two cases used the same title, which made the evaluation key ambiguous. That run scored six records in two Jev requests and reported `$0.000324492`; its ranking is superseded by the corrected fixture.

A subsequent corrected attempt reached the Jev call but the runner tried to read its temporary ledger after deleting the temporary directory. The local command reported `OSError`, so its exact token usage was lost. The harness was changed to read all metrics before cleanup and an offline integration test now verifies that one five-listing batch is used and measured before the temporary directory is removed. The lost-ledger attempt had one 80,000-token app reservation (`$0.00336` at the configured `$0.042`/million input-token rate); that is a reservation bound under the current rate assumption, not a confirmed TypeSafe account charge.

Across the corrected run and known exploratory runs, the local ledger reports `$0.000583926` of Jev input usage, plus the lost-ledger request whose exact amount is unavailable. PLAN-002's earlier synthetic request separately reported `$0.00006611`. The aggregate TypeSafe account charge, credit conversion, taxes, other account use, and automatic-refill setting have not been checked in the account. The app's configured rolling cap is `$4.00`; the user-set `$5.00` ceiling is not proven at account level by these local ledgers.

## Current TypeSafe documentation review

Reviewed 2026-09-30:

- [Jev model documentation](https://docs.typesafe.ai/models) lists `jev-1.13.0`, `$0.042` per million input tokens, free output, a 64k-token request context, and says customer requests/responses are not used to train Jev.
- The [Python SDK response types](https://github.com/typesafe-ai/typesafe-sdk-python) expose input-token usage as optional, and the SDK retries by default. Clue sets retries to zero and retains its reservation when returned usage is missing.
- The current [Master Customer Agreement](https://typesafe.ai/legal/mca), updated 2026-09-23, makes the Order part of the agreement, permits API integration into a customer application, says input consumes credits, and makes automatic purchased-credit refill conditional on an account opt-in. It also describes telemetry processing and says customer data may remain in TypeSafe's standard backups under confidentiality terms.
- The [DPA](https://typesafe.ai/legal/data-processing), updated 2026-04-24, is incorporated into the agreement; it describes TypeSafe as processor, provides EU transfer clauses, and retains data as long as necessary for the stated purposes. The [Privacy Policy](https://typesafe.ai/legal/privacy-policy) says the services are hosted in the U.S. and input is not used to train models.

These public documents do not reveal the owner's accepted Order, current account credit rate, tax treatment, actual refill toggle, account-wide spend, or an individual deletion request outcome. TypeSafe documents zero-data retention for enterprise customers; no such option was verified for this account. No real CV or owner-derived profile was sent in these benchmark runs.
