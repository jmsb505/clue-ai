# PLAN-020 — End-to-end quality evaluation and evidence grounding

Status: M1–M7 are complete. M8's local heading, two distinct evidence paragraphs, and document scaffold are live-validated on IFOM with prompt `.38`: the v13 rubric passed, Jev supported 2/2 paragraphs, Jev separately approved the final CV, and Word/Poppler inspection found no clipping. The compact letter follows the owner's supplied reference. The saved Jev result stayed `review`. No CV edits were retained and no outreach draft was produced despite one sourced inbox; owner acceptance of the exact packet, useful CV tailoring, paired writing comparison, and representative personal-fit calibration remain open. The full repository suite passed 333 tests locally. One earlier unrelated unknown OpenAI ledger reservation remains. PR #4 is open.
Created: 2026-10-06 · Last updated: 2026-10-08
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
- Owner-requested real-listing evaluation, 2026-10-07: three official Milan postings were manually triggered: IFOM AI Engineer (`review`), Accenture AI LLM Technology Architecture Analyst (`review`), and Bending Spoons Graduate AI Software Engineer (`match`). The original IFOM prompt `.12` produced one mechanically reviewable packet but no CV edits and repetitive relevance transitions; the other two letters failed Jev's two-paragraph evidence gate. Three additional IFOM retries exposed nondeterministic recruitment-inbox discovery and a Rewriter block with an unapproved claim ID. Clue now omits that block before Jev and keeps the minimum-two-supported-paragraph packet gate. The `.16` run passed all automated content gates and produced a review packet, still with zero CV edits and no contact. See the sanitized [evaluation report](../evaluations/PLAN-020-evaluation-results.md) and [ADR 0031](../decisions/0031-public-recruitment-inboxes-and-draft-integrity.md).
- Earlier IFOM retests, 2026-10-08, before the `.38` live validation: `.31` and `.32` produced review packets; `.32` passed its v10 writing gate, both Jev paragraph checks, final-CV approval, usage settlement, and one-page Word/Poppler inspection. It had zero CV edits, seven research findings, and one public recruitment inbox. Owner inspection still found repeated “role includes” lists and generic profile evidence. Prompt `.35` prioritized named project evidence and rejected the list pattern, with focused synthetic coverage. The `.34` trigger stopped before generation when exact input-token preflight hit `dns_lookup_failed`; it produced no OpenAI call or usage row. Prompt `.38` later superseded this offline-only checkpoint with a completed live run. Exact request and saved match identifiers remain local.
- Latest IFOM retest, 2026-10-08: prompt `.38` completed five GPT-6 Luna calls at `high` after Clue's local per-opportunity cap was tuned. All five calls settled at `$0.0114668` (54,253 input / 12,083 output tokens); Jev's support and final-CV decisions cost `$0.000468342` combined. The v13 cover-letter rubric passed at 52 words, Jev supported both paragraphs, and Jev separately approved the final CV. The saved result stayed `review` (fit `0.9873`) and location eligible. Research found eight sourced facts and one official recruitment inbox, but no outreach draft; Rewriter made zero CV edits. Word/Poppler inspection found a clean one-page letter and a two-page resume with a sparse second page. Earlier `.38` retries and the local cap change are documented in the evaluation report; provider/account controls were not changed. The exact letter follows the owner's compact direct-example form, while exact-packet acceptance, useful CV tailoring, and repeatable outreach drafting remain open.
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
- The synthetic `SYN-02` packet was rendered and visually inspected. The packaged LibreOffice renderer is unavailable on Windows; the real IFOM `.38` resume and cover letter were exported through read-only Microsoft Word and Poppler-rasterized. They show no clipping/overlap; the two-page resume's second page is sparse. Earlier `.12`–`.16` live files retain the limitations recorded in their historical rows.

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
- [x] Apply Jev evidence-support checks, reopen and visually inspect the generated DOCX artifacts, and report unsupported, unresolved, and unchanged content. The final packet had 2/2 supported letter paragraphs, no unsupported assertions, an explicitly approved CV, and zero bullet edits. Word export plus Poppler rendered one cover-letter page and two resume pages; no clipping or overlap was visible. The letter lacks a greeting and closing and leaves most of its page blank; the resume's second page is sparse.
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
- [x] Visually render and inspect the exact latest real-data DOCX files using hidden Microsoft Word PDF export and bundled Poppler. Inspect every page; record the underfilled letter and sparse second resume page as usability issues. Synthetic `SYN-02` visual inspection passed separately.
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
- [x] The IFOM `.16` run produced a review packet with 2/2 supported letter paragraphs, explicit final-CV approval, complete local usage settlement, and zero CV edits. It was reopened and visually rendered; its letter lacked the later-added greeting/closing scaffold. The newer `.38` output and visual inspection are recorded at the top of this plan and in the evaluation report.
- [x] The two other initial listings failed closed and produced no artifacts. Their unresolved outputs are not counted as successful drafting.
- [ ] Owner review confirms that the actual IFOM letter follows the writing guidelines and that the unchanged CV is useful for this application. Personal-fit calibration, representative portfolio coverage, contact-discovery reliability, and hiring outcomes remain unknown.

Validation:

- [x] Focused workflow, public recruitment-inbox, prompt, and AI-title filter regressions pass.
- [x] Full repository suite, Ruff, byte-compilation, JavaScript syntax, and `git diff --check` after this M5 change pass; details are in Final integration validation below.
- [x] Rendered the latest live DOCX files through hidden Microsoft Word PDF export and Poppler, then inspected the cover-letter page and both resume pages. Presentation gaps are recorded above and in the evaluation report.
- [x] All known OpenAI and Jev usage rows for the live evaluations are settled; the evaluation report records the sanitized totals and Clue-local controls.

Documentation updates:

- [x] Update this plan, [PLAN-019](PLAN-019-application-preparation-framework.md), [ADR 0031](../decisions/0031-public-recruitment-inboxes-and-draft-integrity.md), the roadmap, product definition, and sanitized evaluation report. Exclude profile text, response bodies, request IDs, and generated DOCX files.

Expected Git checkpoint: Validate and push the code, tests, decision record, plan, and sanitized measurements on the milestone branch; merge only through a passing reviewed PR. Never commit `.data`, `.env`, profiles, or generated packet artifacts.

### M6 — Jev-guided letter repair and complete document output

Goal: Correct the observed cover-letter failure mode, tune the upstream research stage from a measured live truncation, and complete the letter scaffold without weakening Jev's evidence gate.

Root cause from the failed Accenture and Bending Spoons letters: the Rewriter was asked for a role connection, then used inferred bridges (including an unsupported project name and claims that project work “connects directly” to job responsibilities). Jev assessed candidate facts against linked evidence and marked those paragraphs unresolved. The prompt also permitted returning fewer than two paragraphs while packet quality still required two. One Jev-supported IFOM letter repeated the same relevance-bridge style and the renderer omitted a greeting and closing. After the letter repair worked for Accenture, the first Bending retest failed earlier: Researcher reached its 2,200-token output limit and stopped before writing. The failures came from generation guidance and stage budgeting, not Jev's saved match result.

Subtasks:

- [x] Revise the Rewriter instructions to keep candidate facts and role requirements as separately sourced statements; prohibit inferred contribution, transfer, fit, or impact claims; preserve project names and verbs; and prefer a concise one-paragraph result over filler when evidence is limited.
- [x] Add one targeted GPT-6 Luna `letter_reviser` call for Jev-unresolved or mechanically repeated paragraphs. Lock initially supported paragraphs, bind revisions to rejected indices and approved evidence, then have Jev recheck the entire final letter.
- [x] Keep Jev as sole match validator and preserve the two-paragraph/2-of-2 support gate, final-resume approval gate, and no-document-on-failure behavior. A repair or Jev recheck failure remains fail-closed.
- [x] Detect repeated sentences and repair the affected paragraph once. Render a generic salutation and closing and use a candidate name only from an unambiguous CV header.
- [x] Make the packet's quality scope visible to the owner: automated pass covers grounding/completeness, never persuading or personal voice; avoid a fixed word-count threshold.
- [x] Add unit/integration coverage for a targeted repair, complete-letter Jev recheck, failed repair, repeated-sentence repair, and rendered salutation/closing.
- [x] Raise only Clue's Researcher output allowance from 2,200 to 4,000 after a live response terminated at the former ceiling; constrain it to eight prioritized findings and retest the affected listing.
- [x] Retest Accenture and Bending Spoons: both produced review packets, 2/2 final letter paragraphs were Jev-supported, Jev approved both final CVs, and saved match/eligibility results were unchanged.
- [x] Render both exact cover letters through Word and Poppler. They are one page with the new greeting and closing and no clipping/overlap; both remain visibly underfilled, and their candidate/role facts are mostly juxtaposed rather than explicitly related.
- [ ] Owner rates the actual letter voice and usefulness. Automated evidence/format passes do not establish owner acceptance, ATS performance, or hiring outcomes.

Acceptance criteria:

- [x] Offline tests show only marked paragraphs are revised, supported paragraphs remain locked, and every final paragraph receives a new Jev support decision.
- [x] The prior two-supported-paragraph gate and final-resume approval gate remain unchanged; unsupported final content cannot reach a document.
- [x] Duplicate prose is detected and the generated DOCX content has a complete generic greeting/closing scaffold.
- [x] Live Accenture and Bending Spoons retests completed with settled OpenAI usage and unchanged Jev match/eligibility records; both final letters passed 2/2 support and exact rendered documents had no clipping or overlap. The Bending attempt before Researcher tuning failed safely at 2,200 output tokens; the retest completed at 4,000.

Validation: 5 focused regressions and 57 workflow tests passed; seven workflow tests that instantiate `TestClient` were deselected. Ruff, byte-compilation, and `git diff --check` passed. A full-suite attempt stalled without producing a summary and was stopped; no full-suite pass is claimed. Accenture used six settled GPT calls (120,404 input / 14,620 output tokens; `$0.0193504` local estimate), including one repair. Bending's successful `.18` run used five settled calls (80,283 / 9,492; `$0.0127743`); its earlier 2,200-token Researcher failure settled two calls (`$0.0018726`) and created no artifact. All known OpenAI usage rows are settled. The initial Accenture retry had separately stopped at DNS during token preflight with no API usage. No provider settings/caps changed; Clue's existing local limits remain `$0.30` monthly and `$0.15` per opportunity.

Expected Git checkpoint: Keep this change on the PLAN-020 milestone branch and update the open PR after the live retest or explicitly report the network-dependent acceptance as pending. Never merge with failed or unverified required checks.

### M7 — Selected-CV evidence path

Goal: Make the evidence selected by Recruiter available to the Rewriter and Jev at source-line precision, then evaluate whether generated materials use that path to produce stronger, job-specific drafts without relaxing any approval gates.

Observed failure: In the `.20` IFOM run, Recruiter returned exact `cv_line_ids` for multiple criteria, but cover-letter output only supported `claim_ids`. The technical profile had hundreds of unreviewed excerpts; Rewriter used a profile skills statement and a Kubernetes “developing” statement rather than a concrete CV project. Jev supported one paragraph and left the other unresolved. The repair repeated a weak statement and the packet had no documents. Jev separately approved the unchanged resume. The exact saved match decision was not changed.

Subtasks:

- [x] Add `cv_line_ids` to supported generated-content schemas and validate every ID against the selected CV for the current request.
- [x] Bind each cited CV line to its exact text and selected CV source when building Jev factual-support assertions; include it for resume edits, letters, answers, and outreach drafts.
- [x] Let the requirement-link gate validate either a Recruiter-mapped CV line or a mapped profile/approved claim, while preserving distinct role criteria and final-resume approval.
- [x] Pass Rewriter only the exact technical-profile excerpts mapped by Recruiter; do not repeat the entire technical-profile body alongside those excerpts. Researcher still receives no candidate data.
- [x] Prefer concrete CV project evidence over skills inventories or development-level labels; keep unsupported paragraphs out of documents and fail closed when insufficient supportable evidence is available.
- [x] Add offline coverage for source-line evidence binding, invalid line ID removal, requirement linkage, and stage-scoped profile context.
- [ ] Run the fixed synthetic workflow checks and bounded live retest against an already explored official listing, without changing saved Jev match results or sending/submitting anything.
- [ ] Inspect every completed DOCX structurally and visually; report writing quality separately from Jev factual support and final-resume approval.
- [ ] Record live stage outputs, usage settlement, profile-routing, crawler findings, Jev decisions, packet gates, and file-render results in the sanitized evaluation.

Acceptance criteria:

- [ ] Valid line citations are limited to the owner-selected CV, are bound to the exact source line sent to Jev, and appear in the dossier's evidence report.
- [ ] Invented or out-of-snapshot line IDs are omitted before Jev; unsupported claims remain absent from files.
- [ ] Each final cover-letter paragraph is linked to a Recruiter criterion through evidence IDs, supported by Jev, and bound to the selected listing. The final-resume approval gate is unchanged.
- [ ] A bounded live evaluation documents each stage from crawler/Researcher through document generation and Jev, including failures; the saved Jev match/eligibility results stay unchanged.
- [ ] Every successful test packet is structurally reopened and visually inspected. No test sends outreach or submits an application.

Validation:

- Run all applicable application workflow regressions; report any `TestClient` cases excluded by the local environment.
- Run Ruff, Python compilation, and `git diff --check`.
- Check current local budget/reservation state before each live listing. Keep unknown usage rows intact and do not retry the interrupted Accenture snapshot until reconciled.
- Reopen and visually inspect each exact live DOCX through the available Word/Poppler workflow; keep output local.

Documentation updates:

- Update PLAN-020, PLAN-021, product definition, roadmap, and sanitized evaluation results. Add ADR 0033 for selected-CV evidence citations and mapped profile context.
- Remove stale claims that a fixed 80-word threshold is used; the human-approved short sample meets the direct/modest/specific/concision rubric.
- State clearly that evidence and completeness pass does not establish persuasive strength, personal voice, ATS success, or hiring outcomes.

Expected Git checkpoint: Validate and push the milestone branch, update PR #4, and wait for required checks. Do not merge or advance `main` with missing or failing checks.

### M8 — Complete cover-letter argument and document structure

Goal: Prevent a list of source-accurate candidate facts and job duties from passing as a finished letter. Require a locally rendered application heading, exactly two distinct project-evidence paragraphs, precise role links, and a complete rendered document. Jev remains the factual-support authority; the saved Jev matching decision stays immutable.

Root cause: The `.20` IFOM request failed the factual gate at 1/2, but earlier supported letters still consisted of brief evidence/duty pairings. A later gate required a third generated opening paragraph even though the local renderer already supplied an “Application for [role] at [employer]” heading. The `.24` request produced an unsupported opening, and one bounded repair did not resolve it, so no artifacts were created. The owner's example establishes the intended structure: application heading, then two concise project-to-responsibility paragraphs, followed by the rendered close. Its facts are not used as candidate evidence.

Subtasks:

- [x] Change Rewriter output to exactly two `evidence` sections; the locally rendered application heading supplies intent. Require a concrete, distinct project example and exact mapped source citations in each paragraph.
- [x] Add deterministic checks for paragraph count, evidence distinctness, repeated content, padded relevance bridges, and direct role-responsibility wording; offer one targeted Letter Reviser call and Jev-recheck every final paragraph.
- [x] Complete local document rendering with CV-header contact details when present, date, application title, salutation, body, polite closing, sign-off, and CV-derived candidate name.
- [x] Add offline cases for structure, distinct source evidence, boilerplate pairing rejection, bounded repair, and safe contact extraction.
- [x] Run focused offline application-workflow and application-preparation checks, Ruff, byte-compilation, and `git diff --check`; record deselected Windows `TestClient` cases and do not claim the full suite passed.
- [x] Inspect `.32` live output at GPT-6 Luna `high`: Researcher, Rewriter, Jev support, final-CV approval, usage settlement, and saved Jev match invariance were recorded. This output did not meet the owner's desired style despite passing its mechanical rubric.
- [x] Reopen and visually inspect the exact `.32` cover-letter DOCX by Word PDF export and Poppler rasterization; one page, readable, no clipping/overlap, but sparse.
- [ ] Run the refined `.35` prompt on the same owner-selected listing when DNS/token-count preflight succeeds. Inspect its exact DOCX and evaluate content against the reference without treating Jev support or the rubric as owner voice acceptance.
- [ ] Record sanitized live evidence and unresolved CV value, research, voice, ATS, and hiring-outcome questions in PLAN-020 and the evaluation report.

Acceptance criteria:

- The local heading states the application and role. The final letter body contains exactly two distinct evidence examples with source-supported links to separate Recruiter-mapped requirements. Padded generic relevance text, missing paragraphs, duplicate evidence, or unsupported claims fail or receive one bounded repair.
- Jev supports the complete final body after repair, and Jev separately approves the final tailored CV. The saved match, fit, eligibility, and filters remain unchanged.
- The local DOCX is structurally valid and visually clean; no artifact is created after failed quality or evidence gates. No word-count minimum is used.
- The output is presented as an owner-review draft. The mechanical gate does not claim to score persuasion, personal voice, ATS success, or hiring outcomes.

Documentation updates: [PLAN-021 M5](PLAN-021-evidence-led-generation-quality.md), sanitized evaluation, product definition, roadmap, architecture overview, [ADR 0034](../decisions/0034-complete-cover-letter-argument.md), and superseding structure refinement [ADR 0035](../decisions/0035-application-heading-and-two-evidence-paragraphs.md).

### 2026-10-08 — Specific evidence and direct-role-link refinement

The `.32` letter showed that the two-paragraph scaffold and Jev entailment check were necessary but insufficient for a useful cover letter. Owner review identified repeated “role includes [technology list]” sentences and selection of general skill claims over distinctive project evidence. Prompt `.35` ranked specific role-relevant project claims higher and detected formulaic role-duty lists; `.38` added first-person owner action and distinctive preferred-profile details, recorded in [ADR 0037](../decisions/0037-first-person-project-evidence-in-cover-letters.md). The `.38` output passed the v13 gate, Jev support, separate final-CV approval, and visual inspection, while zero CV edits and no outreach draft remain gaps.

The `.34` attempt failed at the local DNS resolver during exact token-count preflight (`api.openai.com` lookup failed). Clue did not send the generation request, create usage rows, or consume OpenAI generation budget. This was not evidence of an OpenAI API or key failure. A later network-enabled retry completed as prompt `.38`; Clue increased only its local request caps to fit the selected listing, without changing provider/account controls. A separate pre-existing unknown ledger reservation remains. The full repository suite now passes 333 tests; the older 329-test result is retained as the checkpoint from that earlier attempt.

Expected Git checkpoint: Update PR #4 with the validated branch and wait for required checks. Do not merge, push into `main`, or report milestone completion while required checks or acceptance evidence are missing.

## Final integration validation

- [x] Final full suite after M5: 306 passed in 62.69 seconds in the dependency-complete Python environment with pytest temporary files under Windows Temp; Ruff, `compileall`, `node --check clue_ai/static/app.js`, and `git diff --check` passed. One upstream Starlette/AnyIO deprecation warning remains.
- [x] Writing quality and portfolio representativeness limits are recorded. The live packet is specific and Jev-grounded but includes repeated relevance bridges; one attempt to replace them with transfer claims was rolled back after Jev returned unresolved. Broader voice acceptance still requires owner review.
- [ ] The owner reviews the exact generated packet against the writing rubric before approving it for external use. This review remains separate from the synthetic sample feedback.
- [x] Synthetic live Jev reports distinguish model behavior from assistant-authored labels. The current provider/document run passed its mechanical checks and settled its local usage ledger.
- [x] The original single-listing pilot completed Jev claim support, final-resume approval, and packet-quality checks after output-limit and local-budget tuning. Its DOCX artifacts were reopened structurally; visual rendering for that earlier packet remains unverified. Later M5 tested two additional postings and four IFOM retries, and visually rendered the latest `.16` packet.
- [x] Source-of-truth docs, ADR, and roadmap agree with current synthetic evidence and the remaining acceptance gates; no changelog exists.
- [x] Pushed milestone branch `codex/plan-020-three-listing-evaluation` and opened [PR #4](https://github.com/jmsb505/clue-ai/pull/4). GitHub reports it mergeable but returned no commit status checks or PR workflow runs; local checks above are the available validation evidence. The PR remains open while owner review of the generated output is pending.

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

See [PLAN-020 evaluation results](../evaluations/PLAN-020-evaluation-results.md). Synthetic `SYN-02` passed its Jev, generation, artifact, usage, and visual gates. The owner-requested three-listing exploration kept all original Jev decisions unchanged; the `.38` IFOM packet passed the v13 letter rubric, 2/2 Jev-supported paragraphs, separate final-CV approval, packet quality, settled usage, and Word/Poppler inspection. Its CV had zero bullet edits; no outreach draft was produced despite one sourced inbox. The letter follows the owner's compact direct-example format, and the resume's second page is sparse. Exact-packet owner acceptance, useful CV tailoring, repeatable outreach drafting, personal-fit calibration, hiring outcomes, and broad writing-quality comparison remain open. PR #4 is open; CI status after this checkpoint must be checked before merge.
