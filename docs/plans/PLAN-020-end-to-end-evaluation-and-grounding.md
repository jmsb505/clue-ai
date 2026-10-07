# PLAN-020 — End-to-end quality evaluation and evidence grounding

Status: M1–M4 are complete. M5's three-listing exploratory evaluation and four IFOM retries are recorded. The latest IFOM packet (prompt `.16`) passed Jev claim support for both cover-letter paragraphs, final CV approval, packet quality, and usage settlement; its CV had zero bullet edits and the exact DOCX files have not been visually rendered. The packet remains in owner review. Personal voice acceptance, useful CV tailoring, and hiring outcomes remain unproven.
Created: 2026-10-06 · Last updated: 2026-10-07
Related: [PLAN-019](PLAN-019-application-preparation-framework.md), [ADR 0023](../decisions/0023-application-preparation-and-action-boundaries.md), [ADR 0025](../decisions/0025-jev-approval-of-tailored-resume.md)

## Objective

Create reproducible evidence that Clue's discovery filters, Jev matching decisions, GPT-6 Luna reasoning and writing, and generated application documents behave as intended. Keep Jev authoritative for job matching and add a separately measured Jev evidence-support check for generated candidate claims. Tune only against labeled evaluation cases, preserve manual owner approval, and cap live tests.

## Motivation

The current application workflow tests use a fake model. They verify routing, schemas, provenance IDs, and local artifact generation, but do not establish live GPT output quality. An adversarial synthetic edit claiming a 300% revenue increase and leadership of a 20-person team passed `_validate_rewrite` when attached to an unrelated valid claim ID. Prompt instructions alone therefore do not prevent unsupported content from entering a packet.

The current eight-case Jev benchmark has author-assigned synthetic relevance labels. It is useful as an integration smoke test, not as evidence of the owner's personal job-fit preferences. Evaluation must report that distinction and provide a path to owner-labeled calibration.

## Current state

- PLAN-019 implements deterministic search filters, Jev fit and eligibility assessment, GPT-6 Luna generation, local packet rendering, and manual review.
- Offline application tests use synthetic inputs and fake GPT/Gmail providers. Declared validation dependencies were made available through an isolated temporary Python path; no global installation was made.
- The synthetic Jev and OpenAI evaluations used isolated, disposable Clue databases with separate local accounting. No provider/account-side caps or settings were changed, and synthetic runs did not transmit a CV or profile. Provider keys are never printed.
- The live synthetic Jev filter/fit and claim-support benchmarks completed within isolated $0.025 caps. Their measurements and limitations are in [PLAN-020 evaluation results](../evaluations/PLAN-020-evaluation-results.md).
- Earlier synthetic failures included a request using `max` and a local credential-precedence issue. A later post-style run settled four GPT calls but left one Rewriter reservation unknown because the old runner deleted its temporary ledger. The current runner retains unsettled reservations. Subsequent synthetic runs passed grounding, final Jev resume review, packet quality, and document generation; the latest `SYN-02` artifacts also passed visual inspection. See the evaluation report for sanitized measurements.
- The provider rate card and tool prices are time-sensitive. Use the configured rate-card revision for local estimates and refresh it before live requests; these values are not provider-account limits.
- Technical-profile routing is now implemented and covered by offline tests: permitted source IDs, hashes, and unreviewed claim excerpts are bound to the opportunity snapshot. Recruiter/Rewriter can use the full profile after the owner trigger; optional Hiring Manager practice receives it only after its separate action. Jev receives only the exact excerpts cited by generated blocks. No personal profile was included in the synthetic live runs.
- The first rich-portfolio run stopped before Rewriter because Recruiter used exactly its 2,200-token output allowance and returned an incomplete response; four calls settled at `$0.0028728`, with no unresolved usage or packet. A 3,200-token app-local allowance let the next attempt finish. No provider-side settings or caps changed.
- Earlier live-pilot attempts, 2026-10-07: two manually triggered requests for the same scored Jev `review` listing stopped at measured output limits before Jev grounding or final-resume review. Their settled usage and tuning decisions are retained in the evaluation record and ADRs 0028/0030. These failures were followed by additional policy, budget, and prompt tuning; the final live-pilot completion checkpoint below supersedes them as current status.
- Owner-requested real-listing evaluation, 2026-10-07: three official Milan postings were manually triggered: IFOM AI Engineer (`review`), Accenture AI LLM Technology Architecture Analyst (`review`), and Bending Spoons Graduate AI Software Engineer (`match`). The original IFOM prompt `.12` produced one mechanically reviewable packet but no CV edits and repetitive relevance transitions; the other two letters failed Jev's two-paragraph evidence gate. Three additional IFOM retries exposed nondeterministic recruitment-inbox discovery and a Rewriter block with an unapproved claim ID. Clue now omits that block before Jev and keeps the minimum-two-supported-paragraph packet gate. The latest `.16` run passed all automated content gates and produced a review packet, still with zero CV edits and no contact. See the sanitized [evaluation report](../evaluations/PLAN-020-evaluation-results.md) and [ADR 0031](../decisions/0031-public-recruitment-inboxes-and-draft-integrity.md).
- Follow-up on 2026-10-07: PLAN-021/ADR 0024 replace the former 40,000/32,000/4,000 character admission limits and UTF-8-byte reservation with complete selected source text, exact per-request token counting, a documented model-context check, and token-based local reservation. The earlier M1 snapshot passed 272 tests; the final integration suite after rubric/prompt updates passed 287 tests with Ruff, byte-compilation, and `git diff --check`.

## Desired state

- A versioned evaluation harness reports deterministic-filter confusion matrices, Jev filter/fit and ranking metrics, factual-grounding performance, stage-level GPT writing rubric results, and document integrity/rendering checks.
- Jev remains the sole job-fit and eligibility authority. Separately, Jev evaluates whether each generated factual assertion is supported, contradicted, or unresolved against its approved claim, exact permitted technical-profile excerpt, or verified public source. That check cannot alter the saved match score, status, weights, or filter decisions.
- After generation and factual grounding, a separate Jev decision must explicitly approve the complete tailored resume against the exact saved listing and read-only original match snapshot. This final decision cannot update the original fit/eligibility result; model-reported confidence is diagnostic only.
- Unsupported or contradictory assertions are removed or block the packet from being approved as ready; unresolved assertions remain clearly flagged for owner input. Profile entailment does not independently verify the source's truth, so the owner still reviews all generated materials.
- Synthetic model labels, synthetic Jev judgments, and owner judgments are reported separately. No personal relevance tuning is claimed until the owner labels a suitable set of real opportunities.
- Profile use is stage-scoped and bound to a manual listing trigger. The Researcher gets no candidate profile; the Diagnoser gets the selected CV plus job/Jev context; Recruiter/Rewriter receive full permitted technical profiles and their exact source-bound evidence IDs; optional Hiring Manager practice receives technical context after its own action. The Rewriter may also receive full selected descriptive profiles and writing references. The request is admitted using the exact input-token count and configured output allowance. Unreviewed technical excerpts may be cited without pre-approving each suggestion, but generated facts must pass Jev support and the complete packet remains subject to owner review. Descriptive material with unknown or AI-assisted authorship is style-only and cannot become factual career claims or unconfirmed first-person motivation.
- The current writing-quality fixtures cover two synthetic role families and a 12-project synthetic portfolio. They exercise project selection and evidence levels, but do not reproduce any real candidate portfolio. The latest real-data IFOM packet passed automated content gates; the generated CV had no bullet edits, and the exact packet remains in owner review before any external use. The three-listing sample is too small to establish repeatable drafting, contact discovery, useful CV tailoring, personal-fit calibration, or hiring benefit.
- Live evaluations are individually triggered, privacy-bounded, and protected by small app-side caps. No application submission or outreach send is performed.

## Scope

- Build and run offline benchmark cases for deterministic filters, Jev decisions, generation contracts, prompt-injection resistance, claim grounding, and document rendering.
- Add a bounded Jev evidence-support gate for factual assertions in resumes, cover letters, application answers, and outreach drafts.
- Improve the GPT generation prompts and schemas only when benchmark evidence supports the change.
- Add a synthetic live GPT-6 Luna pipeline pilot and a synthetic live Jev benchmark with independent, low hard caps.
- After synthetic acceptance, use the owner's authorization to run at most one selected, eligible real opportunity through the manual preparation action and inspect its complete output locally.
- Profile use is stage-scoped and bound to the individual listing trigger. Approved profile source excerpts may be used only by the permitted stages and must pass Jev support before appearing in output. Synthetic benchmarks exclude real candidate material.
- Update the plan, source-of-truth architecture/product documentation, ADRs, and change log as applicable.

## Out of scope

- Automatic applications, form submission, email sending, bulk preparation, or Gmail integration testing.
- Changing Jev's match decision based on GPT output or using GPT as a second fit score.
- Tuning to the owner's personal job preferences from assistant-authored synthetic labels.
- Treating Jev's evidence-support output as proof that an underlying owner claim is true in the world.
- Sending user profiles, CVs, contacts, or generated documents to an external provider during synthetic benchmarks.
- Changing the existing Jev rolling app cap or mixing Jev and OpenAI ledgers.

## Source-of-truth impact

- This plan records the evaluation and evidence-grounding work. Update PLAN-019 and ADR 0023/ a new decision record if the Jev responsibility boundary or packet approval rules change.
- Update `docs/architecture/overview.md`, `docs/product-definition.md`, and `docs/roadmap.md` to distinguish fit validation from generated-claim evidence checking, and synthetic verification from owner calibration.
- Keep personal labels, source documents, candidate evidence, API keys, generated content, and live response bodies in local storage only.

## Existing decisions and constraints

- [ADR 0023](../decisions/0023-application-preparation-and-action-boundaries.md) keeps Jev as sole matching validator and GPT-6 Luna as generator/researcher. PLAN-020 extends Jev only to evidence-support checking without granting it authority to revise match results.
- OpenAI currently uses `gpt-6-luna`, `reasoning.effort=high`, the Responses API, strict structured outputs, and `store:false`. The earlier `max` value is superseded by the owner's latest direction. Context7's current GPT-6 Luna model documentation lists both `high` and `max` as supported. No silent model or reasoning fallback.
- Keep OpenAI's app-side request controls and usage ledger separate from Jev. Synthetic limits, where used, belong only to the disposable evaluation database; Clue does not change provider-account settings or limits.
- The first live GPT pipeline run uses synthetic profile, CV, job, and claims in an isolated test database. The real-data pilot occurs only after synthetic acceptance and is limited to one eligible listing chosen through the individual preparation action.
- Only an owner-authored descriptive profile may support a directly stated preference. Unknown or AI-assisted descriptive material is style guidance only and cannot support factual claims or first-person motivation.
- The live synthetic Jev benchmark uses a disposable isolated database; its usage ledger is separate from persisted application settings.
- Any uncertainty, contradiction, unsupported number, identity, qualification, or work-history statement must be surfaced. Human packet review remains mandatory.

## Supporting skills / tools

- `implementation-plan` and `milestone-delivery` for plan and validation checkpoints.
- `anti-slop` for writing-quality review; `documents` and `pdf` for artifact inspection and render checks.
- Context7 documentation for the OpenAI Responses API and TypeSafe Python SDK; official OpenAI model pricing page for current rates.
- Existing pytest, Ruff, byte-compilation, local SQLite, generated DOCX, and isolated low-cap live-provider harnesses.

## Dependencies

- TypeSafe SDK, Scrapling, python-docx, pytest, and Ruff must be available in an isolated validation environment for full-suite evidence. Do not install into the user's global Python environment.
- The TypeSafe and OpenAI accounts must accept the configured keys and have API access. Provider/account-side charges outside Clue's local budgets remain outside these app-side caps.
- Owner-labeled fit judgments are required before personal ranking calibration can be claimed.

## Risks and unknowns

- Jev can itself miss entailment or overstate confidence. Measure false acceptance and false rejection on adversarial and supported paraphrase examples; unresolved results must fail closed.
- A single model handling both matching and evidence checking can share failure modes. Record this limitation and keep deterministic checks and human review in place.
- Assistant-authored relevance labels can create circular benchmark results. Do not present them as personal calibration evidence.
- GPT-6 Luna may produce inconsistent output across live runs. Capture model ID, prompt/schema versions, token usage, request status, and rubric scores, but keep personal response bodies local.
- The reconstructed DOCX workflow does not promise pixel-perfect fidelity to complex source layouts. Evaluate text/order integrity and inspect rendered output; document unsupported layout cases.
- Confidence calibration cannot be inferred from assistant-authored labels; no owner-labeled relevance set exists.
- The synthetic `SYN-02` packet was rendered and visually inspected. A Windows DOCX renderer is not available in the current host, so the latest real IFOM resume and cover letter were reopened structurally with `python-docx` but not visually inspected. Complete real-CV layout remains unverified.

## Milestones

### M1 — Reproducible evaluation baseline

Goal: Establish pass/fail checks and capture baseline performance for every named stage before tuning.

Subtasks:

- [x] Version a synthetic gold set for deterministic filters, Jev hard constraints and ranking, and claim-support decisions, including missing, contradictory, prompt-injected, and unsupported numeric evidence.
- [x] Add metrics for filter precision/recall, Jev decision agreement and nDCG, and generated-claim false acceptance/rejection. Confidence reliability remains unknown until owner-labeled cases exist.
- [x] Add a writing rubric for relevance, evidence traceability, voice, concision, question adherence, and unresolved-fact handling; retain owner judgments separately from mechanical checks.
- [x] Add and run artifact checks for source-line completeness/order, DOCX readability, expected files, and render inspection on a complete synthetic packet.
- [x] Make the live Jev benchmark accept a strict evaluation-only budget so it cannot inherit the full $4 production cap.
- [x] Run the full offline suite in an isolated dependency-complete environment and record the GPT usage-reporting gap.

Affected areas: `clue_ai/evaluation.py`, Jev/application workflow tests, synthetic fixtures, evaluation documentation.

Dependencies: Current architecture and test inventory review.

Acceptance criteria:

- [x] Every benchmark case has a fixed expected result and rationale; labels are marked assistant-authored, not owner judgments.
- [x] Filter cases report precision, recall, false positives, and false negatives.
- [x] Jev cases report aggregate and per-dimension agreement plus nDCG. Confidence is explicitly not treated as a calibrated probability.
- [x] Grounding cases report false accepts/rejects for supported, contradicted, and unresolved evidence.
- [x] The evaluation-only Jev ledger was isolated in a disposable database and could not modify persisted application settings.
- [x] Synthetic Jev baselines and limitations are recorded in the linked report; live GPT output quality remains unmeasured.

Validation:

- [x] Offline evaluation and targeted tests pass, including support-gate and workflow omission tests.
- [x] Full repository suite passes in an isolated dependency-complete environment (224 tests).
- [x] Ruff and byte-compilation pass for changed Python code.

Documentation updates:

- [x] Record metric definitions, fixture provenance, measured Jev results, and limitations in the synthetic-only report under `docs/evaluations/`.

Applicable specialized skills: `anti-slop`, `documents`.

Expected Git checkpoint: Commit the validated M1 changes on the milestone branch, preserve unrelated PLAN-007 work, and merge through a reviewed PR after required checks pass.

### M2 — Jev evidence-support gate and generation corrections

Goal: Prevent generated factual claims from being treated as ready when approved evidence does not support them.

Subtasks:

- [x] Represent generated factual assertions with explicit links to approved claims or verified public research.
- [x] Ask Jev to classify each assertion as supported, contradicted, or unresolved using only the cited evidence and assertion text.
- [x] Add a deterministic numeric/date guard and use Jev's semantic review for names, qualifications, responsibilities, and unsupported questions. Keep public email addresses out of Jev evidence payloads.
- [x] Fail closed on unsupported/contradictory material, preserve clear reasons, and surface owner questions. Do not automatically retry GPT or Jev; correction stays owner-triggered to avoid duplicate spend.
- [x] Ensure no evidence-check response can mutate Jev's fit score, match/filter status, weights, or eligibility state.
- [x] Add UI data-disclosure text and update ADR 0023 for the expanded Jev use.

Affected areas: `clue_ai/application_prompts.py`, `clue_ai/application_workflow.py`, `clue_ai/jev.py`, schemas, database, UI settings/disclosures, tests, architecture and ADRs.

Dependencies: M1 fixed benchmark cases and baseline.

Acceptance criteria:

- [x] Unsupported numeric claims are downgraded by a deterministic guard even if Jev says supported; contradictory and unresolved blocks are omitted before document rendering.
- [x] Supported paraphrases pass and missing/contradictory evidence is distinguished on the fixed live synthetic set. At the tuned 0.50 confidence heuristic, the latest run matched 12/12; a 0.75 cutoff conservatively rejected two supported cases. Labels are assistant-authored.
- [x] Unresolved and contradictory block results are visible in the packet and absent from generated documents.
- [x] An offline test confirms Jev's saved matching row is byte-for-byte unchanged by the support check.
- [x] Owner review remains required; no send or submission operation was introduced.

Validation:

- [x] Grounding precision/recall regression cases and workflow tests pass.
- [x] Provider timeout retains its Jev reserve, incomplete/low-confidence answers remain unresolved, missing evidence is not sent, and budget exhaustion blocks before client creation.
- [x] Ruff and byte-compilation pass for the gate implementation.

Documentation updates:

- [x] Update PLAN-019, product/architecture docs, settings disclosure, and ADR 0023. The repository has no CHANGELOG.md.

Applicable specialized skills: `anti-slop`.

Expected Git checkpoint: Commit the validated M2 changes on the milestone branch without staging unrelated user edits; merge through a reviewed PR after required checks pass.

### M3 — Low-cap live synthetic provider and document pilot

Goal: Evaluate actual Jev and GPT-6 Luna behavior without transmitting personal data.

Subtasks:

- [x] Use a versioned rate card for local usage estimates and verify it before live requests.
- [x] Run the synthetic Jev request in an isolated disposable database under a local test budget.
- [x] Attempt the full synthetic OpenAI workflow at `gpt-6-luna`/`max`; the request failed before producing a packet. The initial runner deleted its temporary usage ledger before preserving all statuses. No persisted application log contains the original provider error.
- [x] Capture complete provider receipts, prompt/schema versions, stage token usage, local ledger costs, filter and Jev metrics, grounding outcomes, rubric status, and document inspection results for a completed run.
- [x] Diagnose the latest post-style failure and add retention for unsettled temporary ledgers; the historic unknown row itself cannot be reconciled because the prior runner deleted its database.
- [x] Verify launcher credential precedence and run bounded synthetic end-to-end requests at GPT-6 Luna `high`; prompt `.2` and `.3` completed. The latest `.3` run captured stage usage, local cost/statuses, prompt version, Jev match, and grounding before database cleanup; all five GPT calls settled. A stale inherited test value is covered by regression tests and cannot override the workspace `.env` value.
- [x] Diagnose the unresolved cover-letter paragraphs: the first run lacked saved-job evidence; the next had a role paragraph supported but a preference paragraph without linked owner-profile evidence. Add source-ID citations, conservative excerpt binding, a Jev scope limitation, paragraph-level grounding reasons, and an explicit mechanical/human-review rubric. An earlier live packet passed all three support checks; the latest final-resume-gate packet passed two of three and omitted the unsupported block while passing packet quality.
- [x] Render and inspect the prompt `.2` GPT-generated synthetic DOCX packet visually. Both files fit one page without clipping or overflow; the corrected cover-letter title style renders cleanly. Sparse content reflects the deliberately small test fixture.
- [x] Visually render and inspect the latest final-resume-gate DOCX packet with Microsoft Word PDF export and PDFium. Both files reopened; content, source order, grounding, and visual checks passed. The canonical renderer is unavailable on this Windows host.

Affected areas: evaluation runners, isolated temporary database, local API client, application artifacts, evaluation report.

Dependencies: M1 and M2 accepted; current provider access and rates.

Acceptance criteria:

- [x] A bounded synthetic GPT run completed with settled usage. An earlier historical receipt cannot be reconstructed because its temporary database was deleted; no request was repeated to recreate it. The runner now preserves unresolved ledgers.
- [x] Prompt `.3` met its authored M2 grounding fixture. The latest `2026-10-07.7` `SYN-02` packet passed all four generated-block support checks, final resume approval, and exact DOCX visual inspection.
- [x] Offline fault-injection tests verify refusal, incomplete response, parse error, provider mismatch, and missing usage receipts fail without a completed packet; unresolved usage blocks retry. The current live run has no unknown usage row.
- [x] No real candidate data is included in the synthetic calls or report.

Validation:

- [x] Synthetic listing match, separate evidence-support, final tailored-resume Jev review, and bounded full GPT workflows completed. The latest successful run settled every current request; the historical missing receipt remains unrecoverable.
- [x] Record that one historic local usage receipt cannot be reconstructed; do not repeat that request to recreate it. Later synthetic evaluations settled all current usage, and the runner retains unresolved ledgers.
- [x] Reopen and inspect the latest final-resume-gate synthetic artifacts structurally; DOCX text, substantive letter body, and resume source-order checks passed.
- [x] Render and inspect the exact prompt `.2` live packet after the owner's usage confirmation and bounded run.
- [x] Render the exact latest live synthetic packet with Microsoft Word PDF export and PDFium; both one-page documents were visually clean. The canonical renderer is unavailable on this Windows host.
- [x] Verify the earlier completed packet and captured request metadata report `reasoning.effort=high`; the latest failure does not indicate an unsupported effort level.

Documentation updates:

- [x] Record sanitized quantitative results, costs, and limitations in `docs/evaluations/` and update this plan.

Applicable specialized skills: `documents`, `pdf`, `anti-slop`.

Expected Git checkpoint: Commit synthetic pilot code/report on the milestone branch after all checks pass; merge through a reviewed PR after required checks pass. Never commit API output containing personal data.

### M4 — One owner-selected real opportunity pilot and calibration handoff

Goal: Verify the manually selected real-data path only after synthetic acceptance and clearly state what remains uncalibrated.

Subtasks:

- [x] Verify separate synthetic API consent and app-side usage controls in the disposable test database.
- [x] Select one scored Jev `review` listing with verified eligible location and no explicit conflict; use only its individual trigger, preserving the saved Jev result exactly. All pilot requests used that same listing; no second listing was triggered.
- [x] Apply Jev evidence-support checks, structurally reopen the generated DOCX artifacts, and report unsupported, unresolved, and unchanged content. The final packet had 2/2 supported letter paragraphs, no unsupported assertions, an explicitly approved CV, and zero bullet edits. Visual rendering was not available on the Windows host.
- [x] Leave Gmail disconnected; perform no send, external write, or application submission.
- [x] Keep personal-fit calibration marked unknown. An owner-label worksheet is deferred until the owner chooses to calibrate personal ranking preferences; no calibration claim is made.

Affected areas: local Settings database, one selected listing's local packet, and a sanitized evaluation summary.

Dependencies: M3 synthetic acceptance; a real-data pilot uses one individually triggered listing. A `review` state must remain visible and cannot be presented as a match.

Acceptance criteria:

- [x] Only one location-eligible, scored `review` listing was used; the original review status and unresolved checks remained visible and unchanged across all attempts.
- [x] Clue's monthly and per-opportunity reservation checks stopped requests that exceeded the then-current local allowance before making the blocked stage call; the local caps were tuned to `$0.15` for one final bounded run. No provider-account cap was changed.
- [x] All outputs remain local in packet status `review` and require owner approval; no Gmail draft, email, or application submission occurred.
- [x] The report lists diagnosed failures, unresolved job checks, per-stage costs, artifact inspection, and pass/fail outcomes.
- [x] Personal-fit calibration remains marked unknown because no owner-labeled opportunity set was supplied.

Validation:

- [x] Confirm the selected Jev snapshot and its status are unchanged after generation and grounding checks.
- [x] Reopen both generated DOCX files structurally; Jev supported both letter paragraphs and approved the final CV.
- [ ] Visually render and inspect the exact real-data DOCX files; the current Windows host has no supported renderer. Synthetic `SYN-02` visual inspection passed separately.
- [x] Verify every OpenAI and Jev usage receipt settled and record remaining Clue-local cap after the pilot.

Documentation updates:

- [x] Update the plan, roadmap, decision record, and sanitized evaluation report; keep profile content, generated artifacts, and identifying run data out of Git.

Applicable specialized skills: `documents`, `pdf`, `anti-slop`.

Expected Git checkpoint: Push only code, generic tests, public docs, and sanitized metrics on the milestone branch; merge through a reviewed PR after required checks pass. Never push the owner's packet or labels.

### M5 — Three-listing exploratory evaluation and evidence-led tuning

Goal: Exercise the full manually triggered flow on three live employer postings, assess the generated content and Jev decisions, then make narrow changes supported by the failures.

Subtasks:

- [x] Manually trigger three official Milan listings: [IFOM AI Engineer](https://ifom.eu/en/job-opportunities/open-positions/open-position.php?docuID=12430), [Accenture AI LLM Technology Architecture Analyst](https://www.accenture.com/it-it/careers/jobdetails?id=R00344204_it), and [Bending Spoons Graduate AI Software Engineer](https://jobs.bendingspoons.com/positions/695a6f1127aeb1bf21a1b44d?gh_jid=3280615&id=3280615). Preserve their original Jev results (`review`, `review`, and `match` respectively).
- [x] Evaluate discovery filtering, Jev match decisions, GPT-6 Luna output, source IDs, Jev claim support, final-resume decisions, local document generation, and usage settlement. The initial IFOM packet passed automated gates but had zero CV edits and repetitive letter transitions; Accenture and Bending Spoons failed the required two-supported-paragraph letter gate.
- [x] Retest IFOM under prompts `.14`–`.16`. These runs identified an organization-published recruitment inbox, a Jev-supported outreach draft on one attempt, nondeterministic contact discovery, an unapproved Rewriter evidence ID, and a cover-letter paragraph Jev could not support.
- [x] Omit only generated blocks that cite evidence outside the request's approved ID set, record the omission for review, and allow Jev to assess remaining blocks. Keep the two-supported-paragraph requirement and final-resume approval gate unchanged.
- [x] Correct the deterministic AI-focus false negative for an AI-implementation role with an `Analyst` title. Add positive and negative regression coverage.
- [x] Keep all generated material local. No outreach was sent, no application was submitted, and no provider-account cap or setting was changed.

Acceptance criteria:

- [x] All three listings have recorded, unchanged Jev match and eligibility results; GPT use is separate from matching authority.
- [x] Unapproved evidence IDs cannot enter Jev evidence checks or generated artifacts; remaining claims require Jev support and explicit final-CV approval.
- [x] The latest IFOM `.16` run produced a review packet with 2/2 supported letter paragraphs, explicit final-CV approval, complete local usage settlement, and zero CV edits. The exact DOCX files were structurally reopened; visual rendering is unavailable on this host.
- [x] The two other initial listings failed closed and produced no artifacts. Their unresolved outputs are not counted as successful drafting.
- [ ] Owner review confirms that the actual IFOM letter follows the writing guidelines and that the unchanged CV is useful for this application. Personal-fit calibration, representative portfolio coverage, contact-discovery reliability, visual rendering, and hiring outcomes remain unknown.

Validation:

- [x] Focused workflow, public recruitment-inbox, prompt, and AI-title filter regressions pass.
- [x] Full repository suite, Ruff, byte-compilation, JavaScript syntax, and `git diff --check` after this M5 change pass; details are in Final integration validation below.
- [x] All known OpenAI and Jev usage rows for the live evaluations are settled; the evaluation report records the sanitized totals and Clue-local controls.

Documentation updates:

- [x] Update this plan, [PLAN-019](PLAN-019-application-preparation-framework.md), [ADR 0031](../decisions/0031-public-recruitment-inboxes-and-draft-integrity.md), the roadmap, product definition, and sanitized evaluation report. Exclude profile text, response bodies, request IDs, and generated DOCX files.

Expected Git checkpoint: Validate and push the code, tests, decision record, plan, and sanitized measurements on the milestone branch; merge only through a passing reviewed PR. Never commit `.data`, `.env`, profiles, or generated packet artifacts.

## Final integration validation

- [x] Final full suite after M5: 306 passed in 62.69 seconds in the dependency-complete Python environment with pytest temporary files under Windows Temp; Ruff, `compileall`, `node --check clue_ai/static/app.js`, and `git diff --check` passed. One upstream Starlette/AnyIO deprecation warning remains.
- [x] Writing quality and portfolio representativeness limits are recorded. The live packet is specific and Jev-grounded but includes repeated relevance bridges; one attempt to replace them with transfer claims was rolled back after Jev returned unresolved. Broader voice acceptance still requires owner review.
- [ ] The owner reviews the exact generated packet against the writing rubric before approving it for external use. This review remains separate from the synthetic sample feedback.
- [x] Synthetic live Jev reports distinguish model behavior from assistant-authored labels. The current provider/document run passed its mechanical checks and settled its local usage ledger.
- [x] The original single-listing pilot completed Jev claim support, final-resume approval, and packet-quality checks after output-limit and local-budget tuning. Its DOCX artifacts were reopened structurally; visual rendering was not available. Later M5 tested two additional postings and four IFOM retries.
- [x] Source-of-truth docs, ADR, and roadmap agree with current synthetic evidence and the remaining acceptance gates; no changelog exists.

## Rollback / recovery

- Revert the relevant M2 code/ADR commit if the evidence gate blocks valid outputs or changes stored Jev decisions. The existing preparation flow remains available after revert, but do not present it as evidence-verified.
- Keep evaluation databases temporary and disposable. Keep the production API consent/caps separate from synthetic test controls.
- Do not delete uncertain provider ledger reservations; reconcile them before another live request. The earlier runner violated this by deleting the latest disposable DB; the fix retains unsettled records and is covered offline.
- Preserve unrelated PLAN-007 changes and all owner data. Generated test artifacts must live in a temporary directory.

## Progress

- [x] Inspected PLAN-019, ADR 0023, current generation prompts, Jev integration, settings disclosures, test inventory, and working-tree state.
- [x] Confirmed targeted application, evidence-support, and Jev tests pass with synthetic fixtures.
- [x] Confirmed an unsupported-metric adversarial probe passes the current generated-claim validator.
- [x] M1 baseline metrics and isolated budget-bounded evaluation suite, including source-line/order, DOCX text, expected-file, and rendered-output checks. Confidence reliability remains unknown until owner-labeled cases exist.
- [x] M2 Jev evidence-support gate implemented and covered by offline and synthetic live checks.
- [x] M3 synthetic provider and document pilot: GPT `high` generation, Jev claim support, final tailored-resume approval, substantive packet quality, DOCX reopen, and usage settlement passed. One unsupported block was omitted.
- [x] M3 synthetic visual inspection passed for the latest `SYN-02` DOCX artifacts using Microsoft Word PDF export and PDFium; portfolio representativeness and exact-packet owner review remain open.
- [x] M4 bounded live pilot and calibration handoff: one listing was triggered manually; the packet passed Jev support, CV approval, quality, and usage checks. Its DOCX files were structurally reopened, but visual rendering is unverified. Calibration remains unknown and owner-labeled calibration is deferred.

## 2026-10-07 synthetic evidence checkpoint

This checkpoint supersedes earlier status notes above where they say current visual inspection is unavailable or the synthetic workflow has only one role family. The bounded suite now has two invented role families and a 12-project synthetic portfolio. These checks are integration evidence, not personal preference calibration.

- `jev-grounding-v1.3` removes the unsupported confidence cutoff layered over Jev's categorical evidence verdict. A fixed 12-case synthetic benchmark scored 12/12 against its authored labels (5 supported, 3 contradicted, 4 unresolved); confidence remains diagnostic, and deterministic unsupported-number/date checks still fail closed. See [ADR 0026](../decisions/0026-jev-categorical-evidence-support.md).
- The latest computer-vision case (`SYN-02`, prompt `2026-10-07.7`, `gpt-6-luna` at `high`) passed all synthetic packet gates: Jev matched the six filter checks and approved the tailored resume under `tailored-resume-fit-v2` with reason `no_material_issue`; 4/4 generated factual blocks were supported; both one-page DOCX files reopened and were visually inspected with no clipping or overlap. Microsoft Word PDF export and PDFium were used because the bundled renderer has no Windows LibreOffice executable. The report records the per-agent checks, source and portfolio coverage, practice results, and settled local usage.
- The latest LLM case (`SYN-01`) returned a Jev `review` for location, so the preparation run stopped before any GPT call. That is the intended fail-closed behavior; the runner did not override Jev or spend OpenAI usage. An earlier `SYN-01` full synthetic run passed under the prior review rubric. Live Jev labels varied across repeats, so this remains integration evidence, not determinism or calibration.
- The Jev resume-review rubric now receives the selected structure policy and Recruiter requirement map and returns a separate diagnostic reason code. Only the explicit `approved`/`revise`/`unresolved` decision controls the packet. Confidence and reason codes cannot change Jev matching. See [ADR 0027](../decisions/0027-explainable-jev-resume-review.md).
- Across successful synthetic runs, Jev `revise` or `review` outcomes were respected, unsupported blocks were omitted, and no submission or message was sent. All usage in the latest completed `SYN-02` run settled. No supplied CV/profile, real job, real web crawl, Gmail draft, or personal portfolio was used.
- Synthetic implementation and visual acceptance were complete at this checkpoint. The later same-day live pilot is recorded below; no hiring outcome or personal-fit calibration is claimed.

## 2026-10-07 live pilot completion checkpoint

This entry supersedes earlier M4 status notes. The bounded pilot used one scored Jev `review` listing with verified eligible location and unresolved pay/language checks. The latest successful request used `gpt-6-luna` at `high`, prompt `2026-10-07.12`, schema `application-output-v3`, and the generation-policy snapshot records all per-stage output limits. No second listing was triggered.

- The final run completed four Researcher calls, Diagnoser, Recruiter, and Rewriter. All seven OpenAI usage rows settled: 87,870 input tokens, 11,570 output tokens, `$0.0145720` Clue-local estimate. Jev completed separate claim-support and final-resume checks (7,821 input tokens total; `$0.000328482` local estimate). No reservation or unknown usage remained.
- Jev supported both cover-letter paragraphs, with zero contradicted or unresolved claims, and explicitly approved the final CV (`no_material_issue`). The separate saved Jev match remained `review`, its unresolved checks and evidence were unchanged, and it was not converted to `match`.
- Packet quality passed. Both DOCX files reopened structurally; exact page count, clipping, and visual layout were not verified because no supported renderer is available on this Windows host. The cover-letter title uses a custom Normal-based style to avoid Word's inherited title rule. Artifacts remain in local packet status `review` for owner review.
- The CV contained zero bullet edits; its source order and file hash were unchanged. Recruiter reported six requirements as partial and one as absent from the CV. This is an evidence-preserving no-change result, not proof that the CV is a strong match. Research returned seven findings, no verified contact, and three unresolved questions; no outreach draft, Gmail draft, email, or application was produced.
- Eight of eleven same-listing requests failed safely during tuning: output-token incompletions, one legacy SQLite retry-constraint issue fixed under ADR 0029, a Clue-local per-opportunity reservation block, and one prompt experiment whose two letter paragraphs Jev marked unresolved. That prompt experiment was rejected and the last Jev-supported prompt `.12` retained. Every known usage receipt settled; the current Clue-local monthly and per-opportunity caps are `$0.15`, with `$0.1306722` used and `$0` reserved/unknown. No OpenAI or Jev account cap or setting was changed.
- The `.13` writing refinement tried more explicit task-level transfer language. Jev did not support either resulting paragraph, so the change was rolled back. The successful `.12` output is specific and evidence-backed, but its repeated relevance-bridge wording remains a writing-quality limitation for owner review; no broad personal-voice acceptance is claimed.
- The pilot verifies one end-to-end path, not personal ranking calibration, ATS outcomes, contact-finding coverage, or hiring benefit. Personal fit remains unknown until the owner labels a representative opportunity set. The exact packet remains subject to owner approval before any external use.

## Implementation discoveries / decisions

- Jev's current fit score and filter decision must stay immutable during generated-content checks. The new use is a separate evidence-support verdict, not a second match score.
- For per-block evidence support only, model-reported confidence below 0.50 is downgraded to unresolved. At a 0.75 cutoff, two expected supported paraphrases (confidence 0.52 and 0.57) were conservatively rejected; the tuned 0.50 heuristic produced 12/12 agreement on the next authored synthetic run. This confidence is not a calibrated probability. The distinct final tailored-resume decision uses Jev's explicit label; no confidence cutoff is applied there (see ADR 0025).
- Validation dependencies are available in a disposable Python environment. Synthetic budgets and usage ledgers live in temporary Clue databases; provider account settings were not changed.
- Launcher credential precedence and evidence binding have regression coverage. The synthetic prompt/schema updates preserve source IDs and reject unsupported content; no real profile or candidate data was used.
- The error handler preserves only safe status/error labels and any returned request reference, settles usage before rejecting a mismatched model, and retains unknown reservations. Offline tests cover refusal, incomplete output, malformed JSON, provider mismatch, missing usage, duplicate-trigger blocking, and reconciliation behavior.
- A separate synthetic writing sample is a limited rubric check; it does not substitute for review of a generated packet or establish personal voice.
- The synthetic portfolio is a coverage fixture, not a representation of any real candidate work. The real preparation path remains gated by the individual listing trigger.
- The official model rate is volatile and must be checked immediately before live requests; rates are never inferred from an old plan entry.

## Completion evidence

See [PLAN-020 evaluation results](../evaluations/PLAN-020-evaluation-results.md). Synthetic `SYN-02` passed its Jev, generation, artifact, usage, and visual gates. The owner-requested three-listing exploration kept all original Jev decisions unchanged; prompt `.16` produced the latest IFOM packet with 2/2 Jev-supported letter paragraphs, explicit final-CV approval, packet quality, and settled usage. The CV had zero bullet edits. Both DOCX files reopened structurally but have not been visually rendered; the packet remains in owner review. Personal-fit calibration, useful CV tailoring, repeatable contact research, hiring outcomes, and broad personal-voice acceptance remain unknown. Final repository validation and Git progression will be recorded after the M5 checks.
