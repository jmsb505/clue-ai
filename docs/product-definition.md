# Product definition

**Status:** DEFINED FOR SINGLE-USER LOCAL FEASIBILITY BUILD; explicit requirements are marked NORMATIVE  
**Owner:** project owner  
**Updated:** 2026-10-07

## Purpose

Build a single-user, local-first job discovery app for the owner’s personal use. The user supplies a CV and search preferences. The app searches accessible job sources, checks user-set constraints, uses TypeSafe AI's Jev model to score role fit, and returns a ranked list with enough evidence for the person to decide what to inspect. The person opens the original listing and chooses whether to apply.

The product helps a person find and compare available jobs. It does not choose candidates for employers or submit applications.

## Intended user

**NORMATIVE:** An individual job seeker searching on their own behalf. The user controls their profile, search conditions, and next step.

**NORMATIVE:** The search geography is selected by the user for each search or saved search. A single launch country is not assumed.

**NORMATIVE initial focus:** Prefer remote roles explicitly eligible from Italy, Europe, the EU/EEA, or worldwide; also include roles explicitly located in Milan. Exclude remote listings with incompatible or unverified work-from geography and physical or unclear-workplace listings without Milan location evidence before Jev. The product remains geography-selectable; this focus is a validation profile, not a permanent country restriction. Do not assume the user's citizenship, residence permit, or work authorization. Ask separately which countries the user is authorized to work in and whether sponsorship is needed.

## Owner requirements

- Take a CV and explicit guiding parameters as search inputs.
- Search across a broad set of job boards, employer career pages, and other sources, within terms, licensing, privacy, technical, and cost limits.
- Use TypeSafe AI's **Jev** model to evaluate the locally screened AI engineering shortlist against the candidate profile and the user's current search criteria.
- Focus this search on junior roles and internships; positions must be paid.
- Rank and list current job openings for the user.
- Do not automate job applications. The user reviews a result and applies through its source if they choose.
- Keep one saved profile, CV, search preferences, and job index locally on the user's device, with clear controls to delete that data.
- Build for one personal user on one local machine. No registration, hosted accounts, public service, multi-user support, or scale target is in scope now.
- Use a friendly interface with the directness and visual approach of [Jobbie](https://jobbie.bot/), while keeping the product focused on search and review.
- Keep recurring spend at $0 for components/data sources outside the configured Jev and separately consented OpenAI application-preparation lanes. Each lane has independent Clue-local usage accounting and configurable request controls; Clue does not set provider-account caps.

**Budget constraint:** Keep Jev and OpenAI accounting independent. Each has configurable Clue-local request controls and a separate usage ledger; these apply only to Clue's own requests and do not change provider-account settings or limits. Use the current rate card for each run, never mix provider usage, and never silently switch models. Recorded application-preparation evaluations use synthetic candidate, job, and research data.

## Recommended search inputs

Treat each preference as either a hard constraint, a weighted preference, or an optional hint. Ask the user which it is when the distinction changes results.

| Input | Example |
|---|---|
| Target roles and role families | Several job titles, adjacent role names, or a career change target |
| Geography | Country, region/city, radius, relocation, remote countries, or time-zone overlap |
| Workplace | Remote, hybrid, on-site, or any; days in office if known |
| Remote-work eligibility | Where the employer permits the employee or contractor to be physically based (for example Italy, EU/EEA, Europe, EMEA, worldwide); keep separate from the job's remote/hybrid label |
| Work authorization | User-provided countries where the user can work, stored as local context; sponsorship need is a separate search filter |
| Compensation | Minimum or range, currency, pay period, and how to handle missing salary data |
| Employment type | Full time, part time, contract, temporary, internship, or other local categories |
| Seniority and scope | Level, years as a rough hint, responsibility scope, or people-management preference; this search targets junior roles and internships |
| Skills and credentials | Required and preferred skills, language fluency, licenses, education, certifications |
| Company and work preferences | Industry, company size, sector, travel, schedule, or user-selected exclusions |
| Freshness | Posted within a chosen period; exclude seen, saved, or dismissed results |
| Importance | Must-have constraints plus adjustable weights for preferences |

Never use protected or sensitive traits such as race, religion, health, disability, age, sex, or family status to score job fit. Do not infer such traits from a CV. A job-specific legal eligibility condition can be handled only when it is explicit, necessary, and user-controlled.

## Bounded pilot defaults

These are working defaults that complete the pilot definition; they can be revised if user research or feasibility evidence points elsewhere.

- Accept PDF and DOCX CVs first. Parse and save the profile locally, then start the search from the same upload action. Keep extracted fields editable afterward.
- Start with an English interface and validate Jev rubrics by CV/job-description language. A listing in a language without a validated rubric may still be shown, but receives “fit not evaluated” rather than an unsupported score.
- Use Italy as the first remote-work eligibility location and Milan as the first local office location. Prefer remote roles; allow hybrid/on-site roles in Milan. English requirements are acceptable; exclude explicit Italian-language requirements while allowing Italian as an optional/preferred skill. Keep work authorization separate from location and do not infer it.
- Classify location evidence as `Eligible here`, `Needs verification`, `Not eligible`, or `Unknown`. Italy, EU/EEA, Europe, and worldwide are positive only when stated and not contradicted. Treat EMEA, timezone overlap, or an unqualified “remote” label as `Needs verification` unless the posting also makes Italy eligibility explicit. Under the default remote-preferred profile, keep only confirmed eligible remote jobs or postings explicitly located in Milan; exclude other and unverified locations before Jev. Preserve the exact evidence passage and source URL.
- Prefer jobs posted within the last 30 days, with shorter freshness preferences available. An older posting stays for review unless closure or expiry is established. Show the employer's datePosted, if supplied, separately from the platform's last-checked time.
- Target junior/entry-level roles and internships, and require paid compensation. Explicit unpaid or volunteer roles conflict; missing pay or unclear seniority remains visible for review and cannot be labeled a confirmed filter match.
- Call a listing “recently checked” only when the source was checked within the past 24 hours. If a source cannot meet that interval or its terms require a longer refresh, label its age and avoid claiming the listing is live.
- Target a 30-second 95th-percentile response for a search over an already indexed pilot dataset. Crawling happens out of band, not in the user's request path.
- Target [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) for the responsive interface. Use Jobbie's friendly, card-based scan patterns and keep the original employer/source action clear.

## Core workflow

1. The user uploads a CV from the local app. Clue extracts the document on-device, saves the original and parsed profile locally, and starts a search without requiring a separate review/save step. The profile remains editable afterward. A saved work-authorization list is local reference; the app does not infer legal eligibility from it.
2. Clue uses the most recently saved search preferences when available. On first use it derives likely target roles from the CV, prefers remote work eligible from Italy, and also allows hybrid/on-site work in Milan, targeting junior or intern roles that are paid. The user can change the country, local office city, role keywords, and other preferences later.
3. When a search starts, Clue refreshes due feeds and crawls due company and job-board pages using the local page budgets. It automatically qualifies public official company/ATS routes, normalizes fields, removes duplicates, and records source and freshness information. A search is broad but bounded; it does not recursively crawl unrelated sections or the whole web. X is a separate manual lead path: the user opens an X search link, checks the post and final employer/ATS page in their browser, then enters the lead in Clue.
4. Each search locally screens fetched and active cached listings for AI engineering or related technical AI implementation and confirmed workplace/geographic scope before Jev. Exclude unrelated/non-engineering work, explicit senior titles, explicit unpaid work, out-of-region remote roles, non-Milan physical roles, and unverified locations under the default profile. Retain AI-focused roles with unknown pay or seniority for Jev. Keep non-hidden/non-applied focused candidates after expiry cleanup. Search coverage reports local exclusions separately from parsing errors and deduplication.
5. Jev automatically evaluates bounded, job-related fit and search-filter compatibility when the user has enabled the one-time opt-in, a key is configured, and the app-side reserve allows the request. Otherwise, listings remain available with a clear unscored reason. A filter conflict remains visible in the run for the user's review.
6. The user reviews match details, saves or dismisses jobs, and opens the original source page. The user decides whether to apply on the original site; Clue never submits an application. A manual X lead, if used separately, keeps its own provenance and is not part of automated discovery.
7. The user can revise their local profile or search and delete the saved CV, profile, preferences, tracked-company choices, indexed jobs, and results through product controls.

## Jev's role in matching

The owner can mark a result or saved role as Applied after sending an application externally. Applied roles are tracked locally with the date marked and posting links, and excluded from search candidates, visible results/counts and saved-role lists until undone. Application records survive history clearing, source expiry and search resets. Undo preserves other saved/hidden state. Full personal-data deletion clears the tracker. Matching uses retained identity and known posting URLs; a new posting with different identifiers may need a new mark. See [ADR 0016](decisions/0016-durable-applied-tracker.md).

**NORMATIVE:** Jev is the required model for fit validation. The user asked for Jev to evaluate candidate fit against each job listing.

**NORMATIVE:** The owner requests inexpensive AI engineering screening before Jev, including cached listings and scoring retries. Do not treat missing salary or an unlabeled level as an exclusion, require exact target-title matches, or equate company AI marketing with AI engineering responsibilities. Jev's filter-compatibility label is advisory and does not establish legal work authorization or guarantee the job is open. Prior broad search snapshots remain historical; start a new search to use the focused shortlist. See [ADR 0017](decisions/0017-ai-engineering-prefilter.md), superseding ADR 0010's all-listings rule, and [ADR 0016](decisions/0016-durable-applied-tracker.md).

**NORMATIVE:** The target seniority is junior/entry-level or intern, and the position must be paid. Explicit unpaid/volunteer or explicitly mid/senior roles conflict; missing compensation or unclear level stays in `review`. These criteria are assessed by Jev and do not remove candidates before assessment. See [ADR 0012](decisions/0012-entry-level-paid-job-criteria.md).

**NORMATIVE:** Focus on AI/ML engineering, LLM/RAG/agents, computer vision/NLP, model research and inference/deployment. Adjacent backend/platform/data roles need actual AI/model implementation evidence. Generic analyst, admin, sales and manual AI rating/annotation work is outside this owner's current scope. Default ranking weights are AI relevance 50, role 25, skills 15, experience 5 and preferences 5. Upgrade only former standard defaults; preserve custom weights. See [ADR 0017](decisions/0017-ai-engineering-prefilter.md), superseding ADR 0013's optional AI focus.

**NORMATIVE:** Target job titles are alternative discovery/ranking preferences, not exact-title exclusions. Jev checks level, pay, location/eligibility, workplace and other requirements separately. Preserve its valid categorical decisions without an uncalibrated confidence cutoff. Missing facts reported as review remain for verification; missing checks never establish a confirmed match. Explicit incompatible work regions (such as LATAM for Italy) override location decisions with separately attributed listing evidence and retained model answers. Default to a fit-ranked Potential opportunities view combining match and review listings, with explicit uncertainty labels and per-check details. Preserve senior/unpaid/location conflicts and the full-candidate set. A search reset clears cached jobs, result snapshots, and refresh timers with a local backup while retaining the local URL/signature registry that prevents unchanged reviewed postings from recurring. Full personal-data deletion clears that registry; the user can include reviewed links again for reassessment. See [ADR 0014](decisions/0014-practical-matching-and-clean-slate.md), [ADR 0015](decisions/0015-explicit-geography-and-jev-decisions.md), and [ADR 0018](decisions/0018-no-repeat-listing-research.md).

**WORKING recommendation:** Use typed Jev questions for bounded fit judgments and combine job-related dimensions in ordinary code using the user's stated weights. Exact constraints, permissions, sorting, and data handling remain in ordinary software. The first implementation uses categorical `Choice` questions with five fit levels and a separate `unknown` answer; returned levels are mapped to a normalized 0–1 fit signal and are not calibrated.

Jev returns structured decisions, not explanatory prose. It cannot by itself provide trustworthy CV evidence snippets or explain a score in natural language. Build explanations from the parsed CV facts and the original job text, and show the source passages where possible. Distinguish “not found in the CV/listing” from “does not match.” Show uncertainty where evidence is missing or Jev is unsure.

Call the result a **fit score** or **match score**, never a hiring probability or prediction that an employer will interview or hire the person. The score is a guide for the user's own review. Do not show a 0–100 number as calibrated until a representative evaluation supports that mapping.

Run Jev automatically after retrieval, expiry cleanup, and strong-identity deduplication, with all current criteria included in the state. Preserve the model/version, rubric, candidate-profile snapshot, listing snapshot, filter assessment, and response needed to reproduce a result, subject to approved retention limits. If Jev is unavailable or the app reserve is exhausted, keep each remaining listing visible as unassessed rather than silently substituting another evaluator.

## Results and interaction

Each result should make these fields easy to scan:

- role, employer, source, original posting link, location and work arrangement;
- posted date, last checked time, salary and currency when supplied;
- match score, AI/ML domain relevance, user-weighted criteria, confidence or evidence status;
- strengths and gaps grounded in CV and job-description evidence;
- save, dismiss, and open-source actions.

Show the enabled sources and regions searched. Only show listings from public sources that the connector can currently fetch and qualify. Do not imply coverage of “the whole internet” or that a listing is open now unless the source status was checked within the stated freshness window. Keep a clear distinction between the employer's posted date and the date this platform observed or verified the listing.
Refresh source indexes to discover new postings, but do not repeat an unchanged listing URL in a new result snapshot or Jev request after a complete assessment. Track the canonical URL and a signature of material posting fields in a local ledger that survives ordinary result/cache reset. Treat the exact URL as the no-repeat unit; do not fuzzy-merge separate URLs that can represent distinct vacancies or country variants. Reassess a URL when a refreshed source supplies materially changed posting data, or when the owner selects “Include previously reviewed listing links.” Report new links, changed links, unchanged reviewed links skipped, and duplicate exact URLs within the current run separately. See [ADR 0018](decisions/0018-no-repeat-listing-research.md).

## Source discovery and crawling policy

**NORMATIVE direction:** Company-board discovery is a primary route, with broad remote-job feeds as supplements. Use a profile-matched company directory seeded from European AI startup lists, Italian AI ecosystem maps, and broader AI/data employers. Resolve the official company careers link and its linked ATS board automatically; the owner should not need to find or type ATS identifiers. The company catalog identifies employers to search, not current vacancies.

For every role, prioritize whether the listing says a person based in the selected country can do the work; a generic `remote` flag or a company's office location is not enough. Prefer documented free public ATS feeds/APIs, then the employer's linked ATS board, job sitemap/RSS/Atom, `JobPosting` JSON-LD, and a bounded career-page crawl. Preserve the canonical employer/ATS posting URL, exact country/location evidence, publisher date/expiration, source check time, and attribution.

The local registry combines the original free feeds (Jobicy, RemoteJobs.org, Remote OK, Remote First Jobs, and Startup Jobs), the requested We Work Remotely, Himalayas, Remotive, Working Nomads, and JustRemote sources, and the tracked-company board crawler. WWR, Remote OK, Himalayas, Remotive, and Working Nomads use their first-party RSS/JSON endpoints; JustRemote uses a bounded Scrapling crawl. Frequently updated feeds refresh hourly; sources whose publishers update daily remain daily. Company career pages and JustRemote refresh every six hours. A failed request does not consume the normal refresh interval; the failed source can retry after a five-minute backoff. Search coverage identifies refreshed, cached, failed, and blocked sources, while active local listings remain available between refreshes. Wellfound and Dynamite Jobs remain one-click manual link-outs because their published terms or developer documentation rule out automated public-board scraping. See the [source review](research/source-discovery-and-crawl-review.md) for the per-source schedule and crawl limits. These routes expand coverage but do not provide internet-wide coverage. EURES remains a useful manual portal until an official vacancy API and reuse path are documented.

Company boards should be automatically qualified from the official career link and its linked public ATS routes. Owner-added supported public sources activate immediately after HTTPS/public-host validation; the owner can pause or remove them at any time. Scrapling does not enforce robots.txt `Disallow` rules in this single-user local crawler. Continue to apply documented API/feed request limits and attribution, and pause a host after an explicit denial, rate limit, or anti-bot challenge. Do not use login-only content, guessed ATS identifiers, unrelated crawling, search-result scraping, stealth, proxy rotation, browser impersonation, CAPTCHA solving, or retries around a block.

X is manual-only. Clue may build a user-clicked X search URL from role and location terms, and the owner may add a lead after inspecting both the X post and final employer/ATS listing. Clue must not use Scrapling or another method to scrape or script X, call the X API, resolve `t.co` or other shortened links, fetch or preview a user-supplied URL, or open links automatically. Store the X status permalink and direct HTTPS listing URL separately, display the destination host, treat the listing text as untrusted data, and tell the user that Clue did not verify that the vacancy remains open. Manual X leads are not counted as an X search or source refresh in connector coverage.

Scrapling is the selected crawler for public HTML job and career pages, employer sites, linked ATS hosts, and owner-added public career URLs. Use its async Spider with expanded career/job link discovery, sitemap traversal, structured-data extraction, streaming, and adaptive selectors. Try static requests first and render detected JavaScript career shells. The local profile uses `robots_txt_obey = False`, eight global requests, at most two per domain, a one-second base delay, 25 HTML pages per employer, 10 child sitemaps, 50 sitemap job pages, and 20 dynamic pages per company batch. A standalone career URL can expose up to 100 same-host pages; JustRemote has a separate 200-page budget. Company pages and JustRemote are eligible every six hours. Keep public-host confinement, response-size limits, an identifying User-Agent, and zero blocked retries. Never use stealth fetchers, proxy rotation, browser impersonation, CAPTCHA solving, or anti-bot bypass. See [profile-aware board-discovery research](research/profile-aware-company-board-discovery.md) and [ADR 0009](decisions/0009-broader-local-public-crawling.md).

The CV-first search may refresh due company boards in the background after the owner starts a search. Keep the page responsive, stream per-source progress, and refresh incrementally instead of crawling an entire domain on every page load. Search should automatically use the profile-matched catalog; the owner must not need to resolve company ATS slugs manually.

## Product boundary

### In scope for the first product increment

- Local candidate profile and PDF/DOCX CV upload that immediately starts search; extracted fields stay editable afterward.
- Per-search role, geography, must-have, and preference inputs.
- A source registry, automatically qualified public source connectors, normalized listing records, duplicate handling, and freshness checks.
- A profile-matched directory of official company boards and automated company/ATS discovery through Scrapling.
- A manually controlled X search handoff and owner-reviewed lead intake; no X API or X site automation.
- Jev-based fit scoring and a transparent ranked-results view.
- Saving, dismissing, revising search criteria, and opening the employer or job-board source.

### Out of scope

- Automated applications, application-form filling, screening-question answers, or employer contact.
- Automated X API searches, scraping or browser automation on X, server-side URL expansion/preview, or automatic external-link opening.
- Employer-side recruiting, candidate selection, or workforce-management decisions.
- A claim that every public or private job board is covered.
- Resume rewriting or generated application materials in the first increment.
- Universal country/source coverage, hosted infrastructure, or additional framework selections beyond the local Scrapling crawler and feasibility-stage needs.
- Hosted accounts, multi-user access, public listing redistribution, or scaling beyond the owner's local use.
- Paid job feeds, paid infrastructure, or other paid services beyond the monthly TypeSafe ceiling.

## Local data and privacy behavior

**NORMATIVE:** Store the saved CV, parsed/editable profile, search preferences, cached job listings, and results locally on the owner's device. Provide a single clear action to delete the local profile and its associated data. Do not create a hosted account or upload the job index.

**WORKING recommendation:** Do CV parsing and job indexing locally. Do not send name, email, phone number, or exact home address to Jev when those fields are not needed for job-fit scoring. After one-time opt-in, send only the minimum relevant parsed profile and listing text for fit evaluation. The work and education history can still identify someone and remains personal data. Explain which fields leave the device, where Jev processes them, and any retention/telemetry behavior.

Keep the original CV, extracted profile, search criteria, saved jobs, and fit results under user-controlled local deletion. The owner waived confirmation of device encryption for local data and backups on 2026-09-30; the project does not claim encryption or Windows permission evidence. After a one-time in-app opt-in, TypeSafe receives minimized parsed profile and listing fields automatically after each search when scoring gates pass. The original CV, contact details, work authorization, and source URL stay local. The owner waived account/terms verification; account-specific provider retention, telemetry, and deletion behavior remain unverified.

For owner-triggered OpenAI preparation, Clue sends the selected CV text, each full permitted technical and descriptive profile, owner-confirmed writing preferences, a saved Jev snapshot, and the selected job/research context to their assigned stages. Before generation, it sends the same stage input, instructions, structured-output schema, and tools to OpenAI's input-token counting endpoint. Clue checks the returned input count plus the stage output allowance against GPT-6 Luna's documented context window and reserves its app-side spend using the count. It does not shorten selected profile text to fit a character threshold. Recruiter/Rewriter receive exact source-bound evidence references from technical profiles; generated facts must cite those references and pass Jev support before entering the packet. Unreviewed technical suggestions do not require one-by-one pre-approval, but Jev support confirms only that the wording is supported by the supplied excerpt, and the owner reviews the exact packet. The Researcher receives no personal profile; the Diagnoser receives the selected CV and job/Jev context. Clue sets Responses API `store:false`; this prevents response-state storage for retrieval but does not itself provide Zero Data Retention. OpenAI documents that abuse-monitoring logs may contain prompts and responses and are retained for up to 30 days by default unless the organization is approved for Modified Abuse Monitoring or Zero Data Retention. Do not promise zero retention without checking the account's controls. See [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

CV parsing remains local. PDF/DOCX extraction includes selectable text and DOCX tables, headers, and footers; text boxes are retained with a visual-order caveat. Embedded images are flagged but not OCR'd, and text exceeding the local extraction limit is rejected rather than silently truncated. Review the extracted text before selecting a CV for a preparation run.

## Quality and validation direction

Before relying on rankings in personal searches, evaluate the pipeline on representative, synthetic or otherwise appropriate CV/listing pairs. Compare results with the owner's judgments and a simple keyword baseline. Review precision and recall in the first results, ranking quality, probability calibration, confidence handling, missing-data behavior, duplicate and stale-listing rates, and cost per search. Inspect results across role families, languages, seniority, and regions. Do not collect or use protected traits as ranking features.

Measure personal usefulness through save/open/dismiss actions and explicit “why is this a match?” feedback. Keep “unknown” available when a CV or listing lacks evidence. The user should be able to correct their profile and change criterion weights without re-uploading their CV.

## Decisions still open

The personal app's product behavior and source policy are defined. The following are remaining evidence tasks or owner choices, rather than unanswered product goals:

- Confirm each source's personal-use terms, free limits, and geographic coverage; see the [source discovery review](research/source-discovery-and-crawl-review.md).
- Provider account/terms and device-encryption checks were waived by the owner on 2026-09-30; the app's $4 request reserve and one-time Jev opt-in remain, but provider-wide limits are not verified.
- The synthetic backup/restore and deletion path is tested; Windows file permissions and encryption are not verified or required by owner decision.
- Review the synthetic relevance examples and provide judgments or defer personal calibration before treating scores as personally validated.

## Wider discovery and candidate qualification evidence

**NORMATIVE:** Keep revisiting enabled source indexes on their documented cadence, but do not repeat Jev assessment for an unchanged listing at an already researched exact URL. Search across varied AI engineering role families and independent source families; the source list is intentionally broad but finite. Deduplicate exact listing links without fuzzy-merging distinct URLs, preserve publisher attribution and the original listing link, and explain which sources were queried or represented by cached listings. See [ADR 0018](decisions/0018-no-repeat-listing-research.md) and [ADR 0019](decisions/0019-free-ai-and-global-job-feeds.md).

**NORMATIVE:** In addition to filter compatibility and the weighted fit score, compare the candidate's saved profile with up to four explicit employer qualifications from each listing and separately assess seniority against stated level/years. Keep mandatory and preferred items labeled. Use `met`, `partly_met`, `not_met`, and `not_enough_evidence`; missing CV evidence is not a deficiency. If no requirements are extracted, say so and point the user to the full listing. Persist each check in that run's result snapshot. These are evidence summaries, not hiring probabilities; the user verifies requirements on the source listing. See [ADR 0020](decisions/0020-qualification-and-seniority-evidence.md).

## Workplace and language scope

**NORMATIVE:** Treat remote as a preference, not a hard workplace constraint. For remote roles, require explicit evidence that the employee may work from the selected country; for the current Italy profile, Italy, Europe, EU/EEA, or worldwide are accepted. “Remote” alone, timezone overlap, and broad EMEA remain unverified unless Italy is separately named. Hybrid/on-site roles are eligible only when the posting identifies the selected local city (Milan by default). An unknown workplace type is accepted only when the listing clearly identifies that city. Exclude other and unverified locations before Jev, even when the uncertain-location option is set; that option applies to broader workplace modes. Report each exclusion reason in source coverage. See [ADR 0022](decisions/0022-strict-europe-or-milan-location-gate.md).

**NORMATIVE:** English-language requirements are acceptable. Exclude a job only when its posting explicitly requires Italian; a preferred/optional Italian skill is not a conflict. Missing or ambiguous language details remain eligible for Jev review. The local language detector is a bounded aid; the original posting remains authoritative. Include the workplace preference, local city, and language rule in Jev's filter state, and let remote work act as a ranking preference for otherwise eligible roles. See [ADR 0021](decisions/0021-milan-workplace-and-language-preferences.md).

## Jev-coordinated application preparation

The Applications index, per-listing dossier, and local copy/ZIP email handoff are specified in [PLAN-022](plans/PLAN-022-application-workspaces.md) and [ADR 0024](decisions/0024-application-workspaces-and-local-email-handoff.md).

**IMPLEMENTED LOCALLY; SYNTHETIC IMPLEMENTATION GATES PASS; OWNER ACCEPTANCE AND REAL-DATA PILOT PENDING.** [PLAN-019](plans/PLAN-019-application-preparation-framework.md), [PLAN-020](plans/PLAN-020-end-to-end-evaluation-and-grounding.md), [PLAN-021](plans/PLAN-021-evidence-led-generation-quality.md), [ADR 0023](decisions/0023-application-preparation-and-action-boundaries.md), [ADR 0024](decisions/0024-model-aware-token-budgeting.md), [ADR 0025](decisions/0025-jev-approval-of-tailored-resume.md), [ADR 0026](decisions/0026-jev-categorical-evidence-support.md), and [ADR 0027](decisions/0027-explainable-jev-resume-review.md) define the local claim register, requirement-to-proof maps, versioned CV/cover-letter/answer packets, per-listing preparation queue, bounded public contact research, outreach drafts, and owner-recorded interview feedback. Jev remains the sole job-matching validator. After generation, Jev makes a separate explicit decision on whether the final tailored resume is ready for the selected listing; this decision cannot modify the saved fit, filter, qualification, or seniority result. Jev also checks each generated factual block against linked approved claims, exact technical-profile excerpts, or verified public evidence. GPT-6 Luna through the OpenAI Responses API at `reasoning.effort=high` researches through the existing Scrapling-backed Clue tools and drafts from permitted technical profiles, selected descriptive-profile/style context, and selected CV references. The Researcher receives no candidate profile; Diagnoser receives the selected CV and job/Jev context; Recruiter and Rewriter receive permitted technical profiles after the individual listing trigger; only Rewriter receives descriptive context and selected writing references. Before each generation, Clue sends the complete stage request to OpenAI's token-count endpoint, checks it against the current model context window, and reserves local spend from the exact input count and stage output allowance. Selected profile text is not cut off by character limits. A reviewable packet requires Jev's explicit resume approval, supported factual content, and at least two role-sourced cover-letter paragraphs; a failed gate creates no document artifacts. Jev confidence is recorded for evaluation but is not calibrated and does not override its decision label. Only owner-authored descriptive profiles can support directly stated preferences. Unknown or AI-assisted descriptive profiles guide style only and cannot support first-person or factual claims. The owner may choose a base CV or permit the agent to recommend one from selected references, and may ask it to preserve or improve structure. Multiple CVs remain private local content/layout references; originals stay unchanged. Clue cannot change the saved Jev match, send messages, or submit applications.

The repository template keeps `OPENAI_API_KEY=` empty. API calls require a key, separate data-sharing consent, a monthly cap, a per-opportunity cap, and a current rate card. After reviewing the packet, the owner can use the dossier's local email preview to copy the publicly sourced recipient, subject, and body, select files from the approved packet, and download them together as a ZIP. No Gmail setup is needed for that handoff. The optional Clue Gmail adapter can separately create an unsent draft from the exact approved recipient, subject, and body. The owner sends the message and submits applications manually. The Gmail API scope that supports draft creation also permits sending, so the adapter exposes draft creation only. This Codex session's GitHub/Gmail connectors do not transfer to the API agent.

The Applications workspace gives every owner-triggered preparation request one local dossier. It keeps the job snapshot and stage with current and older packet files, contact research, outreach drafts, reminders, and owner-saved submission receipts. The existing `/preparations` links remain compatible. The workspace requires no Google connection; the optional Gmail draft adapter remains a separate action.

The existing search flow may automatically discover, deduplicate, filter, and run Jev matching. No Researcher, contact crawl, or writing stage runs for a mined or selected listing by default. An eligible listing offers its own **Prepare application** button; clicking it starts the research and document packet for that job only. There is no bulk or scheduled auto-start. Mock interview practice is a separate optional trigger. A distinct GPT-6 Luna Researcher gathers public, sourced role/company/team information and contact evidence; it has bounded crawler access but receives no CV or private profile claims. The Diagnoser, Recruiter, Rewriter, and optional Hiring Manager practice stages cannot browse. Diagnoser reports observable resume text/layout risks without claiming exact ATS simulation. Recruiter maps job criteria to approved claims and exact technical-profile evidence references and shows Jev's result read-only; any coverage measure describes CV evidence coverage, not fit. Rewriter uses Google's X/Y/Z accomplishment pattern only when supported by approved claims or cited profile excerpts and never invents numbers. Jev separately checks each generated fact against only its linked evidence; its decision cannot change matching. Hiring Manager conducts mock interview practice and evaluates the owner's answers, not candidate-job fit. The latest `SYN-02` computer-vision run passed synthetic filtering, all four supported content blocks, Jev's final resume approval, packet quality, agent checks, settled usage, DOCX reopen, and visual inspection. A latest repeated `SYN-01` case returned Jev `review` and correctly stopped before GPT; an earlier complete `SYN-01` run passed, so label variance remains visible. The supplied profiles are local only; no real profile data has been sent to an API. Owner review of the exact synthetic packet remains open. See the [PLAN-020 evaluation record](evaluations/PLAN-020-evaluation-results.md). Automated reminders, external tracker synchronization, cohort analytics, and an optional worker remain deferred.
