# Definition gate

**Definition status:** PASS — product and bounded-pilot definition complete  
**Personal local-use readiness:** PARTIAL — TypeSafe account terms, ongoing source approvals, local device protection, and personal relevance calibration remain
**Reviewed:** 2026-09-30

This gate separates “is the personal app defined?” from “is it ready to use with the owner's real CV and rely on its rankings?” The first answer is yes. The second needs a few provider and local-runtime checks.

| Definition concern | Status | Decision and evidence | Next evidence |
|---|---|---|---|
| Purpose and intended user | PASS | The owner searches for themself using a CV and preferences in a single-user local app; no employer-side candidate selection or public service. | Revisit only if the owner later chooses to offer it to others. |
| Geography and coverage | PASS | Geography remains a user input. The first profile is fully remote work from Milan/Italy; five no-key feeds/APIs are enabled and representative samples confirm generic remote, EMEA, and missing location data must remain uncertain. PLAN-001 M2 compared one transient EU Lever API/page sample; it did not approve that board for indexing. | PLAN-001 M3 will extend source/relevance evidence; per-board terms, display, attribution, and retention review still gate ongoing ATS use. |
| Scope and non-goals | PASS | Discover, filter, rank, save/hide, and open original postings. No automated applying, application submission, or employer contact. | No further definition needed. |
| Search workflow and result vocabulary | PASS | CV/profile review; where the user will work is a search input; self-described work-authorized countries remain local reference and are not interpreted as legal eligibility; hard filters plus weighted preferences; eligibility evidence, confidence, unknowns, source and timestamps; save/hide/open-source. | Validate labels against real Italy/Europe listings. |
| Pilot defaults | PASS | PDF/DOCX first; English UI; default 30-day posting window; 24-hour “recently checked” label; a listing in an unvalidated language may show without a Jev score; [WCAG 2.2 AA](https://www.w3.org/TR/WCAG22/); a 30-second p95 search target on an already indexed pilot set. | Measure usability, language handling, accessibility, and response time during pilot. |
| Source acquisition policy | PASS | The enabled five-source set is Jobicy, RemoteJobs.org, Remote OK, Remote First Jobs, and Startup Jobs, each with a documented $0 path, attribution/direct link, refresh, and local retention. EURES is not integrated; ATS and other aggregators remain `Review` per the [source review](../research/source-discovery-and-crawl-review.md) and ADR 0003. | For each ATS board, check ongoing display, attribution, refresh, and retention terms before enabling it; the source list remains intentionally incomplete. |
| Crawling policy | PASS | Scrapling is selected for bounded local crawling of registered public HTML job and career pages; feeds/APIs remain direct connectors. Crawl outside the request path, respect source controls, stop on blocks, and exclude stealth, proxy rotation, CAPTCHA bypass, logged-in automation, and SERP scraping. | Validate the Scrapling adapter and each source parser during the local pilot. |
| Jev role and ranking | PARTIAL | TypeSafe Jev remains the required fit evaluator. PLAN-001 M3a scored five eligible synthetic postings in one request; Jev and an exact-keyword baseline both scored `nDCG@5 = 1.0` against assistant-authored synthetic grades. This verifies the integration and metric path, not personal usefulness or superiority over the baseline. | Owner reviews the synthetic examples or defers personal calibration; continue to show evidence and uncertainty and never imply hiring probability. |
| Budget | PASS | Owner cap: $5/month all-in for TypeSafe Jev and $0 for every other source/service. App-side $4 rolling reserve and stop behavior are covered by local tests; the synthetic request used 1,574 input tokens, with `$0.00006611` estimated by the app ledger at its configured rate. | Verify provider credit conversion, taxes, automatic refills, and the account's all-in hard stop. |
| Candidate data and deletion | PASS for pilot definition | CV, saved profile, preferences, local job index, and results live on the owner's device with user-controlled deletion. M3a used only synthetic data and a disposable database; M3b tested local deletion and manual backup/restore using synthetic data. No real CVs until TypeSafe terms and local device protections are checked. | Owner confirms device encryption and file permissions; verify TypeSafe terms, telemetry, retention, deletion, and transfer. |
| System boundaries | PASS for local plan | Local profile → source connectors → local normalization/dedup/freshness → deterministic constraints → Jev → transparent results. FastAPI/Jinja/SQLite is selected; no crawl runs synchronously for each search. | Validate local file/key handling and source adapters in PLAN-002. |
| Validation plan | PARTIAL | M3a's synthetic-only benchmark measured hard-filter correctness, confidence, stale/duplicate/link signals, Jev cost, and Jev/keyword `nDCG@5`. Both rankers scored 1.0 on assistant-authored labels; this small constructed set does not establish personal relevance, live-source freshness, latency, or comparative ranking quality. M3b tested synthetic local backup/restore and deletion. | Gather the owner's relevance judgments or defer personal calibration; complete TypeSafe, source, and local-device checks. |

## Checks before using a real CV or relying on rankings

These items cannot be closed by product research alone; they require provider terms or local runtime evidence.

1. Confirm the TypeSafe API's personal-use terms, Order/DPA, account-specific credit conversion, $5 all-in stop, retention, telemetry, deletion, and data transfer terms before sending a real CV-derived profile.
2. The initial free source set is selected and its feeds were smoke-checked; M2 added a transient Lever API/page parser comparison. Continue source-by-source terms validation before enabling any employer/ATS board. The [source review](../research/source-discovery-and-crawl-review.md) records coverage, limits, and alternatives with conflicting or incomplete terms.
3. Confirm local file permissions and device encryption. Manual backup/restore and user-controlled deletion are documented and tested with synthetic data; no hosted accounts, authentication service, or shared deployment is planned.
4. Revisit privacy or employment/AI review only if the owner later offers the app to other users.
5. Review the synthetic benchmark examples and provide personal relevance judgments, or explicitly defer personal calibration before relying on rankings.

## Gate decision

The **definition gate passes for a single-user local feasibility build**. The Milan/Italy remote search focus, user inputs, local data boundary, five-source strategy, crawler behavior, budget, and Jev's role are defined in the product definition, source review, ADRs, and [PLAN-001](../plans/PLAN-001-free-local-source-discovery.md). Before real CV use, confirm TypeSafe's terms and local privacy controls; all other costs remain $0.

This gate does not authorize a public deployment. Until TypeSafe and source conditions are checked, use synthetic data and the documented $0 source paths; do not bypass site controls or exceed the Jev cap.
