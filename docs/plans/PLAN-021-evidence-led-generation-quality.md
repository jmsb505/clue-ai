# PLAN-021 — Evidence-led generation quality and context budgeting

Status: M1 complete; M2 synthetic pipeline checks pass for two role families, but paired baseline and representative portfolio/owner rubric acceptance remain open; M3 Jev-approved packet gates pass on synthetic fixtures, while real public-research and manually triggered real-data validation remain open
Created: 2026-10-07 · Last updated: 2026-10-07
Related: [PLAN-019](PLAN-019-application-preparation-framework.md), [PLAN-020](PLAN-020-end-to-end-evaluation-and-grounding.md), [ADR 0023](../decisions/0023-application-preparation-and-action-boundaries.md)

## Objective

Make Clue produce useful, job-specific resumes, cover letters, and research drafts from all selected, permitted candidate material. Validate the original job match with Jev, require Jev to explicitly approve the final tailored resume against that same listing, and require Jev evidence support for generated factual claims. Use test evidence to tune prompt context, output budgets, quality gates, and workflows.

## Motivation

Tune platform workflows and guardrails when evaluation evidence shows a better path to useful application materials. App-authored character cutoffs can reject selected profiles even when a complete request fits the model context. Use exact request token counting and the documented context check instead of arbitrary per-profile character limits.

OpenAI's current model documentation lists GPT-6 Luna at a 1,050,000-token context window and a maximum of 128,000 output tokens. The Responses API also has an input-token counting endpoint that returns the exact number of tokens for the model's input. Clue currently uses character cutoffs for profile admission and UTF-8 payload bytes as a token estimate for its local spend reservation. The exact model-context budget and measured generation costs therefore are not represented in the current guardrails.

Earlier evidence also showed that the Recruiter hit its 2,200-token output allowance and returned incomplete JSON. Raising that stage to 3,200 allowed the following response to complete at 2,445 output tokens. This supports tuning per-stage output allowances from actual incomplete and complete responses rather than setting one blanket output limit.

## Current state

- GPT-6 Luna runs through the Responses API at `reasoning.effort=high`, after the owner manually triggers one listing. No application or outreach is submitted or sent.
- Diagnoser receives the selected CV and Jev snapshot. Recruiter and Rewriter receive the full selected technical profiles and source-bound evidence. Rewriter also receives the full selected descriptive profile and permitted writing references. Researcher gets no candidate profile.
- Jev is authoritative for the saved job fit and eligibility. After generation, a separate Jev decision approves or rejects the final tailored resume against the exact listing without modifying the saved fit result. A third, separate Jev support check validates each generated factual block against only its cited evidence.
- Generated claim support, line/source bindings, Jev's final tailored-resume decision, packet-quality gates, and DOCX generation have synthetic tests. In the latest synthetic live run, Jev approved the final resume (confidence 0.64, retained as diagnostic only), the packet-quality gate passed, and both DOCX files reopened. Jev supported two of three generated factual blocks; the remaining block was omitted. The broader portfolio benchmark and exact-artifact visual inspection remain open.
- The prior GPT usage ledger estimated input tokens from UTF-8 payload bytes; it now counts the exact request. Use the current configured rate card and token-based reservation.
- OpenAI's current model page applies 2× input and 1.5× output rates to the full request when input exceeds 272,000 tokens. The prior local ledger used only standard rates; M1 must apply this surcharge for long requests.

## Desired state

- Clue counts each exact Responses API request before generation, checks it against the documented model context window, and reserves spend from the counted input tokens plus the configured maximum output tokens.
- Requests above 272,000 input tokens reserve at the documented long-context multipliers: 2× input and 1.5× output for the full request.
- No selected profile is rejected because of an arbitrary character-length cutoff. If a complete request exceeds the model context window, Clue reports the counted size and keeps the request from reaching generation. It does not silently truncate candidate evidence.
- Per-stage output allowances are based on required schema/content and measured completion rates. An incomplete result never produces a finished packet.
- A packet is useful only when it contains at least two supported body paragraphs with candidate evidence and verified role-source citations. A title-only or materially incomplete cover letter fails the packet before document rendering.
- Packet readiness requires the saved Jev match plus an explicit Jev `approved` decision for the final tailored resume. Jev's reported confidence is recorded for diagnosis only because it is not calibrated; it cannot override the discrete decision. Unsupported or contradicted facts cannot enter a document.
- A fixed, diverse benchmark reports filtering, Jev fit/eligibility, each generation agent, Jev claim support, document integrity, and rendered document quality separately. Synthetic results are labeled synthetic. Personal-fit calibration is labeled unknown until owner labels real opportunities.
- Real candidate data is sent only after the owner clicks Prepare application for an individual listing. The owner checks the final materials and performs every application or outreach action.

## Scope

- Replace arbitrary profile character cutoffs and byte-as-token reservation with model-aware, exact input-token preflight and token-based reservation.
- Tune stage output allowances based on captured incomplete/completed responses and content requirements.
- Strengthen the fixed evaluation corpus and rubric for Diagnoser, Recruiter, Rewriter, Researcher, Hiring Manager, Jev, source grounding, and generated artifacts.
- Make packet readiness require meaningful outputs and Jev-supported factual content.
- Record the resulting platform behavior and decisions in source-of-truth documentation.
- Run a bounded synthetic end-to-end validation. Use real profile material only in a manually triggered individual-listing pilot; no automatic or bulk runs.

## Out of scope

- Replacing Jev with GPT or letting GPT alter Jev fit, filter, eligibility, or qualification results.
- Automatic application submission, form filling on the employer site, Gmail writes, or outreach sends.
- Treating Jev's support verdict as proof that a source claim is true outside the supplied evidence.
- Tuning Jev to synthetic author-assigned labels as if those labels represented the owner's preferences.
- Raising provider/account caps or changing provider-level billing settings. App-side spend rules remain independently configured and observable.

## Source-of-truth impact

- Add ADR 0024 for token-aware request admission, profile routing, and stage output budgets.
- Update `docs/product-definition.md`, `docs/architecture/overview.md`, `docs/roadmap.md`, and PLAN-019/PLAN-020 where their current context-limit or acceptance statements become stale.
- Keep evaluation fixtures and aggregate metrics in versioned repository files; keep API keys, personal source files, live response bodies, and owner-labeled private decisions in local storage.
- The repository has no `CHANGELOG.md`.

## Existing decisions and constraints

- ADR 0023 keeps Jev as the only job-fit and eligibility validator and defines the per-listing manual trigger and owner review.
- The selected technical and descriptive profiles are bound to an individual listing request. Researcher does not receive either profile.
- The official GPT-6 Luna model page documents the current context and output limits: [Models](https://developers.openai.com/api/docs/models).
- OpenAI documents exact request token counting: [Counting tokens](https://developers.openai.com/api/docs/guides/token-counting) and [Count input tokens API](https://developers.openai.com/api/reference/resources/responses/subresources/input_tokens/methods/count).
- Application and provider keys stay local; request logs must not persist prompts or generated personal content.

## Supporting skills / tools

- `implementation-plan` and `milestone-delivery` for the staged work.
- `anti-slop` for user-facing writing-quality criteria and documentation prose.
- OpenAI API documentation via Context7 for model limits and token-count endpoint details.
- Existing pytest and Ruff toolchain. No new test suite is added beyond the user's request to test and tune the workflow.

## Dependencies

- OpenAI API key and manual-trigger consent are configured locally for synthetic testing.
- Current OpenAI rate card is verified before a live generation run.
- A locally selected eligible listing and CV are required before any real-data pilot.
- A representative public portfolio reference may be used only where the owner has selected or authorized the source; synthetic fixtures must not be described as representative of the owner's private projects.

## Risks and unknowns

- Input-token counting adds a preflight request to the same OpenAI service and sends the same manually authorized request context for counting. Its returned count must cover instructions, structured-output schema, and Researcher tool definitions used by the subsequent request.
- A model or API update may change the documented context limit. Keep the model ID and context limit centralized, with tests for the current values and a clear failure when they disagree.
- A higher output allowance can increase latency and per-opportunity cost. Reserve against the maximum before generation and tune one stage at a time from measured incomplete and complete runs.
- Jev support labels assess only supplied evidence. Owner review remains necessary for truth, relevance, tone, and final use.
- Synthetic writing scores do not prove recruiting outcomes. Track callback/interview results only from later owner-labeled application history.

## Milestones

### M1 — Model-aware input and output budgets

Goal: Admit complete, appropriately selected profile context using exact token counts and tune generation ceilings from evidence.

Subtasks:

- [x] Add a Responses input-token counter using the current official request fields, including `instructions`, `input`, `tools`, `text`, and `reasoning` when present.
- [x] Check counted input plus `max_output_tokens` against the current GPT-6 Luna context window before generation.
- [x] Replace UTF-8 byte-derived reserved input tokens with the preflight token count; preserve the separate app-side monthly and per-opportunity cost checks.
- [x] Apply the documented long-context price multipliers above 272,000 input tokens to the full request reservation and settlement.
- [x] Remove the 40,000/32,000 profile character blockers. Pass the full bound profile text unless the exact request would exceed model context or the configured spend limit.
- [x] Tune the Recruiter ceiling against the captured 2,445-token complete response; inspect the remaining stages' output usage before changing their ceilings.
- [x] Add failure-path diagnostics and tests for token-count failure, context overflow, cost-reservation refusal, and incomplete output.

Affected areas: `clue_ai/openai_provider.py`, `clue_ai/application_workflow.py`, tests, Settings disclosure as needed, architecture/product docs, ADR 0024, and this plan.

Dependencies: Current GPT-6 Luna model documentation and configured local synthetic OpenAI credentials.

Acceptance criteria:

- [x] The input-token counter sends only the exact request fields supported by the endpoint and includes prompt instructions, schema, and tools in its count.
- [x] A request within model context reaches generation with the complete selected profile; a request outside the context or spend limit is stopped before generation with a specific local reason.
- [x] The local reservation uses the counted input tokens and configured maximum output tokens, then settles to the provider usage receipt.
- [x] Requests with more than 272,000 input tokens use the documented 2× input and 1.5× output multipliers; requests at or below the threshold use the standard rate card.
- [x] No candidate content is silently trimmed and no incomplete response produces a packet.
- [x] Full profile-routing tests and provider error tests pass.

Validation:

- [x] Unit tests cover token-count payload parity, accepted count response, malformed/missing count, provider errors, context boundary, and reservation settlement.
- [x] Run the application workflow test module, full repository suite, Ruff, byte-compilation, and `git diff --check`.
- [x] Run bounded synthetic OpenAI end-to-end samples after offline tests pass; report per-stage receipts and local cost, with no personal data.

Documentation updates:

- [x] Update product/architecture docs, ADR 0024, PLAN-019/020 where stale, and the PLAN-020 evaluation results for repeated synthetic requests.
- [x] Record model limits, token counts, cost, response completion statuses, and unresolved receipts in the evaluation report.

Applicable specialized skills: `anti-slop`.

Expected Git checkpoint: Commit only after validation; preserve pre-existing uncommitted work and keep the checkpoint on a milestone branch until checks pass.

### M2 — Generation-quality benchmark and meaningful artifacts

Goal: Tune each writing agent against varied role and portfolio cases and prevent technically successful but empty or generic documents.

Subtasks:

- [x] Define a versioned rubric for ATS-readable structure, job-criteria coverage, evidence-based XYZ rewrites, direct/modest voice, specificity, concision, and factual grounding.
- [x] Create synthetic cases with a 12-project profile, two generation role families, senior/junior filter cases, and incomplete or conflicting evidence; keep owner data out of shared fixtures. Broader generation across career levels remains open.
- [x] Evaluate Diagnoser, Recruiter, Rewriter, Researcher, and Hiring Manager separately on completed synthetic runs. Keep Jev matching and claim support metrics separate from GPT writing scores.
- [x] Add a packet quality gate that rejects title-only or materially incomplete documents while preserving owner-editable drafts for review when they contain useful, approved content.
- [x] Tune prompts and stage budgets when live or adversarial evidence exposes a defect; retain the before/after failure evidence and rerun affected synthetic checks. A broader paired quality study remains open.
- [x] Render and inspect exact generated DOCX output and retain regression checks for document text, source order, and structure. Exact visual review passed for the latest synthetic packet.

Affected areas: application prompts/workflow, evaluation corpus and runner, claim support, resume/cover-letter rendering, tests, and product/architecture/evaluation docs.

Dependencies: M1 complete; stable token and cost measurements.

Acceptance criteria:

- [x] Schemas completed for successful fixed synthetic end-to-end cases; a Jev `review` case stops before GPT. Resume source lines remain preserved according to their selected policy.
- [x] Unsupported or contradicted facts are absent from final reviewable documents. Jev match and evidence-support metrics are reported separately.
- [x] Included resume edits map to role criteria and exact cited evidence; unsupported requirements remain gaps.
- [x] The cover letter has substantive, role-specific body text or the packet fails; title-only output cannot pass.
- [ ] Complete a paired baseline/tuned rubric study for each agent and owner-rate the exact packet against the approved voice sample. Available per-agent mechanical and live checks are recorded, but this is not complete.
- [x] Exact synthetic output documents reopen and pass structural and visual inspection.

Validation:

- [x] Run offline adversarial grounding, filter, Jev, and document regression tests.
- [x] Run bounded synthetic live evaluations with per-stage receipts, local costs, Jev outcomes, per-agent checks, and exact artifact inspection.
- [ ] Compare old and tuned prompts side by side on the same fixed cases; failure-driven corrections are recorded, but a paired writing-quality comparison remains open.

Documentation updates:

- [x] Record fixture provenance, metric definitions, failure-driven changes, results, and limitations in the evaluation report and source-of-truth docs.

Applicable specialized skills: `anti-slop`, `documents`, `pdf`.

Expected Git checkpoint: Commit after validation on the milestone branch, keep main unchanged until the PR checks pass, and merge through the reviewed PR.

### M3 — Jev-approved full preparation packet

Goal: Verify the listing decision, generated facts, and final resume/cover-letter/research packet as separate but connected results.

Subtasks:

- [x] Confirm the individual synthetic listing is Jev-eligible before generation and record its exact Jev decision; non-match/review outcomes stop before generation.
- [x] After grounding, require a separate Jev approval of the final tailored resume against the exact listing and saved match snapshot; record its rubric and decision without changing the saved match.
- [x] Require Jev evidence support for each factual block; retain source provenance and distinguish supported, contradicted, and unresolved results.
- [x] Verify a support check cannot mutate Jev's fit score, ranking, eligibility, or saved decision.
- [x] Ensure all selected technical and descriptive profile context is routed only to the allowed generation stages after the individual trigger.
- [x] Validate source bindings, supporting excerpts, and no invented contact addresses on synthetic research fixtures. Real public-source and outreach-contact validation remains part of the manual pilot.
- [x] Confirm every generated document and draft remains local for owner review; the app has no application-submission or email-send action.

Affected areas: Jev, application workflow, local packet UI, research artifacts, data boundaries, tests, ADR 0023/0024, and product docs.

Dependencies: M1 and M2 complete; an owner-selected listing and CV for any real-data run.

Acceptance criteria:

- [x] Jev's saved job-match decision is unchanged by generation and support checking.
- [x] The packet cannot enter review unless Jev explicitly returns `approved` for the final tailored resume; model-reported confidence remains diagnostic and does not replace the decision label.
- [x] Every factual assertion in final documents is supported by its linked source according to Jev; unsupported/contradicted text is excluded and unresolved items are visible.
- [x] A valid, substantive resume and cover letter are available for owner review, or the packet fails with actionable reasons.
- [x] Synthetic research outputs include source links and confidence, and the agent does not invent outreach addresses.
- [x] The real-data path is bound to one manual listing trigger; no send, submission, or bulk generation path is exposed.

Validation:

- [x] Full unit/integration suite, data-boundary checks, and synthetic end-to-end evaluation pass.
- [ ] Run at most one real listing after the synthetic gates pass and the owner selects its listing/CV. Report only sanitized measurements; keep generated content and personal data local.
- [ ] Inspect the exact real packet locally for evidence, job relevance, quality, and formatting; record owner corrections and acceptance without claiming an application outcome.

Documentation updates:

- [x] Update ADRs and current product/architecture/roadmap docs with verified behavior and unresolved calibration questions.

Applicable specialized skills: `anti-slop`, `documents`, `pdf`.

Expected Git checkpoint: Commit on the milestone branch and merge to main only after all applicable checks pass; do not push personal documents, profiles, API output, or local databases.

## Final integration validation

- [x] Fixed synthetic filter and Jev benchmark; per-agent stage evaluation; adversarial support cases; full workflow; structural and visual artifact inspection.
- [ ] One manually selected real listing packet after synthetic acceptance and a locally configured source CV, if available.
- [x] Full test suite (287 passed), Ruff, compile check, docs cross-check, `git diff --check`, and sanitized evaluation results. Branch/CI verification remains before merge.

## Rollback / recovery

- If exact token counting is unavailable or returns incomplete counts, stop before generation and preserve the request for diagnosis; do not fall back silently to character truncation.
- If a new prompt or gate degrades quality, revert that prompt/gate to the last benchmarked version and rerun the fixed corpus.
- Preserve request/usage receipts for uncertain provider outcomes; never retry an unsettled request automatically.
- If Jev support checking changes matching outcomes or lets unsupported facts into files, block packet readiness and correct the responsible code before resuming.

## Progress

- [x] Confirmed the current model documentation lists GPT-6 Luna's context window and max output; fetched current official API docs for exact input token counting.
- [x] Rechecked the model-specific rate page: prompts above 272,000 input tokens use 2× input and 1.5× output pricing for the full request.
- [x] Regression-tested full selected-profile routing; admission depends on exact request token count, model context, and configured local spend controls rather than a character cutoff.
- [x] M1 exact token preflight, context admission, spend reservation, output-ceiling tuning, full regression tests, and synthetic live checks passed.
- [x] M2 versioned writing rubric and meaningful-artifact gate are implemented; latest synthetic packet passed structural/quality gates.
- [ ] M2 broader portfolio and career-level generation coverage, paired per-agent quality comparison, and exact-packet owner review remain open; two role families and exact visual inspection are complete.
- [x] M3 explicit Jev approval of the final tailored resume and complete-packet gates passed the latest synthetic integration.
- [ ] M3 manually selected real listing/CV pilot and exact-packet owner review remain open.

## Implementation discoveries / decisions

- 2026-10-07: The 40k/32k profile limits were app-authored size checks, not limits imposed by GPT-6 Luna. Replace them with exact request token counting and a context-window check instead of arbitrarily increasing character thresholds.
- 2026-10-07: Preserve separate local spend controls. Use exact input-token counts for each generation reservation and provider-reported input/output usage for settlement.
- 2026-10-07: Keep Jev's fit/eligibility decision and evidence-support checks separate. GPT output quality never writes back into Jev's saved match decision.
- 2026-10-07: Require a third, separate Jev decision on the final tailored resume. Use its explicit `approved` label; retain uncalibrated confidence as diagnostic metadata only. A failed Jev or artifact-quality gate persists a non-reviewable output report and creates no documents.

## Completion evidence

M1 completion evidence: exact token preflight, context admission, spend reservation, output-ceiling tuning, and regression tests passed. M2/M3 synthetic evidence includes two role families, a 12-project portfolio, per-agent checks, Jev claim support and tailored-resume decisions, held-out Diagnoser/Hiring Manager challenges, and DOCX reopen plus visual inspection. The latest `SYN-02` run passed with all generated factual blocks supported and the resume explicitly approved by Jev. A repeated `SYN-01` correctly stopped on Jev `review` before GPT generation; an earlier full `SYN-01` run passed. This variance is reported rather than tuned away. The fixed support fixture scored 12/12 against authored labels, not owner judgments. The exact packet has not been human-rated, the synthetic portfolio is only a test fixture, and the real-data pilot awaits its individual trigger.

## 2026-10-07 final tuning checkpoint

Evidence-backed changes retained in this checkpoint:

- Recruiter output allowance increased from 3,200 to 5,000 tokens after a live synthetic response terminated at the former ceiling. The concise-output instruction remains, and current tested responses completed below the allowance.
- The Jev evidence-support decision now follows the explicit categorical response; uncalibrated confidence no longer overturns `supported`. Unsupported numbers/dates still fail a deterministic check, and missing or invalid model decisions remain unresolved. The synthetic 12-case benchmark matched its fixture labels 12/12.
- The final resume reviewer receives the selected structure policy and Recruiter requirement map, uses rubric `tailored-resume-fit-v2`, and returns an explanatory reason code alongside the controlling categorical decision. Tests and a live `SYN-02` case cover both approval and the prior safe `revise` behavior.
- Diagnoser output is filtered through the same exact-reference validator used by the adversarial challenge; fabricated IDs are rejected and measured. Hiring Manager practice now copies questions and answers exactly and returns a scored assessment for each answer.
- Exact current `SYN-02` DOCX files were rendered by exporting through Microsoft Word and rasterizing with PDFium. Both were one page and visually clean. The canonical renderer remains unavailable on this Windows host; the verified fallback is documented.

This completes the available synthetic integration checks for M1–M3, not the broader quality acceptance or M4. Paired baseline scoring, broader career-level generation, exact-packet owner review, representative portfolio coverage, and a real public-research run remain open. M4 awaits the owner’s per-listing trigger with an eligible listing and selected CV. No personal profile data was sent during these evaluations.
