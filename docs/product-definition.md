# Product definition

**Status:** DEFINED FOR SINGLE-USER LOCAL FEASIBILITY BUILD; explicit requirements are marked NORMATIVE  
**Owner:** project owner  
**Updated:** 2026-09-30

## Purpose

Build a single-user, local-first job discovery app for the owner’s personal use. The user supplies a CV and search preferences. The app searches accessible job sources, checks user-set constraints, uses TypeSafe AI's Jev model to score role fit, and returns a ranked list with enough evidence for the person to decide what to inspect. The person opens the original listing and chooses whether to apply.

The product helps a person find and compare available jobs. It does not choose candidates for employers or submit applications.

## Intended user

**NORMATIVE:** An individual job seeker searching on their own behalf. The user controls their profile, search conditions, and next step.

**NORMATIVE:** The search geography is selected by the user for each search or saved search. A single launch country is not assumed.

**NORMATIVE initial focus:** The first source-coverage and ranking pilot should find fully remote jobs a person can perform while based in Milan, Italy. Include roles that explicitly allow work from Italy, the EU/EEA, Europe, or worldwide. The product remains geography-selectable; this focus is a validation profile, not a permanent country restriction. Do not assume the user's citizenship, residence permit, or work authorization. Ask separately which countries the user is authorized to work in and whether sponsorship is needed.

## Owner requirements

- Take a CV and explicit guiding parameters as search inputs.
- Search across a broad set of job boards, employer career pages, and other sources, within terms, licensing, privacy, technical, and cost limits.
- Use TypeSafe AI's **Jev** model for the candidate-to-listing fit evaluation.
- Rank and list current job openings for the user.
- Do not automate job applications. The user reviews a result and applies through its source if they choose.
- Keep one saved profile, CV, search preferences, and job index locally on the user's device, with clear controls to delete that data.
- Build for one personal user on one local machine. No registration, hosted accounts, public service, multi-user support, or scale target is in scope now.
- Use a friendly interface with the directness and visual approach of [Jobbie](https://jobbie.bot/), while keeping the product focused on search and review.
- Keep recurring spend at **$0 for every component and data source except TypeSafe Jev, capped at $5/month**. Run the app and store data locally; no paid hosting, authentication, email, analytics, or other services are needed.

**Budget constraint:** The owner caps Jev allocation at $5 per rolling 30 days and requires $0 for other services. The app reserves up to $4 for its own Jev requests. On 2026-09-30 the owner waived provider-side account, terms, and refill verification for this local personal use; account-wide billing, credits, and charges remain unverified, not guaranteed by the local ledger. If the app-side cap is reached, pause Jev evaluation and label affected listings “fit not evaluated”; do not silently substitute another model. Use no-cost feeds, APIs, and public employer pages for the local workflow.

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
| Seniority and scope | Level, years as a rough hint, responsibility scope, or people-management preference |
| Skills and credentials | Required and preferred skills, language fluency, licenses, education, certifications |
| Company and work preferences | Industry, company size, sector, travel, schedule, or user-selected exclusions |
| Freshness | Posted within a chosen period; exclude seen, saved, or dismissed results |
| Importance | Must-have constraints plus adjustable weights for preferences |

Never use protected or sensitive traits such as race, religion, health, disability, age, sex, or family status to score job fit. Do not infer such traits from a CV. A job-specific legal eligibility condition can be handled only when it is explicit, necessary, and user-controlled.

## Bounded pilot defaults

These are working defaults that complete the pilot definition; they can be revised if user research or feasibility evidence points elsewhere.

- Accept PDF and DOCX CVs first. The user reviews and corrects extracted facts before saving the profile.
- Start with an English interface and validate Jev rubrics by CV/job-description language. A listing in a language without a validated rubric may still be shown, but receives “fit not evaluated” rather than an unsupported score.
- Use Milan, Italy as the first search test location, with fully remote work as a hard preference and Italy, EU/EEA, Europe, or worldwide as explicit eligibility scopes. Keep the person's work authorization as a separate user-controlled input.
- Classify location evidence as `Eligible here`, `Needs verification`, `Not eligible`, or `Unknown`. Italy, EU/EEA, Europe, and worldwide are positive only when stated and not contradicted. Treat EMEA, timezone overlap, or an unqualified “remote” label as `Needs verification` unless the posting also makes Italy eligibility explicit. Exclude an explicit incompatible country restriction from an Italy-only search. Preserve the exact evidence passage and source URL.
- Default to jobs posted within the last 30 days, with shorter freshness filters available. Show the employer's datePosted, if supplied, separately from the platform's last-checked time.
- Call a listing “recently checked” only when the source was checked within the past 24 hours. If a source cannot meet that interval or its terms require a longer refresh, label its age and avoid claiming the listing is live.
- Target a 30-second 95th-percentile response for a search over an already indexed pilot dataset. Crawling happens out of band, not in the user's request path.
- Target [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/) for the responsive interface. Use Jobbie's friendly, card-based scan patterns and keep the original employer/source action clear.

## Core workflow

1. The user opens the local app, uploads a CV, and reviews the extracted candidate profile before saving it on the device. A saved work-authorization list is local reference; the app does not infer legal eligibility from it.
2. The user starts a search, chooses where they will work from and a role target, and labels must-haves and preferences. The first pilot profile starts from Milan, Italy and fully remote work; the user can change it.
3. An out-of-band ingestion process fetches from geography-relevant `Approved` sources in the source registry, normalizes fields, removes duplicates, and records source and freshness information. A user search never starts an unbounded crawl.
4. Ordinary software applies exact user-defined constraints. Missing listing data remains “unknown” unless the user chooses to treat it as a hard exclusion.
5. Jev evaluates bounded, job-related fit questions using the candidate profile and listing. The system ranks the evaluated results using the user's weights.
6. The user reviews match details, saves or dismisses jobs, and opens the original source page. They can manually record that they applied outside the platform.
7. The user can revise their local profile or search and delete the saved CV, profile, preferences, indexed jobs, and results through product controls.

## Jev's role in matching

**NORMATIVE:** Jev is the required model for fit validation. The user asked for Jev to evaluate candidate fit against each job listing.

**WORKING recommendation:** Use typed Jev questions for bounded fit judgments and combine job-related dimensions in ordinary code using the user's stated weights. Exact constraints, permissions, sorting, and data handling remain in ordinary software. The first implementation uses categorical `Choice` questions with five fit levels and a separate `unknown` answer; returned levels are mapped to a normalized 0–1 fit signal and are not calibrated.

Jev returns structured decisions, not explanatory prose. It cannot by itself provide trustworthy CV evidence snippets or explain a score in natural language. Build explanations from the parsed CV facts and the original job text, and show the source passages where possible. Distinguish “not found in the CV/listing” from “does not match.” Show uncertainty where evidence is missing or Jev is unsure.

Call the result a **fit score** or **match score**, never a hiring probability or prediction that an employer will interview or hire the person. The score is a guide for the user's own review. Do not show a 0–100 number as calibrated until a representative evaluation supports that mapping.

Run Jev after retrieval, deduplication, and hard filters so calls are spent on plausible postings. Preserve the model/version, rubric, candidate-profile snapshot, listing snapshot, and response needed to reproduce a result, subject to approved retention limits. If Jev is unavailable or returns low-confidence results, label the result accordingly rather than silently substituting another evaluator.

## Results and interaction

Each result should make these fields easy to scan:

- role, employer, source, original posting link, location and work arrangement;
- posted date, last checked time, salary and currency when supplied;
- match score, user-weighted criteria, confidence or evidence status;
- strengths and gaps grounded in CV and job-description evidence;
- save, dismiss, and open-source actions.

Show the enabled sources and regions searched. Only show listings from approved sources. Do not imply coverage of “the whole internet” or that a listing is open now unless the source status was checked within the stated freshness window. Keep a clear distinction between the employer's posted date and the date this platform observed or verified the listing.

## Source discovery and crawling policy

**NORMATIVE direction:** Include company career pages, documented free APIs, and feeds as primary discovery routes. For the initial Milan/Italy remote focus, prioritize sources that expose where a job may be performed, not only a generic `remote` flag. Prefer a documented, zero-cost feed/API; then the employer's public ATS board; then its job sitemap, RSS/Atom, or `JobPosting` JSON-LD; use a bounded HTML crawl only when needed and permitted. Record cost, terms, geographic eligibility, attribution, allowed cache/retention, request limits, and canonical link for every source.

The M1 pilot registry enables five no-key feeds/APIs: Jobicy, RemoteJobs.org, Remote OK, Remote First Jobs, and Startup Jobs. Their source-specific refresh, local-retention, attribution, and direct-link rules are in the [source review](research/source-discovery-and-crawl-review.md). This is a broad but incomplete registered set, not internet-wide coverage. EURES is a useful manual portal outside the integrated source set until an official vacancy API and reuse path are documented.

The source registry states are `Approved`, `Review`, and `Blocked`. Approve a source after confirming $0 cost at expected personal use and recording its public path, attribution, geography, and local caching/refresh rules. Employer-by-employer opt-in is not a default step; if published source rules conflict with the planned local use, mark it `Review` or use another source. A public page or permissive `robots.txt` alone is not approval. On access denial, rate limit, CAPTCHA, bot challenge, or explicit block, stop that connector. Do not bypass the restriction with stealth mode, proxy rotation, browser impersonation, authentication, or search-result scraping.

Scrapling is the selected crawler for registered public HTML job and career pages, including employer and ATS pages. Use its ordinary Spider/static-fetching path behind the source connector boundary. Enable `robots_txt_obey` explicitly, cap the Spider at four concurrent requests overall and one per domain, and use a two-second base `download_delay` that increases when source rules require it. Keep documented feeds and APIs as source-specific connectors. Never use stealth, proxy rotation, browser impersonation, CAPTCHA solving, or anti-bot bypass.

## Product boundary

### In scope for the first product increment

- Local candidate profile and PDF/DOCX CV upload with an edit/review step.
- Per-search role, geography, must-have, and preference inputs.
- A source registry, approved source connectors, normalized listing records, duplicate handling, and freshness checks.
- Jev-based fit scoring and a transparent ranked-results view.
- Saving, dismissing, revising search criteria, and opening the employer or job-board source.

### Out of scope

- Automated applications, application-form filling, screening-question answers, or employer contact.
- Employer-side recruiting, candidate selection, or workforce-management decisions.
- A claim that every public or private job board is covered.
- Resume rewriting or generated application materials in the first increment.
- Universal country/source coverage, hosted infrastructure, or additional framework selections beyond the local Scrapling crawler and feasibility-stage needs.
- Hosted accounts, multi-user access, public listing redistribution, or scaling beyond the owner's local use.
- Paid job feeds, paid infrastructure, or other paid services beyond the monthly TypeSafe ceiling.

## Local data and privacy behavior

**NORMATIVE:** Store the saved CV, reviewed profile, search preferences, cached job listings, and results locally on the owner's device. Provide a single clear action to delete the local profile and its associated data. Do not create a hosted account or upload the job index.

**WORKING recommendation:** Do CV parsing and job indexing locally. Do not send name, email, phone number, or exact home address to Jev when those fields are not needed for job-fit scoring. Send only the minimum relevant profile and listing text for fit evaluation. The work and education history can still identify someone and remains personal data. Explain which fields leave the device, where Jev processes them, and any retention/telemetry behavior.

Keep the original CV, extracted profile, search criteria, saved jobs, and fit results under user-controlled local deletion. The owner waived confirmation of device encryption for local data and backups on 2026-09-30; the project does not claim encryption or Windows permission evidence. TypeSafe receives reviewed profile and listing fields only after the in-app disclosure/opt-in and an explicit score action. The owner waived account/terms verification; account-specific provider retention, telemetry, and deletion behavior remain unverified.

## Quality and validation direction

Before relying on rankings in personal searches, evaluate the pipeline on representative, synthetic or otherwise appropriate CV/listing pairs. Compare results with the owner's judgments and a simple keyword baseline. Review precision and recall in the first results, ranking quality, probability calibration, confidence handling, missing-data behavior, duplicate and stale-listing rates, and cost per search. Inspect results across role families, languages, seniority, and regions. Do not collect or use protected traits as ranking features.

Measure personal usefulness through save/open/dismiss actions and explicit “why is this a match?” feedback. Keep “unknown” available when a CV or listing lacks evidence. The user should be able to correct their profile and change criterion weights without re-uploading their CV.

## Decisions still open

The personal app's product behavior and source policy are defined. The following are remaining evidence tasks or owner choices, rather than unanswered product goals:

- Confirm each source's personal-use terms, free limits, and geographic coverage; see the [source discovery review](research/source-discovery-and-crawl-review.md).
- Provider account/terms and device-encryption checks were waived by the owner on 2026-09-30; the app's $4 request reserve and explicit score action remain, but provider-wide limits are not verified.
- The synthetic backup/restore and deletion path is tested; Windows file permissions and encryption are not verified or required by owner decision.
- Review the synthetic relevance examples and provide judgments or defer personal calibration before treating scores as personally validated.
