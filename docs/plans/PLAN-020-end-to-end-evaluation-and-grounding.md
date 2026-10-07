# PLAN-020 — End-to-end quality evaluation and evidence grounding

Status: M1–M3 synthetic and implementation gates validated across two role families; current synthetic visual inspection passed; exact-packet owner acceptance and the manually triggered real-data pilot remain pending; M4 is owner-triggered
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
- Follow-up on 2026-10-07: PLAN-021/ADR 0024 replace the former 40,000/32,000/4,000 character admission limits and UTF-8-byte reservation with complete selected source text, exact per-request token counting, a documented model-context check, and token-based local reservation. The earlier M1 snapshot passed 272 tests; the final integration suite after rubric/prompt updates passed 287 tests with Ruff, byte-compilation, and `git diff --check`.

## Desired state

- A versioned evaluation harness reports deterministic-filter confusion matrices, Jev filter/fit and ranking metrics, factual-grounding performance, stage-level GPT writing rubric results, and document integrity/rendering checks.
- Jev remains the sole job-fit and eligibility authority. Separately, Jev evaluates whether each generated factual assertion is supported, contradicted, or unresolved against its approved claim, exact permitted technical-profile excerpt, or verified public source. That check cannot alter the saved match score, status, weights, or filter decisions.
- After generation and factual grounding, a separate Jev decision must explicitly approve the complete tailored resume against the exact saved listing and read-only original match snapshot. This final decision cannot update the original fit/eligibility result; model-reported confidence is diagnostic only.
- Unsupported or contradictory assertions are removed or block the packet from being approved as ready; unresolved assertions remain clearly flagged for owner input. Profile entailment does not independently verify the source's truth, so the owner still reviews all generated materials.
- Synthetic model labels, synthetic Jev judgments, and owner judgments are reported separately. No personal relevance tuning is claimed until the owner labels a suitable set of real opportunities.
- Profile use is stage-scoped and bound to a manual listing trigger. The Researcher gets no candidate profile; the Diagnoser gets the selected CV plus job/Jev context; Recruiter/Rewriter receive full permitted technical profiles and their exact source-bound evidence IDs; optional Hiring Manager practice receives technical context after its own action. The Rewriter may also receive full selected descriptive profiles and writing references. The request is admitted using the exact input-token count and configured output allowance. Unreviewed technical excerpts may be cited without pre-approving each suggestion, but generated facts must pass Jev support and the complete packet remains subject to owner review. Descriptive material with unknown or AI-assisted authorship is style-only and cannot become factual career claims or unconfirmed first-person motivation.
- The current writing-quality fixtures cover two synthetic role families and a 12-project synthetic portfolio. They exercise project selection and evidence levels, but do not reproduce any real candidate portfolio. Exact-packet owner review and the manually triggered real-data pilot remain open.
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
- The canonical documents renderer and Poppler are available. The exact current synthetic packet was rendered and visually inspected: each file fits one page without clipping or overflow, and the corrected cover-letter heading has no unwanted rule. Both files are sparse because the synthetic inputs intentionally contain few sections and claims; complete real-CV layout remains untested.

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
- [ ] Select at most one eligible match through its individual Prepare application action and run one packet using only the disclosed approved inputs.
- [ ] Apply Jev evidence support checks, inspect each generated artifact and report factual corrections/unsupported assertions to the owner.
- [ ] Leave Gmail disconnected; perform no send, external write, or application submission.
- [ ] Produce an owner-label worksheet for a stratified sample of real opportunities before making any claim of personal Jev ranking calibration.

Affected areas: local Settings database, one selected listing's local packet, and a sanitized evaluation summary.

Dependencies: M3 synthetic acceptance; a real-data pilot requires the user to choose one eligible listing and click its individual Prepare application action, which authorizes only that selected run and its disclosed inputs.

Acceptance criteria:

- [ ] Only one eligible, individually triggered listing is sent through the live generation path.
- [ ] The API cap blocks any additional request that would exceed the reservation.
- [ ] All outputs remain local and require owner approval; Gmail/application state has no send/submission event.
- [ ] The report lists corrections, unresolved items, per-stage costs, artifact inspection, and whether the workflow passed acceptance.
- [ ] Personal fit calibration remains marked unknown until the owner supplies judgments for the evaluation set.

Validation:

- [ ] Confirm the selected Jev snapshot and its status are unchanged after generation and grounding checks.
- [ ] Inspect generated DOCX outputs in a local renderer and validate every factual assertion against the approved evidence.
- [ ] Verify API usage receipts and remaining cap after the pilot.

Documentation updates:

- [ ] Update plan, roadmap, and local-only evaluation report; exclude private content from Git.

Applicable specialized skills: `documents`, `pdf`, `anti-slop`.

Expected Git checkpoint: Push only code, generic tests, public docs, and sanitized metrics on the milestone branch; merge through a reviewed PR after required checks pass. Never push the owner's packet or labels.

## Final integration validation

- [x] Final full suite (287 passed in 62.82 seconds; one pytest cache-path permission warning) in a disposable dependency-complete environment after the latest Jev and prompt changes; Ruff, `compileall`, and `git diff --check` also pass.
- [ ] Writing quality and portfolio representativeness require broader evidence and owner review of the exact packet. Current synthetic checks pass mechanics but do not establish personal voice, fit, or portfolio acceptance.
- [ ] The owner reviews the exact generated packet against the writing rubric. This review remains separate from the synthetic sample feedback. Automated filter, Jev, grounding, usage, privacy-boundary, and document checks pass on synthetic cases.
- [x] Synthetic live Jev reports distinguish model behavior from assistant-authored labels. The current provider/document run passed its mechanical checks and settled its local usage ledger.
- [ ] One real pilot, if M3 passes, is bounded to the single owner-authorized listing and manually reviewed.
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
- [ ] M4 one owner-selected live pilot and calibration handoff.

## 2026-10-07 final evidence checkpoint

This checkpoint supersedes earlier status notes above where they say current visual inspection is unavailable or the synthetic workflow has only one role family. The bounded suite now has two invented role families and a 12-project synthetic portfolio. These checks are integration evidence, not personal preference calibration.

- `jev-grounding-v1.3` removes the unsupported confidence cutoff layered over Jev's categorical evidence verdict. A fixed 12-case synthetic benchmark scored 12/12 against its authored labels (5 supported, 3 contradicted, 4 unresolved); confidence remains diagnostic, and deterministic unsupported-number/date checks still fail closed. See [ADR 0026](../decisions/0026-jev-categorical-evidence-support.md).
- The latest computer-vision case (`SYN-02`, prompt `2026-10-07.7`, `gpt-6-luna` at `high`) passed all synthetic packet gates: Jev matched the six filter checks and approved the tailored resume under `tailored-resume-fit-v2` with reason `no_material_issue`; 4/4 generated factual blocks were supported; both one-page DOCX files reopened and were visually inspected with no clipping or overlap. Microsoft Word PDF export and PDFium were used because the bundled renderer has no Windows LibreOffice executable. The report records the per-agent checks, source and portfolio coverage, practice results, and settled local usage.
- The latest LLM case (`SYN-01`) returned a Jev `review` for location, so the preparation run stopped before any GPT call. That is the intended fail-closed behavior; the runner did not override Jev or spend OpenAI usage. An earlier `SYN-01` full synthetic run passed under the prior review rubric. Live Jev labels varied across repeats, so this remains integration evidence, not determinism or calibration.
- The Jev resume-review rubric now receives the selected structure policy and Recruiter requirement map and returns a separate diagnostic reason code. Only the explicit `approved`/`revise`/`unresolved` decision controls the packet. Confidence and reason codes cannot change Jev matching. See [ADR 0027](../decisions/0027-explainable-jev-resume-review.md).
- Across successful synthetic runs, Jev `revise` or `review` outcomes were respected, unsupported blocks were omitted, and no submission or message was sent. All usage in the latest completed `SYN-02` run settled. No supplied CV/profile, real job, real web crawl, Gmail draft, or personal portfolio was used.
- Synthetic implementation and visual acceptance are complete for this evaluation checkpoint. Review of a generated packet, broader portfolio coverage, and one manually selected real listing/CV pilot remain the next acceptance gate; no hiring outcome or personal-fit calibration is claimed.

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

See [PLAN-020 evaluation results](../evaluations/PLAN-020-evaluation-results.md). The latest synthetic `SYN-02` flow passed final tailored-resume approval, packet quality, DOCX reopen, visual inspection, and usage settlement. A repeated `SYN-01` returned Jev `review` and stopped before GPT; an earlier full `SYN-01` run passed. The remaining gates are paired writing-quality evaluation, exact-packet review, representative portfolio coverage, and the single owner-triggered real listing/CV pilot.
