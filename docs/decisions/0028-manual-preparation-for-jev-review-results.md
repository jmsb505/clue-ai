# ADR 0028 — Manual preparation for Jev review results

- Status: Accepted — bounded real-data pilot completed with explicit limits recorded
- Date: 2026-10-07
- Related: [ADR 0023](0023-application-preparation-and-action-boundaries.md), [ADR 0025](0025-jev-approval-of-tailored-resume.md), [ADR 0026](0026-jev-categorical-evidence-support.md), [PLAN-020](../plans/PLAN-020-end-to-end-evaluation-and-grounding.md)

## Context

The selected pilot listing had a scored Jev `review` result with verified eligible location and unresolved pay/language checks. It had no observed explicit AI-use prohibition. Clue therefore retained Jev's `review` label and used the individual **Prepare for review** action without changing the saved result.

Requiring `match` for any dossier made the owner-triggered pilot impossible, even though Clue distinguishes unresolved evidence from explicit conflict. Rewriting Jev's label would undermine the matching authority and hide the uncertainty the product should expose.

The first manually triggered run also exposed two independent execution gaps: the third-party aggregator page rejected the bounded crawler, and the Rewriter stopped after consuming exactly its 3,600-token output allowance. All five OpenAI receipts settled ($0.0127501 total); no packet was produced and no Jev claim-support or final-resume call ran. The original Jev result remained unchanged. The report and local ledger made both causes observable.

A second trigger for that same listing included a validated public employer-page URL. The aggregator still rejected the crawl, but the employer job page was fetched and saved successfully. Research completed; the Diagnoser then stopped at exactly its 1,600-token allowance. Its five OpenAI receipts settled at `$0.0032318`, bringing this listing's cumulative OpenAI usage to `$0.0159819` with no open or unknown reserve. No claim-support or final-resume Jev call ran, no packet or artifact was produced, and the original Jev result remained unchanged.

A third trigger passed Researcher, Diagnoser, and Recruiter, then Rewriter stopped at exactly its 7,000-token allowance. All five receipts settled at `$0.0151293`; cumulative usage for the listing reached `$0.0311112`, with no open or unknown reserve. The original Jev result stayed unchanged and no packet was produced. A subsequent retry initially failed locally, before any API call, because this installation retained a legacy two-column SQLite unique constraint. ADR 0029 records the migration and retry fix.

After that database fix, a fourth run completed Researcher, Diagnoser, and Recruiter but again reached Rewriter's 5,000-token allowance despite removing the redundant line-order array and limiting edits. The API's output allowance includes reasoning tokens, so this exact-limit result does not show how much structured text was returned. All six receipts settled at `$0.0146512`; cumulative usage reached `$0.0457624`. No Jev grounding call or packet was reached. OpenAI's model documentation lists 128,000 maximum output tokens for GPT-6 Luna, so the next bounded test uses a 16,000-token Clue-side Rewriter allowance.

## Decision

Allow one deliberate per-listing preparation trigger for either:

- a completed, scored Jev `match` with `eligible` location status; or
- a completed, scored Jev `review` with `eligible` location status.

The second action is labeled **Prepare for review**. The original Jev status and dimension evidence are copied into the immutable preparation snapshot and remain unchanged. The search card and dossier state plainly that Jev did not confirm a match and list the unresolved filter checks. The dossier also displays relevant listing facts, including when pay is not stated, so the owner can verify them at the original posting.

The owner may add an optional direct public employer job-page URL to the same individual trigger. Clue validates it as a public HTTPS URL, binds it into the snapshot hash, shows it in the dossier, and makes it available to the Researcher crawler. When that link and an aggregator are both present, the Researcher prefers the employer page. It receives no profile or CV and cannot open or submit application forms. Based on measured output-limit failures, set Diagnoser's allowance to 2,800, Recruiter's to 9,000, and Rewriter's to 16,000 tokens, below the documented GPT-6 Luna 128,000-token maximum. Limit Diagnoser to eight concrete findings and Rewriter to eight high-value bullet edits. In preserve mode, the Rewriter returns no redundant line-order list; the local renderer retains the exact source order. Store per-stage output allowances in the generation-policy snapshot so a later owner-triggered run after a budget change creates a new auditable request. Surface a specific safe status when a stage reaches its output allowance. Keep `reasoning.effort=high`.

For this bounded pilot, raise Clue's local monthly and per-opportunity ceilings from `$0.10` to `$0.15` after the previous limits blocked the conservative reservation for a final same-listing run. This is a Clue-local budget change; no OpenAI or Jev account settings or caps are changed. The ledger remains separate, reserves before each provider call, and reports actual/reserved/unknown usage independently.

Explicit `conflict`, `unassessed`, `not_eligible`, `needs_verification`, or `unknown` location states stay blocked. Preparation remains individually triggered; discovery, ranking, refresh, or batch selection never starts generation. The independent Jev factual-support checks and final explicit tailored-resume approval remain mandatory. Resume approval does not alter the original match decision or resolve unrelated listing questions.

Do not run the AI-assisted workflow for a listing that explicitly prohibits AI use in application materials. Check the employer's current listing before the trigger.

## Consequences

- A carefully bounded `review` case can produce a useful dossier without presenting it as a confirmed fit.
- Unresolved criteria remain visible to the owner rather than being silently waived.
- Requiring verified location eligibility and blocking any overall conflict preserves explicit location and hard-filter constraints.
- Supplying an official page gives bounded research a primary source even when a job-board aggregator blocks the crawler.
- The Diagnoser, Recruiter, and Rewriter allowances, compact schemas, 16,000-token Rewriter ceiling, and Clue-local caps are measured responses to one bounded listing. The final `.12` run passed Jev claim support for both cover-letter paragraphs, final CV approval, packet quality, usage settlement, and visual rendering. It had zero CV bullet edits and no verified outreach contact. A `.13` transfer-wording experiment failed Jev support and was rolled back; the successful `.12` output still needs owner style review.
- Failed snapshots remain retryable on compatible databases after migration; the legacy unique index and optional employer URL handling are covered by regression tests.
- Jev remains the sole job-matching authority; no score threshold or generation output can change its saved result.
- The UI and tests cover the `review` label, unresolved criteria, location gate, and unchanged saved match state.

## Validation

Offline tests show that only eligible `match` and `review` results can create requests; conflict, unassessed, and ineligible or unverified location states are rejected; a valid employer URL is snapshot-bound; and unsafe URLs are rejected. A full fake-provider review-path test reaches separate final Jev resume approval while leaving the saved Jev filter state unchanged. PLAN-020 records the live pilot, document render, all settled usage receipts, and the remaining owner-review/calibration limits; it does not establish personal-fit calibration or a hiring outcome.
