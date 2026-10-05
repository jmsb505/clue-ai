# Discovery reach and candidate qualification assessment

Updated: 2026-10-05

## Search and identity flow

An owner-started search refreshes due feeds and public employer sources, normalizes each listing and retains its publisher URL/credit, applies the local AI-engineering focus screen, deduplicates exact canonical URLs, then excludes unchanged researched listing URLs before the Jev batch. Index pages continue to refresh so new listing URLs can be discovered. Changed posting content at the same URL can be assessed again; distinct URLs are not fuzzy-merged. The local URL ledger persists through ordinary search reset and is removed on full personal-data deletion. See [ADR 0018](../decisions/0018-no-repeat-listing-research.md).

The source registry has 15 built-in entries: 12 automatic feed/API/crawler sources, one manual X lead route, and two manual-only boards. It also supports owner-added validated public sources and employer-linked ATS boards. The enabled automatic sources include two additional free APIs from [AI Dev Jobs](https://aidevboard.com/docs) and [Dev Global Jobs](https://devglobaljobs.com/developers). The source review records all current use conditions, costs, attribution and refresh behavior. These sources add coverage; they do not make search internet-wide.

Each new API source runs at most five varied AI role-family queries per daily source interval, one page for each query, with a one-second gap. The AI Dev Jobs page limit is 50; Dev Global Jobs is 100. Only an explicitly remote-only search passes the documented remote parameter; remote-preferred mode leaves workplace broad and applies the user's location policy locally. An HTTP 429 stops that source and marks it paused; no retry is made. Raw, parsed, AI-focused, new, and existing exact-URL identities appear separately in search coverage.

## Workplace and language scope

New searches default to remote preferred, with remote work eligible only when supported from the selected country. The default local-office city is Milan: confirmed hybrid/on-site jobs there remain eligible; explicit hybrid/on-site locations elsewhere are excluded. Missing or ambiguous workplace/city evidence stays in review when the user includes unknown locations. The city is an editable search input.

The owner accepts English-language requirements and excludes an explicit Italian-language requirement. A bounded local text detector removes clear mandatory-Italian cases before Jev, while preferred Italian, English requirements, and ambiguous language evidence remain eligible. Jev receives a separate typed language filter question so unclear cases can be reviewed. Coverage records known local-scope exclusions. Remote preference is included in Jev's preference signal and never overrides hard geography or language constraints. See [ADR 0021](../decisions/0021-milan-workplace-and-language-preferences.md).

## Jev decision flow

For each locally eligible, not-yet-researched listing in the result snapshot, Jev returns its existing five fit dimensions and independent search-filter checks. Clue also extracts at most four short explicit employer requirements, preferring stated mandatory qualifications and then preferred qualifications. Requirements are included as untrusted data in the Jev state, not instructions. The saved profile is minimized using the existing contact-redaction path. The original CV file, direct contact details, home address, source URL and application URL are not added to the fit state; saved work-authorization countries, sponsorship preference, search criteria, parsed profile fields, and selected listing details are included for evaluation.

Each extracted item receives a typed `met`, `partly_met`, `not_met` or `not_enough_evidence` status and model confidence. Missing information is `not_enough_evidence`; `not_met` requires direct contradictory profile evidence. A separate typed seniority check compares the candidate's documented experience with explicit level, responsibility and years evidence from the listing. It does not infer age or work history from education dates. If the role or profile supplies too little information, seniority is `not_enough_evidence`. All answers, including an explicit `not_enough_evidence`, are required for a complete evidence assessment. Missing or invalid Jev answers keep that URL eligible for retry in the no-repeat ledger.

The checks and extracted listing text are serialized inside the existing `search_results.dimensions_json` row with the fit score and filter decisions. No migration is needed, and later edits to the active listing do not rewrite these per-run JSON values. The result detail labels extracted requirements as a small partial checklist, keeps preferred items distinct, shows seniority evidence, preserves the source link, and explains uncertainty. Historical results written with older rubric versions have no fabricated qualification panel.

The existing 80,000-input-token Jev reservation and $4 application cap remain in force. The new questions are bounded to four qualification checks plus one seniority check per listing. Jev's score and these evidence checks are not hiring probabilities. The user opens the source listing to verify that the vacancy is active, the employer's complete requirements, paid status and work-from-Italy eligibility.

## Limits

The requirements parser is deliberately small and operates on normalized listing text. It can miss requirements expressed through unusual formatting, language, or very long paragraphs; “none detected” means none were extracted, not that the posting has no requirements. Results show the full source link and description for review. No personal fit calibration has been claimed. The source API response shapes were reviewed from public documentation but were not live-fetched during implementation; connector reach and real-world recall remain unmeasured until the owner starts a search.
