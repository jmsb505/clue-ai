# PLAN-019 — Local application preparation and feedback framework

Status: Core M0–M5 local implementation complete; live provider pilot pending owner configuration; M6 optional worker deferred
Created: 2026-10-06 · Last updated: 2026-10-06
Related: [ADR 0023](../decisions/0023-application-preparation-and-action-boundaries.md)

## Objective

Define a staged, local-first extension that uses the existing Jev model as the authority for candidate/job matching and GPT-6 Luna through the OpenAI API for research, writing, and file generation. The owner reviews generated materials and performs any external action. Optimize for qualified interviews per hour of human effort, with factual accuracy and no duplicate external actions as constraints. Application count is a throughput measure, not the success metric.

The owner approved this product and architecture direction on 2026-10-06. Core local implementation now includes the evidence register, per-listing trigger, bounded Researcher and writing stages, packet generation/review, unsent Gmail draft adapter, and owner-reported outcomes. OpenAI remains disabled until an API key is supplied, separate data-sharing consent is recorded, both owner-set caps are configured, and a current rate card is available. This development checkout deliberately leaves `OPENAI_API_KEY=` blank. No personal profile data, live OpenAI request, or live Gmail action was used for implementation verification.

## Motivation

Clue already discovers and ranks jobs and has a durable manually marked applied tracker. Search history is in progress under PLAN-007. PLAN-019 adds reviewed evidence claims, requirement-to-proof maps, versioned application packets, contact provenance, a per-listing preparation queue, interview-stage feedback, and local receipt records. Long-term cohort analytics, spreadsheet synchronization, scheduled follow-ups, and a background worker remain separate follow-on decisions.

The extension should scale preparation more broadly than cold outreach. It should reduce repeated administration while keeping unresolved facts and consequential actions visible to the owner. Discovery and Jev matching may run through the existing automatic search flow; every research/generation run requires an explicit **Prepare application** action on that individual job listing.

## Current state

- The product definition says the owner reviews a result and applies through the source site. Clue does not prepare full application materials or submit an application.
- [ADR 0016](../decisions/0016-durable-applied-tracker.md) makes the applied tracker a manual, durable snapshot. Marking a role applied records the owner's action; it does not verify employer receipt.
- Clue is a single-user local Python/FastAPI/Jinja/SQLite app. Its Jev integration assesses fit dimensions, filter compatibility, explicit qualifications, and seniority with an existing app-side rolling budget guard. The app is not an always-on background service.
- Current Milan/Italy, workplace, language, paid-role, and seniority requirements remain authoritative in [ADR 0021](../decisions/0021-milan-workplace-and-language-preferences.md), [ADR 0022](../decisions/0022-strict-europe-or-milan-location-gate.md), and the product definition.
- The implementation has routes and local storage for evidence sources/claims, one-request-per-listing generation, bounded sourced research, versioned artifacts, packet approval, mock-interview practice, owner-reported stages, separate receipt evidence, and Gmail draft creation after exact approval. API and Gmail credentials remain separately gated.
- The existing application-stage action happens outside Clue. Clue records the owner's attestation or a locally uploaded receipt; it does not submit a form, send an email, or claim receipt from an owner attestation.

## Desired state

The approved direction is that Clue retains reviewed candidate claims and private evidence locally; creates immutable job snapshots and requirement-to-proof maps; prepares versioned CV, cover-letter, and answer packets only for individually triggered opportunities; queues next actions; researches a small number of public professional contacts with provenance; records owner-reported outcomes; and summarizes interview stages and recurring skill gaps.

The roles are deliberately separate: the existing Jev integration is the sole matching validator; the OpenAI API agent (`gpt-6-luna`, `reasoning.effort=max`) researches public information and prepares tailored CVs, cover letters, application answers, and outreach drafts; Clue's ordinary code enforces gates, budgets, schemas, storage, and permissions; and the owner reviews the finished package and performs every external send or application submission. Preparation state and application stage remain separate. The applied tracker remains authoritative for exclusion from job discovery.

For each opportunity, the agent may use the owner-approved technical profile as the evidence source, the descriptive profile for confirmed writing preferences, and several existing CVs as content/layout references. The owner can set a default base, mark which CVs may be compared, and choose whether structure should be preserved or improved. The agent may recommend or select the best permitted starting CV for a role, then versions the result without changing any original. It handles research and drafting without asking for approval at each intermediate step; it asks the owner only when a material fact or policy decision is missing or conflicting. A Gmail draft is created only after the owner approves the exact recipient, subject, and body. The owner then sends it manually from Gmail.

## Source material and evidence limits

This proposal synthesizes the supplied application framework, job-search research, technical profile, descriptive profile, and `Writing_Skills_Research_and_Clue_Integration.md`. These source files remain private inputs and are not copied into this repository.

The research report references [Ashby's referral analysis](https://www.ashbyhq.com/talent-trends-report/reports/referrals), [Ashby's recruiting operations benchmarks](https://www.ashbyhq.com/talent-trends-report/reports/recruiting-operations-benchmarks-talent-trends), and [LinkedIn's recruiter outreach guidance](https://www.linkedin.com/business/talent/blog/product-tips/tips-for-writing-inmails-from-linkedin-recruiters). Referral differences are observational and do not predict an individual conversion multiplier. Recruiter-to-candidate outreach evidence may not transfer to candidate-to-manager messages. Hiring-manager outreach, posting cadence, conference networking, and open-source-to-job conversion have weaker direct evidence in the report; test them within a time budget.

The writing review cites [Liang et al. (2023)](https://arxiv.org/abs/2304.02819), [RAID (ACL 2024)](https://aclanthology.org/2024.acl-long.674/), and [Tufts et al. (NAACL Findings 2025)](https://aclanthology.org/2025.findings-naacl.271/). Their results show detector false positives or robustness/sensitivity limits in the specific samples and conditions studied. They do not establish that every detector fails, or predict detector behavior on short application messages. The shortlisted writing skills were not benchmarked on the owner's drafts, and the cited research does not establish a hiring benefit. Treat detector output as an uncertain external observation, not a writing-quality or authorship score; detector scores are not an acceptance criterion.

Google's [resume-writing guide](https://services.google.com/fh/files/misc/resume-writing-tips-for-veterans-2021.pdf) recommends the “Accomplished X as measured by Y by doing Z” pattern. Clue uses it as an optional evidence-organization template; the guide does not justify adding metrics that the candidate cannot substantiate. Greenhouse documents [specific resume parsing failures](https://support.greenhouse.io/hc/en-us/articles/200989175-Unsuccessful-resume-parse) and [supported upload formats](https://support.greenhouse.io/hc/en-us/articles/360052218132-Supported-formats-for-resumes-cover-letters-and-other-candidate-uploads). These vendor-specific notes inform the Diagnoser's observable checks; they do not reveal other employers' parsers, configurations, or screening outcomes.

## Scope

- Preserve the local single-user product and existing stack; add no hosted CRM, vector database, generic agent framework, or second job index.
- Add an OpenAI Responses API generation provider using `gpt-6-luna` with `reasoning.effort=max`, subject to the separate budget and data-sharing gates below. Jev remains the matching authority and its existing budget is unchanged.
- Define a reviewed claim register, role-family evidence map, durable preparation queue, versioned packet, controlled contact research, interview feedback, and stage-level reporting.
- Build in dependency order: reviewed evidence → durable queue → bounded OpenAI generation and local packet rendering → selective public contact research → outcomes and feedback. Submission remains a manual owner action and has no Clue adapter in this plan.
- Keep a concise “Next actions” queue. Prioritize interviews/deadlines, important replies, application-ready packets, contact decisions, due follow-ups, and strategic review.
- Treat thresholds and cadence from the supplied job-search report as configurable starting heuristics, not validated optima.

## Out of scope

- Application submissions, sent messages, and any autonomous external action.
- Universal auto-apply, bulk outreach, logged-in social-network scraping, automated connection requests, guessing email addresses, or bypassing blocks.
- Inventing experience, motivation, availability, compensation, work authorization, or answers to employer attestations.
- Automated proctored assessments or employer-prohibited AI answers. Route these to the owner with the applicable instruction attached.
- Committing personal profiles, CVs, contacts, application answers, generated packets, or personal claim values to this public repository.
- Uncapped API usage, silent model/provider fallback, model-authored changes to Jev decisions, direct agent-controlled email/Gmail access, message sending, employer-site writes, arbitrary local file access, and any application-submission adapter. Owner-approved creation of an unsent Gmail draft through a separate adapter is the only planned external write.

## Source-of-truth impact

- This plan and ADR 0023 are the source of truth for the implemented local preparation flow, its disabled-by-default provider gates, and deferred follow-on work. Manual application submission and message sending remain outside Clue.
- The product definition, architecture overview, roadmap, and accepted ADR 0023 record the Jev/OpenAI division, separate budgets, review gates, and current implementation state.
- Personal source documents are inputs, not repository artifacts. Public docs contain schemas, policies, and synthetic examples only.

## Existing decisions and constraints

- **Local storage and one user:** preserve [ADR 0004](../decisions/0004-single-user-local-app.md); use additive SQLite migrations and existing local deletion controls.
- **Model roles:** existing Jev remains authoritative for candidate/job fit and filter/qualification assessment. GPT-6 Luna is the selected generation/research model; it must not write or override Jev scores, filter states, or qualification decisions. Python owns deterministic gates, state, and tool permissions; the owner reviews truth and final artifacts.
- **Jev-to-GPT handoff:** run existing deterministic hard gates and Jev assessment first. Persist and pass a read-only, versioned Jev snapshot (run ID, model/rubric versions, fit dimensions, filter result, explicit qualification checks, and seniority assessment) to the generation stage. A Jev `conflict` blocks packet generation; `review` or unassessed results require owner resolution; only the existing policy's eligible match path proceeds. GPT may flag a suspected mismatch for owner review, but cannot recalculate, rank, revise, or overrule Jev. Re-run Jev only when its inputs or rubric materially change, not once per generated file.
- **Separate budgets:** preserve [ADR 0006](../decisions/0006-jev-scoring-and-budget-guard.md)'s $4 rolling 30-day app reserve and $5 owner ceiling. OpenAI API usage is an additional provider budget, never paid from or merged with Jev's ledger. Clue must not call OpenAI until the owner configures both a monthly hard app-side cap and a per-opportunity cap. Until then, API generation is disabled; local templates and the existing search/Jev workflow remain available.
- **OpenAI API setting:** use model ID `gpt-6-luna`, the [Responses API](https://developers.openai.com/api/reference/resources/responses/methods/create), and `reasoning.effort: "max"` as requested. The [model guide](https://developers.openai.com/api/docs/models/gpt-6-luna) documents the model and current reasoning options. Use [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) for artifact schemas; verify account availability during implementation. Do not silently lower effort or substitute another model if the request fails.
- **Current price reference:** the official model page lists $0.10 per million input tokens and $0.50 per million output tokens as of 2026-10-06; web-search and other tool charges may be additional. This is a volatile snapshot for planning, not a permanent rate or a value to hard-code. Recheck prices and account controls before implementation and after model/rate-card changes.
- **Data-sharing gate:** OpenAI use requires its own explicit disclosure and opt-in, separate from Jev consent. Send only the opportunity packet, relevant reviewed claim excerpts, and approved style guidance needed for that draft. Exclude raw writing samples by default; do not send contact details that are not needed. Verify current API data controls and terms before enabling personal data transfer; their status is unknown in this planning document.
- **Human action boundary:** the API agent may research, draft, revise, and stage local artifacts for review. It has no send, connection-request, application-submit, logged-in browser, shell, arbitrary filesystem, or unrestricted database tool. After reviewing a complete outreach draft, the owner may trigger a separate adapter to create an unsent Gmail draft; the owner sends it manually. The owner also manually completes every application submission.
- **Profile and CV inputs:** the owner may add multiple existing CVs locally, set a default or let the agent choose among permitted references for a role, and choose whether to preserve their structure or allow improvements. Preserve originals and version all tailored copies. Use the technical profile for supported claims and the descriptive profile only for owner-confirmed tone and preferences. Do not treat either profile or old CV text as independently verified proof when evidence conflicts.
- **Gmail draft boundary:** the agent writes outreach drafts but has no Gmail access. After reviewing the exact To/Subject/body, the owner may trigger a separate adapter to create an unsent draft, then sends manually. See the Gmail draft handoff below for the OAuth scope and current Codex connector boundary.
- **Applied-state integrity:** preserve [ADR 0016](../decisions/0016-durable-applied-tracker.md). A packet or contact task must never mark a job applied. Only an owner attestation or supported receipt creates a submitted event, with its evidence strength recorded.
- **Eligibility:** apply the current product definition and ADRs 0021/0022. A hard blocker is an excluded state, not a low tier; unknown evidence creates a verification task. Do not infer work authorization from citizenship or location.
- **Personal facts:** keep display name, education status, work authorization, availability, and other answer-bank values private and owner-reviewed. Do not infer a completed degree or authorization from an in-progress education record or citizenship. Keep dates out of user-facing tracker columns/cards; use internal timers for freshness and follow-ups, with action labels such as “Follow-up ready.”
- **Profile evidence:** the technical profile is an index of candidate claims, not proof by itself. Distinguish measured result, implemented code, demonstration, coursework, exposure, and planned work. Only reviewed claims may enter outgoing material.
- **Role-family evidence:** use four lanes—applied AI/LLM systems, computer vision, edge/inference, and AI product/backend. For AI/LLM work, distinguish implemented contracts, evaluation, retrieval, and recovery from roadmap items. For vision, keep dataset, split, model/version, metric, hardware, and personal contribution distinct. For edge work, show measured deployment without implying deep firmware specialization. For product/backend work, use implementation evidence such as typed contracts, persistence, tests, and UI integration; do not imply enterprise-scale ownership. Keep cloud, Kubernetes, Terraform, distributed ML, and production SRE as development areas unless reviewed evidence supports a stronger claim. Specific project names and claims stay in the local register.
- **Profile preferences and voice:** use the descriptive profile only for owner-confirmed interaction and writing preferences; it is not a corpus of authored prose or a basis for inventing personality. Build a private voice profile only from owner-selected writing samples, label original writing separately from AI-assisted revisions the owner approved, and keep samples/profile data local and deletable.
- **Metric discrepancy:** the supplied materials describe an older FPGA Dice result near `0.674` and a later V4 result near `0.7647`. Keep experiments separate; verify repository revision, data split, metric definition, hardware, baseline, and personal contribution before approving either claim.
- **Research limits:** referral comparisons in the supplied report are observational, not a personal causal multiplier. Recruiter-to-candidate outreach evidence may not transfer to candidate-to-manager outreach. A/B/C thresholds, referral wait, follow-up timing, and weekly capacity are hypotheses to calibrate.

## Proposed workflow and policy

**Automatic versus owner-triggered work:** The existing search flow may automatically discover listings, deduplicate them, apply deterministic hard filters, run Jev on eligible candidates, and update ranking/history. These steps do not invoke the Researcher or any GPT writing/practice stage. Each eligible listing shows its own **Prepare application** button. Only the owner's click for that specific listing creates a preparation request; there is no automatic preparation for every mined, selected, or queued listing, no bulk-start action, and no scheduled worker that starts preparation without a new owner trigger. The click starts one complete, bounded packet run for that job: role/company/contact research as enabled, resume diagnosis, evidence mapping, tailored CV and application materials, and outreach draft. Optional interactive interview practice has its own explicit trigger on the same listing. The final packet still requires owner review; Gmail draft creation and sending/submission remain separate manual actions.

1. Reuse discovery, current hard filters, and exact-identity deduplication. Verify the official vacancy and preserve its text, URL, capture time, and content hash. Discovery itself does not generate application material. Clue does not submit applications.
2. Run the existing Jev assessment as part of the search flow and store its versioned result as the matching authority. Do not ask GPT to re-score the candidate or decide whether a role matches. A Jev conflict blocks preparation; review/unassessed states wait for owner resolution. An enabled **Prepare application** action is available only after deterministic gates pass and Jev returns an eligible `match`.
3. Build a requirement map from the full available job description. Keep required, preferred, inferred, and unknown conditions labeled. The harness maps requirements to owner-reviewed claim IDs; GPT may suggest mappings but code validates claim membership and Jev eligibility.
4. Keep Jev fit, any separate treatment tier, and contact confidence as distinct values. Proposed starting treatment rubric: technical overlap 30, level/eligibility 20, distinctive proof 20, human accessibility 10, personal preference 10, and freshness/process opportunity 10. A: 80–100, B: 60–79, C: below 60. Calibrate against owner judgments before treating these bands as useful.
5. After the individual **Prepare application** click, run a dedicated Researcher role. It gathers role, company, team, and—when contact research is enabled—public professional-contact evidence through the existing Scrapling-backed Clue crawler. It receives the job snapshot and public search terms, not the CV, profiles, private claims, or other personal data. It returns a versioned research packet with source URL, page title, observation time, supporting excerpt, fact-versus-inference label, confidence, and unresolved gaps. It cannot draft application prose or contact the person. M2 establishes role/company research; M3 extends the same role to selective contact research.
6. Pass the read-only Jev result, reviewed technical claims, confirmed descriptive-profile style preferences, permitted CV references, and cited research packet to the relevant writing/practice stages. Use separate stage prompts and strict output schemas, all on GPT-6 Luna with `reasoning.effort=max`. Only the Researcher receives crawl/search tools; the four later stages cannot browse, fetch pages, edit files, or invoke external actions. The local orchestrator controls stage order and passes typed, versioned outputs between stages.
7. Validate schemas, source links, claim IDs, artifact limits, and input revisions in ordinary code. Render DOCX/PDF locally into a versioned draft area; preserve every source CV. Show the complete packet, research provenance, exact changes, unresolved questions, and Jev assessment at one final review checkpoint. Any material input or output edit invalidates that review.
8. Use cited public contact findings to prepare one concise, role-specific outreach draft and an optional follow-up reminder. Do not guess contact details or repeat research from the writing stages. Clue never sends messages or connection requests. Replies, closure, withdrawal, no-contact requests, or interview progression cancel stale reminders.
9. After final review, the owner may explicitly choose **Create Gmail draft** for the approved outreach To/Subject/body. The separate Gmail adapter creates an unsent draft; the owner edits or sends it manually in Gmail. For applications, the owner opens the official form, uses the reviewed answers/files, and submits manually. Clue can record the resulting owner attestation or receipt afterward. Keep self-assessment separate from employer feedback and unresolved applications separate from rejections.

### Research and writing/practice stages

These are role-specific GPT-6 Luna calls coordinated by Clue, not autonomous agents with independent credentials or direct filesystem access. The Researcher is a separate stage with the only public-crawl tools. The Diagnoser, Recruiter, Rewriter, and Hiring Manager stages receive only their needed local inputs and typed results from earlier stages. They use `reasoning.effort=max` as requested; the pilot records quality, latency, and cost per successful packet so the owner can judge the trade-off.

Every preparation run starts with one owner click on **Prepare application** for one eligible listing. Bind that request to the job identity and snapshot, Jev run, selected CV, profile/claim/policy revisions, and request version. Reserve OpenAI budget only after the click and before the first API call. Repeated clicks for an active request are idempotent; if the job or Jev snapshot has gone stale, refresh it and require a new click. A listing without a trigger uses no Researcher, GPT generation, contact-crawl, or OpenAI budget. The full packet run covers that listing only. Hiring Manager practice remains an optional separate action on the same listing because it is interactive and may need extra usage.

1. **Researcher — source gathering.** Find and summarize relevant public role, employer, team, and permitted contact information. Every retained statement must point to a source and observation time and distinguish quoted facts from inference. The stage returns evidence and unknowns, not claims about Juan or finished outreach prose. Writing/practice stages cannot crawl or treat page text as instructions.
2. **Diagnoser — resume readability audit.** Clue extracts the selected CV locally and compares extracted text/section order with the document. The stage flags concrete layout or extraction risks and identifies the affected section or line where possible. It reports risks and confidence; it cannot say that a line was screened out by an employer's ATS, reproduce an unknown employer configuration, or explain why a person was ghosted. Greenhouse's own support material documents parser failures involving tables, columns, headers/footers, text boxes, images, and formatting; those observations support a general readability audit, not a universal ATS simulator.
3. **Recruiter — job-description evidence map.** Break the captured job description into required, preferred, and unclear criteria, then map each criterion to reviewed claim IDs and CV sections. Report `supported`, `partial`, `not shown in this CV`, or `uncertain`, with the evidence and gap. If a transparent coverage figure is shown, define it as the share of evaluable criteria with supported CV evidence; it is a document-coverage measure, not a candidate-fit, screening, or interview-probability score. Jev remains the only matching validator. The recruiter stage displays its saved result read-only and cannot change it.
4. **Rewriter — evidence-bound XYZ suggestions.** Improve selected weak bullets with Google's accomplishment pattern: what was accomplished (X), how the outcome was measured (Y), and what action produced it (Z). Use a metric only when a reviewed claim supports that exact number and its scope. A number is not required for every bullet. If no verified metric exists, keep a clear qualitative result or ask the owner; never estimate, backfill, or manufacture a number. Return a proposed replacement tied to the original bullet and supporting claim IDs; Clue applies approved patches only to a copy of the selected CV.
5. **Hiring Manager — interview practice.** As a separate optional practice stage, ask challenging, role-specific questions grounded in the job criteria, the owner's documented experience, and relevant sourced context. The owner supplies each answer. Give transparent practice feedback on relevance, evidence/specificity, reasoning, clarity, and reflection, with reasons and a next practice prompt. Do not supply an invented autobiographical answer, predict the actual interview, or present practice ratings as Jev fit or an employer's hiring score.

Jev helps at the eligibility/matching gate and provides read-only context to the Recruiter. Its explicit qualification checks and supported skill/experience gaps can help select interview-practice topics, but Jev does not parse ATS layouts, judge prose, validate XYZ wording, or score interview answers. Do not rerun Jev for a stylistic CV edit; rerun it only when the job/profile evidence, applicable preferences, or Jev rubric materially changes. A content-coverage gap is not by itself a qualification failure.

Tier estimates must not form a circular score: accessibility starts unknown and is researched only for promising roles. Do not penalize strong roles because no hiring manager is public. Overflow remains queued with priority and due actions; there is no requirement to contact everyone. The report's proposed 2–4 A-tier research packets per week and daily discovery capacity are trial settings, not quotas.

### Writing quality and voice

Apply a short writing procedure after the evidence-grounded draft: select reviewed evidence, draft for the specific reader, edit against an owner-confirmed voice profile, check factual changes, then present the exact final text for review. The procedure improves clarity and voice; it is not an attempt to pass AI detectors.

- Invite the owner to select roughly 5–10 authored samples across professional messages, project explanations, and applications. This is a starting range, not a requirement. Label AI-assisted revisions separately, and include one as a voice reference only when the owner explicitly approves it. Do not mine private correspondence automatically or use chat typos as a target style.
- Keep source samples and the private, revisioned voice profile on the device under `.data/`, subject to explicit review and existing full-deletion controls. Never put sample text or personal voice-profile values in Git. Each API request carries the profile revision and only the approved style guidance needed for that draft; raw samples are excluded by default and require explicit selection and preview before any API request.
- Preserve correct grammar, names, dates, numbers, technical scope, causal claims, qualifications, uncertainty, and useful technical/ATS terms. Never invent facts, enthusiasm, conversations, memories, or intentions. If a material detail is missing, ask the owner or narrow the claim.
- Edit repeated generic phrasing in context. Do not mechanically swap synonyms or ban valid passive voice, punctuation, contrast, lists, or technical vocabulary. Keep different priorities for hiring-manager messages, recruiter email, CV bullets, application answers, and technical project pages.
- Return the final artifact, unresolved questions, and a concise internal change summary. Keep the summary and review notes out of employer-facing fields.

| Output | Writing priority |
|---|---|
| Hiring-manager message | A specific team connection, one relevant proof point, and a small ask. |
| Recruiter email | Exact role, relevant background, and practical eligibility/availability details. |
| CV bullet | Action, scope, documented result, technical terms, and units. |
| Application answer | Answer the question directly using true experience and genuine intent. |
| Technical project page | Method, evidence, trade-offs, and limitations. |

### Review queue

Order the queue by interview/deadline, important reply, application-ready packet, contact decision, due follow-up, and strategic review. An eligible unrequested listing shows **Prepare application** on that listing's own card; one click starts work only for that opportunity. Show preparation status (`not_requested`, `preparing`, `needs_info`, `ready`, `stale`, `skipped`) separately from application stage. A card shows company/role, Jev result, fit thesis, eligibility evidence, up to two proof points, exact material changes, unresolved questions, and the next action. Final packet review offers approve, edit, skip, defer, and request-clarification actions. Batch review may group completed packets, but it never starts preparation in bulk and each approval remains bound to its own artifact version and destination. Measure total owner time, including corrections and unknown answers, before claiming an effort reduction.

## Proposed data and execution design

### Components

| Proposed component | Responsibility |
|---|---|
| `evidence.py` | Claim source, revision, review state, role-family scope, permitted wording, and limitations |
| `preparation.py` | Opportunity snapshots, Jev assessment linkage, per-listing owner trigger, requirement maps, owner-selected CV base/layout references, treatment components, and packet versions |
| `agent_bridge.py` | OpenAI Responses API adapter, scoped context assembly, strict output schema, usage reservation/settlement, and fail-closed tool-call validation |
| `research.py` | Agent-directed calls to the installed Scrapling adapter for bounded public crawl/search, host and response limits, provenance capture, and prompt-injection-safe content handling |
| `documents.py` | Deterministic local DOCX/PDF rendering and artifact versioning; the model does not write arbitrary paths |
| `contacts.py` | Contact provenance, confidence, route, function match, and suppression |
| `gmail_drafts.py` (optional) | Owner-triggered Gmail draft creation after final message review; no send operation |
| `workflow.py` | Typed transitions, idempotent per-listing trigger checks, due actions, approval/version checks, and leases; no background auto-start |
| `feedback.py` | Application events, interview stages, and mature-cohort analytics |

These are proposals, not existing modules or commands.

### Durable records and state

Proposed records: `candidate_claims`; owner-selected `cv_sources` with a Clue-managed storage ID, role as content/layout reference, and revision; an optional private `writing_profiles` record with owner-reviewed preferences, revision, and source-sample labels/references; `opportunities` with stable identity, immutable job snapshot/hash, profile/policy revision, Jev run/model/rubric references and treatment components; `application_packets` with selected base CV, artifact version, claim references, voice-profile revision, model/prompt/schema identifiers, source links, validation result and review state; `contacts` with opportunity links; `gmail_drafts` with owner-approved recipient/subject/body hash, Gmail draft ID, creation state and reconciliation state; `workflow_actions` with dependency, state, due timer, payload hash and approval scope; `openai_usage_ledger` with request/opportunity/artifact IDs, model/reasoning setting, input/output/reasoning usage, tool charges, price-card revision, reserved/settled amount and request status; `consents` with provider/purpose/revision/time; `application_events`; and `interview_stages`.

Keep preparation (`not_requested`, `preparing`, `needs_info`, `ready`, `stale`, `skipped`), application stage (`unsubmitted`, `submitted`, `screen`, `technical`, `final`, `offer`, `rejected`, `withdrawn`, `no_response`), and action execution (`draft`, `approved`, `running`, `succeeded`, `failed`, `outcome_unknown`, `cancelled`) as separate state machines. Search and Jev results may exist while preparation remains `not_requested`; only the explicit trigger transitions it to `preparing`.

Keep current `applications(job_id)` and `application_urls` authoritative for applied exclusion. An opportunity and packet must survive job-index expiry, so do not make their lifecycle depend on a cascading foreign key to `jobs`. Use transactional additive migrations with backup/rollback checks. Ordinary search reset retains preparation and feedback; full personal-data deletion removes imported CV sources, claims, writing profiles and samples, packets, contacts, Gmail linkage/metadata, actions, and events. A Gmail draft already created remains in the owner's mailbox until they delete it there; Clue has no Gmail delete tool. Suppression retention requires an explicit owner choice.

Key an external draft-creation operation by opportunity, action type, destination, and artifact version. Approval binds to payload hash, recipient/destination, and permitted action; changes invalidate affected approvals. Gmail draft creation can succeed even if the local request times out. Record an uncertain state, reconcile by draft ID or approved content hash, and check before retrying to avoid duplicate drafts. Clue never retries into a send operation.

### OpenAI agent, tool harness, and untrusted input

Keep orchestration in the local Clue process. It assembles a narrowly scoped, versioned request for the OpenAI Responses API using model ID `gpt-6-luna` and `reasoning.effort: "max"`. The agent returns strict structured output for a defined artifact schema. [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) enforce response shape, not factual truth; ordinary code checks IDs, revisions, source URLs, lengths, and policy, and the owner reviews meaning.

Only the Researcher call receives function tools. Its allowlist is limited to reading the immutable job snapshot and requesting public web searches or bounded page fetches through Scrapling; Clue validates each proposed call against the opportunity scope, public-host rules, page/request budget, source policy, and current consent. Writing/practice calls receive no tools. Clue validates their structured responses and saves approved proposals through ordinary local code; a missing or conflicting fact is presented to the owner for resolution. Do not expose arbitrary filesystem, database, shell, general network, logged-in browser, Gmail, social connection, message-send, application-submit, or employer-form tools to any model stage. The local renderer writes only to Clue's controlled artifact directory and never overwrites a selected CV or original source documents. No API call may change JEV records, Jev scores, hard-gate results, filter states, qualification checks, or seniority decisions.

The GPT model receives no Gmail credentials or mailbox tools. Only the separate owner-triggered adapter described below can create Gmail drafts after final review.

The per-opportunity context may include the bounded job-description snapshot/hash, read-only Jev result and rubric/model identifiers, the selected CV's locally extracted content and structure needed for tailoring, relevant owner-reviewed claim IDs/evidence excerpts, approved answer facts, output schema, and minimum approved style guidance. Send only the selected base CV and the minimum content needed; do not send other stored CVs or the full technical/descriptive profiles by default. The selected CV content is personal data and requires the separate OpenAI opt-in. Raw writing samples stay local and are excluded; any sample use requires owner selection, preview, and separate consent. Contact-search queries use employer/role/team terms only, not CV text or private claims.

Treat job descriptions, search results, and fetched pages as untrusted data, never as instructions that can alter policy or grant tools. Public-source text must not instruct the agent to reveal private context, modify the Jev result, or take an external action. Capture source URLs, timestamps, and excerpts, and show those with generated material. Contact details remain tentative until checked against a public source. Never guess email addresses. Revalidate that all request revisions still match before saving output; stale requests and unknown fields fail closed into owner review.

### Gmail draft handoff

Research and compose outreach messages locally in Clue. Present the finished contact evidence and exact To/Subject/body in the final review screen. Only after the owner approves that content may they click **Create Gmail draft**. A separate adapter creates an unsent message in Gmail's Drafts; the owner may edit and send it manually. Do not expose Gmail read, update, delete, or send methods to the GPT agent. The current Codex Gmail connector is available only in this assistant session and does not automatically become a tool for a Clue API agent.

The Gmail API's [`users.drafts.create`](https://developers.google.com/workspace/gmail/api/guides/drafts) creates a message with the `DRAFT` label. The [`gmail.compose` OAuth scope](https://developers.google.com/workspace/gmail/api/auth/scopes) also permits sending and is restricted, so the adapter must isolate its credential and implement only draft creation. Bind creation to the owner-approved recipient/subject/body hash and keep the returned draft ID. If a create call times out after dispatch, do not retry automatically; have the owner check Gmail Drafts and reconcile before another attempt. If the owner requires a credential that cannot send at all, keep the approved email in Clue or offer a local `.eml`/copy-to-Gmail handoff instead. Clue does not read, update, or delete existing Gmail messages/drafts, so the owner manages the created draft in Gmail.

### OpenAI budget and cost controls

| Budget lane | Current policy | Gate before use |
|---|---|---|
| Jev matching | Existing $4 app-side reserve per rolling 30 days toward the owner's $5 ceiling; preserve the current Jev ledger and behavior. | No change in this plan. GPT usage never consumes Jev reserve. |
| OpenAI generation/research | A distinct app-side ledger and provider spend. Owner has not set the dollar amount yet. | Disabled until both an owner-set monthly cap and per-opportunity cap are configured, and OpenAI data-sharing consent is recorded. |
| Public web tools | Query/page usage can add provider or local crawl costs and consumes time. | Count tool charges in the OpenAI request reservation where billed by OpenAI; apply per-opportunity query/page limits and existing public-source host/rate/response-size rules. |
| Gmail draft handoff | Separate Google OAuth/API quota and permission; current account setup is not verified. | Create unsent drafts only after final owner approval; no send tool. Verify the minimum supported scope and account requirements before implementation. |

For planning only, the official [GPT-6 Luna model page](https://developers.openai.com/api/docs/models/gpt-6-luna) listed $0.10 per 1M input tokens and $0.50 per 1M output tokens on 2026-10-06. Tool charges may be additional, and model prices/account terms can change. Recheck the rate card and tool prices during implementation and whenever the configured model or price-card revision changes; do not treat these values as permanent or hard-code them as the spend guard.

Before each API request, reserve a conservative estimate from the configured rate-card revision using input/output limits plus applicable tool-call charges. Refuse the request if the reservation would exceed either cap. On completion, settle against provider-reported usage and recorded tool charges, release unused reservation, and store the receipt and rate-card revision. If a request times out after dispatch or usage cannot be reconciled, retain the conservative reservation and require reconciliation before retry. Disable API work when the cap is reached, usage is missing, pricing is stale, or consent is absent; do not silently downgrade effort, switch providers, or fall back to another paid model. A deterministic local template remains available. Configure provider-level budget alerts/limits when available, but do not treat them as a substitute for the app-side guard.

Keep the API key in local server-side configuration, never in browser code or generated artifacts. OpenAI receives only the approved request payload; the owner must separately opt in to sending personal profile-derived data. At implementation, verify current API terms, retention/data controls, and account billing behavior and document what was verified. Do not imply deletion or non-retention beyond verified provider controls.

### Contact data and outreach

Use the job post, company/team pages, engineering blogs, published technical work, public GitHub identities, and available search results. GPT may conduct this research through the bounded read-only web tools above. Do not depend on logged-in scraping, automated connection requests, or bulk enrichment. Retain only a professional name, company, public role, team evidence, source URL and observation time, contact route, confidence, function match, and suppression state.

Distinguish a verified job owner, likely team lead, relevant engineer, and recruiter. A current title does not prove vacancy ownership; a GitHub contribution does not prove current employment or willingness to refer. Prefer a verified same-function warm contact; otherwise choose a job-linked manager, exact-team senior engineer, or relevant recruiter. No verified contact is a valid result. Never guess an email address or send parallel near-identical messages for several roles at one employer.

Start with one primary message per role: the exact vacancy, an observed team problem, one reviewed proof point, and a small ask. Use roughly 60–90 words when the channel permits, then preserve the owner's edited voice. Do not say “I applied” before submission is recorded. One follow-up around 5–7 days is a configurable report heuristic, canceled on a relevant reply or closure.

## Autonomy and human review

| Mode | Behavior | Gate |
|---|---|---|
| Prepare | Research public sources, draft and revise materials, validate, render, and queue for review without external writes | First release after Jev, budget, data-consent, and packet gates pass |
| Gmail draft | Save the exact approved outreach email as an unsent Gmail draft; no send action is available to the agent or Clue workflow | Owner reviews recipient, subject, and body, then explicitly clicks Create Gmail draft; separate Gmail authorization is configured |
| Application handoff | Link the official destination and present exact materials; the owner checks them and manually fills/submits outside Clue | Owner reviews each artifact and independently performs the application |
| Scheduled preparation (optional) | Run bounded read-only discovery/research and draft preparation into the local review queue; never send messages, submit applications, or answer employer forms | Separate owner decision, stop control, per-run and spending caps, and supervised evidence |

GPT cannot make salary/availability commitments, complete legal attestations, resolve ambiguous eligibility, or answer sensitive optional forms as though verified. It asks the owner or marks the field unresolved. Keep the main queue focused on owner decisions and due work.

Represent `prepared`, `submitted_by_owner`, and `submission_confirmed` distinctly. The owner may record their action and any supported receipt after acting outside Clue; a packet alone never changes the applied tracker. A generic receipt is not a qualified interview. Preserve the exact approved artifact version in the packet record. Repeated owner marks must preserve the existing first-mark date.

## Feedback and evaluation

Track channel, treatment tier/version, role family, CV/proof and voice-profile revisions, verified referral status, contact type, useful replies, stage transitions, outcome maturity, packet corrections, writing-review ratings, and human minutes. Report:

- qualified interview yield per qualified application;
- qualified interviews per human preparation/review/outreach hour;
- OpenAI cost per generated packet and per opportunity, including research-tool charges and owner correction time;
- unsupported claims, wrong contact facts, owner corrections, and missing answers per packet;
- clarity, naturalness, voice match, role relevance, factual changes, and owner correction effort for the writing pilot;
- tier conversion with counts and mature/pending denominators;
- verified referral versus ATS-only and contact-type outcomes;
- completed-stage progression rates;
- duplicate actions, stale approvals, uncertain outcomes, recovery events, and cost.

Treat channel comparisons as descriptive unless controlled evidence supports more. A-tier and referred candidates are selected differently. A useful first calibration labels roughly 20–30 historical or synthetic roles across accepted and excluded groups; this is a pilot sample, not statistical validation. Keep unresolved cases as awaiting response until a defined observation window matures. Review recurring interview topics with controlled tags, separating self-perceived gaps from interviewer feedback.

## Supporting skills / tools

- Keep the owner-approved preparation instructions and role-specific procedures versioned with the packet contract. If a repo-local `.agents/skills/clue-application-workflow/` is useful for operating the workflow, include the separate Researcher boundary and Diagnoser, Recruiter, Rewriter, and Hiring Manager procedures there; it remains guidance only. The bounded Responses API calls plus local Clue harness perform generation and own persistent state.
- Put the writing procedures in that same skill; do not add an overlapping always-on writing skill. The reviewed [hannsxpeter/humanizer](https://github.com/hannsxpeter/humanizer) and [adewale/anti-slop-writing](https://github.com/adewale/anti-slop-writing) are references, not runtime dependencies. Prefer an original concise procedure and verify the exact upstream revision and license before copying any material.
- Keep schema/playbook references shared and host-independent. Do not assume a skill installed in Codex Work appears in the Windows checkout or other coding tools.
- Test the future skill on synthetic cases: missing contact, conflicting metric versions, stale packet, unsupported required answer, employer no-AI instruction, prompt injection in a job description, unauthorized send request, missing experience, a valid technical use of “robust”, justified passive voice, a necessary three-part list, a very short message, and a draft that already reads naturally.
- Use `ui-ux-research` with an appropriate frontend skill for substantial queue UI work. Use current official library docs when implementation selects or changes a library/API.

## Dependencies

- Owner review of reusable technical claims, role-family relevance, answer-bank facts, and interaction defaults.
- Owner-set OpenAI monthly and per-opportunity dollar caps, separate API data-sharing opt-in, verified current API controls, and an implementation rate-card revision.
- Existing backup/deletion behavior and applied snapshots preserved by additive migrations.
- A versioned Jev assessment snapshot interface and the validated tool/schema contract before the GPT agent is enabled.

## Risks and unknowns

- A model can cite an approved claim while still distorting it. Human review and claim-level evidence are required.
- The descriptive profile is interpretive and may be wrong; use only low-risk preferences that the owner confirms.
- Public contact information may be stale or misattributed. Retain source and observation time; allow suppression and deletion.
- Referral and outreach evidence may not transfer to the owner's roles or market. Measure personal outcomes before increasing effort.
- API timeouts can incur charges even when the local caller did not receive output. Reserve conservatively and reconcile usage before retry.
- A model can make inaccurate paraphrases or infer unsupported facts even when given approved claims. Schema validation does not establish truth; owner review remains required.
- Public pages may be stale or contain prompt-injection text. Preserve provenance, enforce public URL limits, and treat page text as data.
- Account-level spending controls may be alerts or delayed limits. Keep the local reservation ledger and owner-set caps as required gates; current cap amount is still unset.
- Writing samples can expose private correspondence or produce an overfit, flattened voice profile. Use only owner-selected samples, preserve register differences, and allow profile/sample deletion. The reviewed skills were not benchmarked on the owner's drafts; their principles provide no detector-passing or hiring-benefit guarantee.
- Windows scheduler ownership, concurrent workers, provider receipt access, employer AI policies, and supported ATS application routes are unverified.

## Milestones

### M0 — Policy and facts

**Goal:** establish reviewed evidence and current eligibility/workflow policy before generating packets.

**Implementation status:** Complete for the local evidence register and owner-reviewed claim flow. Profile/CV files are stored locally; extracted claim suggestions remain unreviewed until the owner approves them. This is a one-time evidence onboarding step, not an intermediate review for each listing.

**Subtasks:** seed the local claim register from profile materials as unreviewed; review reusable claims and role-family limits; reconcile metric versions; record answer-bank facts and exclusions; confirm current Milan/Italy and language rules.

**Affected areas:** local profile/evidence storage, product definition, ADR 0023.

**Dependencies:** owner review; current ADRs 0021/0022.

**Acceptance criteria:** no unreviewed claims in outgoing drafts; every numeric result has experiment context and contribution; current geography/language/paid/seniority policies are preserved; private evidence is excluded from Git.

**Validation:** inspect claim-to-source references and exercise export allowlists with synthetic data; check that no personal profile content enters tracked files.

**Documentation updates:** claim schema and review policy; decision status; known unknowns.

**Applicable specialized skills:** implementation-plan; anti-slop for outgoing prose.

**Expected Git checkpoint:** one validated milestone checkpoint under the repository delivery policy.

### M1 — Durable preparation queue

**Goal:** add opportunity and packet state without changing applied tracking.

**Implementation status:** Core milestone complete. Preparation requests, immutable Jev/job/input snapshots, versioned packets, durable local artifacts, reset retention, full-deletion cleanup, and request/packet state are implemented. The preparations page is the review queue; timed follow-ups and worker leases are not part of this release.

**Subtasks:** additive SQLite migration; stable opportunity and job snapshot identity; separate preparation/application/action states; content-hash queue; Next actions and opportunity detail views; reset and deletion behavior.

**Affected areas:** database/repository/domain/services/web/templates, product definition, architecture, roadmap.

**Dependencies:** M0; transactional migration and backup/restore path.

**Acceptance criteria:** preparation never marks applied; applied snapshots and URL identities survive migration/reset; queue survives restart and job expiry; full deletion clears new personal records; stale packet state is visible.

**Validation:** migration and rollback/restore checks, exact applied identity checks, state-transition and deletion scenarios, UI keyboard/accessibility review.

**Documentation updates:** schema, reset/delete semantics, recovery steps, updated implementation state.

**Applicable specialized skills:** ui-ux-research and frontend design skill for substantial queue UI.

**Expected Git checkpoint:** one validated milestone checkpoint under the repository delivery policy.

### M2 — Jev-coordinated OpenAI packet generation

**Goal:** produce source-grounded versioned packets through the GPT-6 Luna API agent under a local Clue harness only after an explicit owner trigger for one eligible listing, with Jev remaining the matching authority.

**Implementation status:** Core pipeline implemented and synthetically exercised. Runtime use remains disabled in this checkout because the OpenAI key is intentionally blank and separate consent, monthly/per-opportunity caps, and a current rate card are still required. The owner writing pilot, real-account billing check, and final model/price verification are post-development enablement work; no quality or hiring outcome claim is made here.

**Subtasks:** requirement-to-proof map; immutable read-only Jev assessment handoff; per-opportunity context assembly; Responses API adapter using `gpt-6-luna` and `reasoning.effort=max`; strict structured output schemas; a separate Researcher stage with scoped crawl tools and immutable sourced research packets; four tool-free GPT stages (Diagnoser, Recruiter, Rewriter, Hiring Manager) with versioned prompts and typed outputs; an explainable criterion-to-claim coverage map that does not compete with Jev; local resume extraction/readability checks; evidence-bound XYZ bullet patches with optional verified metrics; optional mock interview practice and answer feedback; allowlisted tool execution; separate budget reservation/settlement and consent gates; import several existing CVs as local source/layout options; allow an owner default or agent recommendation/selection among explicitly permitted base CVs; let the owner choose whether to preserve structure or allow improvements; generate versioned CV, cover-letter, application-answer, and outreach-message drafts; local DOCX/PDF rendering; owner-selected writing samples with author/source labels; optional private, revisioned voice profile; output-specific writing procedure; small owner-reviewed writing pilot.

**Affected areas:** Jev assessment snapshot contract, evidence/preparation services, private profile storage and deletion, Responses API bridge/tool harness, usage ledger, contact research, local document templates, product and architecture docs.

**Dependencies:** M0–M1; owner-set monthly and per-opportunity OpenAI caps; explicit API data-sharing consent; current account/API settings and pricing verified.

**Acceptance criteria:** Jev's saved result is the only matching authority and GPT cannot alter it; Jev conflict blocks generation and review/unassessed requires owner resolution; stale JD/profile/policy/claim/voice-profile/Jev/research revisions are rejected; unknown claims cannot enter drafts; the Researcher alone has allowlisted read-only crawl tools and receives no CV/profile/claim data; writing/practice stages have no network, crawl, filesystem, shell, Gmail, send, submit, or employer-form tools; each role emits a validated typed output; Diagnoser reports observable extraction/layout risks without claiming exact ATS simulation or explaining ghosting; Recruiter maps criteria to reviewed claims and any coverage figure is defined as document coverage, not fit; Jev remains visible and read-only; Rewriter never invents metrics and every factual replacement traces to claim IDs; Hiring Manager feedback is practice feedback, not a hiring prediction or fit score; originals remain unchanged; the owner can choose a default CV or permit the agent to recommend a base from selected references; tailored documents preserve the chosen structure unless the owner opted into improvements; changed artifacts invalidate prior review; the owner sees the complete packet and outreach evidence at one final review checkpoint; a separately authorized Gmail adapter can create only an unsent draft after approval of its exact recipient/subject/body; costs are reserved/settled against both OpenAI caps and are never merged with Jev spend; API calls are impossible without cap configuration and consent; outgoing text invents no fact, feeling, or intention and preserves technical meaning, qualifications, and uncertainty; private samples/profile values stay local, never enter Git, and are removed by personal-data deletion.

**Manual trigger acceptance:** automatic discovery, deduplication, hard filters, and Jev scoring produce listing results without starting research or generation. A single listing's **Prepare application** action starts only that listing after hard gates pass and Jev is `match`; `review`, unassessed, and `conflict` cannot start a run. No bulk, scheduled, or queue-driven action starts preparation. The trigger records the exact opportunity/Jev/input revisions, reserves only that opportunity's budget, and duplicate clicks cannot launch duplicate work. Optional interview practice requires its own owner action. A stale input requires refresh and a fresh trigger.

**Validation:** synthetic cases cover Jev `match`/`review`/`conflict`/unassessed handoffs, stale snapshots, unknown claims, unsafe URLs, conflicting metrics, unsupported answers, employer no-AI instructions, prompt injection, forbidden tool calls, API failures, cap exhaustion, missing usage receipts, and retry reconciliation. Verify that untouched listings, bulk selection, and scheduled/queue processing make zero research/model calls; an explicit click starts only its bound eligible listing; repeated clicks do not duplicate requests or spend; stale Jev/job/profile inputs require a new trigger; and budget is reserved only after a trigger. Add parser extraction cases for columns, tables, headers/footers, text boxes, images, malformed reading order, and partial extraction; requirement maps with supported, partial, absent-from-CV, and uncertain evidence; unsupported/missing metrics that must remain unnumbered; interview answers with strong and weak evidence, reasoning, and clarity; and assertions that none of the four writing/practice stages can browse. Run a local pilot on 10–12 representative drafts comparing the current workflow, GPT-6 Luna max without a voice profile, and GPT-6 Luna max with the owner-approved profile; hold some drafts out from tuning and randomize/anonymize comparison order. The owner rates clarity, naturalness, voice match, role relevance, factual changes, correction effort, and time. Record input/output/tool cost per packet and stage. Treat factual drift as a veto, not a weighted score. This pilot is usability evidence, not statistical validation or evidence of hiring benefit. Detector scores are not an acceptance gate. Review rendered PDF/DOCX output.

**Documentation updates:** packet contract, voice-profile revision and sample retention/deletion rules, writing procedure and evaluation evidence, skill trigger/boundaries, user guide, current state.

**Applicable specialized skills:** documents skill if DOCX generation is selected; anti-slop for user-facing prose.

**Expected Git checkpoint:** one validated milestone checkpoint under the repository delivery policy.

### M3 — Selective public contact research

**Goal:** after an owner triggers preparation for an individual high-priority role, use the bounded GPT-6 Luna Researcher tools to find a small number of public, provenance-backed professional contacts without bulk enrichment or automatic research of other listings.

**Implementation status:** Core contact research, source evidence, confidence labels, cross-retry suppression, and a separate exact-approval Gmail draft adapter are implemented with synthetic fixtures. No real OAuth authorization or Gmail draft was created. Automated reminders and cancellation on reply/closure are deferred; the owner remains responsible for monitoring and sending.

**Subtasks:** agent-directed crawl/search through the installed Scrapling adapter; enforce per-opportunity query/page and cost limits; verify source URLs and capture excerpts/observation times; assign confidence and function-match labels; contact suppression; draft one primary message and a reason-gated backup; configure owner-approved Gmail OAuth/adapter; create a Gmail draft only after final owner approval; reconcile draft IDs/timeouts; configurable owner reminders; cancellation on reply/closure/interview.

**Affected areas:** contacts/workflow modules, Next actions UI, local deletion, product privacy docs.

**Dependencies:** M1–M2; configured query/page/cost limits under the OpenAI budget, approved contact data-retention rules, and separate Gmail authorization if draft staging is enabled.

**Acceptance criteria:** no contact crawl or enrichment occurs before an explicit trigger for that individual opportunity; no fabricated identities or guessed routes; each retained detail has source and observed time; personal profile data is excluded from contact-search queries; only public read-only pages are crawled; no-contact-found is a valid state; the agent has no Gmail tool; only an owner-triggered adapter creates an unsent draft after exact To/Subject/body approval; Clue never sends; timeout reconciliation prevents duplicate drafts; due owner reminders cancel on terminal/relevant events.

**Validation:** synthetic contact confidence, suppression, repeated-role, reply/cancel, changed-recipient, Gmail OAuth denial, final-approval binding, draft-create timeout, and duplicate-reconciliation scenarios; privacy/deletion review.

**Documentation updates:** contact data fields, retention/suppression, cadence and user controls.

**Applicable specialized skills:** no new skill until repeated use proves one is needed beyond the application workflow skill.

**Expected Git checkpoint:** one validated milestone checkpoint under the repository delivery policy.

### M4 — Outcomes and interviews

**Goal:** reconcile application status and turn mature stage feedback into useful preparation.

**Implementation status:** Local v1 implemented: owner submission attestation, separate receipt upload, interview self-assessment/employer-feedback fields, skill-gap tags, and an event summary. Automated spreadsheet reconciliation, cohort conversion analytics, and mature-window statistics are deferred until the owner chooses an outcomes source of truth and the definitions are calibrated.

**Subtasks:** tracker import/export mapping with stable identity; application event and interview-stage records; receipt/attestation evidence level; briefing and controlled gap tags; cohort dashboard. Keep any existing Google Sheet compatible during transition and avoid two independent automatic writers.

**Affected areas:** applications, feedback, reports, tracker integration, deletion.

**Dependencies:** M1–M3; stable identity reconciliation with any existing Google Sheet.

**Acceptance criteria:** receipt differs from owner attestation; pending is not rejection; stage denominators exclude pending cases; self-assessment is distinct from employer feedback; human effort and packet quality are visible.

**Validation:** synthetic tracker reconciliation, missing/duplicate receipt, unresolved stage, mature cohort and deletion scenarios.

**Documentation updates:** event schema, metric definitions, maturity windows, tracker source-of-truth choice.

**Applicable specialized skills:** implementation-plan; no new integration until tracker ownership is explicitly selected.

**Expected Git checkpoint:** one validated milestone checkpoint under the repository delivery policy.

### M5 — Human-controlled application handoff

**Goal:** make approved packets easy for the owner to inspect and use while keeping every application submission and message send manual and outside Clue.

**Implementation status:** Core handoff implemented: exact packet confirmation, local artifact download, optional Gmail draft creation only after exact-recipient/subject/body confirmation, and post-action owner attestation/receipt. Clue has no send or submit operation. No live external action was used in validation.

**Subtasks:** render final versioned CV/cover-letter/answer bundle; provide the verified official vacancy link; show exact changes and unresolved fields; let the owner record their manual action and optionally attach/import a receipt; save the exact approved artifact version used.

**Affected areas:** packet review UI, application tracker, security/privacy docs.

**Dependencies:** M1–M4 and packet pilot evidence.

**Acceptance criteria:** no outbound send/submit adapter or API tool exists; owner is clearly responsible for checking and manually submitting/sending outside Clue; a packet never changes the applied tracker; only the owner's post-action attestation or imported evidence records an application event; exact approved material is recoverable.

**Validation:** verify review bundle links and rendered documents; test version invalidation, owner attestation and receipt import, duplicate owner marking, and recovery of the exact reviewed artifact.

**Documentation updates:** owner review and manual submission guide; current application-state semantics and receipt provenance.

**Applicable specialized skills:** release-readiness before any meaningful rollout.

**Expected Git checkpoint:** one validated milestone checkpoint under the repository delivery policy.

### M6 — Optional worker for owner-triggered preparation

**Goal:** offer an explicit local worker for bounded research and draft preparation only after the owner has triggered a specific opportunity, and only if the supervised workflow shows enough value. The worker may resume an already requested action; it cannot create preparation requests.

**Implementation status:** Deferred and not authorized. The current request model uses a deliberate per-listing button and app-managed execution; no always-on or scheduled worker is included.

**Subtasks:** Windows Task Scheduler/worker option; durable SQLite leases for owner-triggered actions only; visible stop/cancel; queue backpressure; per-run request and cost caps; API consent checks before every run.

**Affected areas:** worker lifecycle, database leases, local settings, operations documentation.

**Dependencies:** M1–M5; measured workload, configured OpenAI caps, and separate owner decision.

**Acceptance criteria:** no silent always-on service; no automatic or bulk preparation enqueue; the worker only consumes an exact owner-triggered opportunity/action and cannot create a trigger; one active lease per action; app/worker cannot double-run or double-spend; stop is graceful; due work resumes safely; worker only creates local review drafts and has no external write capability.

**Validation:** restart/recovery, concurrent worker, lease expiry, stop/cancel, per-run and rolling budget guard, duplicate preparation, API timeout reconciliation, and revoked consent scenarios.

**Documentation updates:** install/disable/recovery instructions, data retention, OpenAI cap/consent behavior.

**Applicable specialized skills:** release-readiness if distributed beyond the owner’s machine.

**Expected Git checkpoint:** one validated milestone checkpoint under the repository delivery policy.

## Final integration validation

For implementation, validate additive migration and restore; exact applied identity preservation; no preparation-to-applied leakage; claim/packet version invalidation; action dedupe and lease recovery; follow-up cancellation; URL/HTML safety; source provenance; Jev cap preservation; OpenAI usage settlement; Gmail draft approval binding and timeout reconciliation. Run the repository's relevant checks and synthetic/manual scenarios for each milestone. Do not use live personal CVs, listings, providers, or employer forms as test fixtures without a separately reviewed need.

## Rollback / recovery

Take and validate a local database backup before schema changes. Keep additive migrations reversible or provide a documented restore path. Preserve applied snapshots, URL history, and Jev spend ledger. If packet/workflow logic fails, disable new preparation while retaining existing tracker/search behavior. Cancel queued outbound actions when approval, destination, or source validity cannot be established.

## Progress

- Integrated the writing-skills review into M2: sample provenance, local voice-profile handling, output-specific editing rules, detector evidence limits, and a small owner-reviewed pilot. The cited writing skills remain references, not dependencies.
- Added the owner-requested five-role workflow to M2: a separate source-gathering Researcher followed by Diagnoser, Recruiter, Rewriter, and optional Hiring Manager practice stages on GPT-6 Luna max. Only the Researcher receives crawler tools; Jev remains the matching authority; ATS checks are limited to observable parseability risks; XYZ edits require evidence-backed metrics and never force a number into every bullet.
- Added a per-listing **Prepare application** start gate: discovery, deterministic filters, and Jev may remain automatic, while research, file generation, and outreach research run only after an owner click for one eligible listing. The click binds revisions and budget to that job; mock interview practice is a separate optional trigger.
- Owner-approved the Jev/GPT division on 2026-10-06: Jev validates matching; GPT-6 Luna via the OpenAI Responses API at `reasoning.effort=max` researches and generates drafts under a local tool/budget harness. The owner reviews the complete packet before any Gmail draft is created or application is marked submitted. Outreach sending and applications remain manual.
- Implemented the private evidence register, per-listing manual trigger, Jev snapshot binding, separate API budget/consent gates, bounded public Researcher, Diagnoser/Recruiter/Rewriter stages, optional interview practice, versioned local artifacts, contact suppression, approval-bound Gmail draft staging, and owner outcome feedback.
- `.env.example` intentionally contains an empty `OPENAI_API_KEY=`. Tests use only synthetic records and fake provider/Gmail responses. No real CV, API request, Gmail draft, or employer application was used.

## Implementation discoveries / decisions

- Separate prompt roles are ordinary orchestrated calls through one GPT-6 Luna configuration, not standalone autonomous agents with independent credentials or tools.
- Jev remains the only matching validator. GPT may make content/research suggestions but cannot write or override Jev results or deterministic gates.
- OpenAI API work remains disabled until the owner supplies a key, sets monthly and per-opportunity caps, records separate data-sharing consent, and installs the current rate card. A key alone does not enable calls.
- The owner reviews the complete final artifacts before any external write. A separate adapter may create an unsent Gmail draft only after that approval; no send operation is in scope. The owner submits applications manually.
- Store claim values and generated artifacts locally; public Git contains only generic schemas and synthetic examples.
- Reserve and settle API use separately from Jev; reconcile uncertain API usage before retrying to avoid duplicate spend.

## Completion evidence

Synthetic implementation evidence for this checkout:

- `pytest tests/test_application_prep.py tests/test_application_workflow.py -q --tb=short`: 22 passed.
- `ruff check clue_ai tests`: passed.
- Bundled Python `-m compileall -q clue_ai`: passed.
- Full repository suite: 207 passed with one upstream Starlette/AnyIO deprecation warning. The exact PLAN-019 commit snapshot was tested with the project-declared TypeSafe and Scrapling dependencies installed in an isolated temporary directory; no provider key was supplied and tests use synthetic data/fakes.
- Existing suite expectations were aligned to the current documented Jev rubric, crawler limits, source registry, owner-added-source behavior, and AI-engineering search scope. No runtime behavior was changed by that validation-alignment work.
- No live OpenAI/Gmail operation or personal-data pilot was performed. The API key remains blank by request. M6, reminders, external tracker synchronization, and cohort analytics remain deferred.
