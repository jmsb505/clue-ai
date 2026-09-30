# ADR 0007: Use manual X lead discovery

**Status:** ACCEPTED
**Date:** 2026-10-01

## Context

The owner finds job opportunities in X posts and wants Clue to use the resulting links as candidate leads. The app is local and personal. The owner's recurring spend limit is $0 for everything except TypeSafe Jev. X currently prices post reads at $0.005 per returned post, and its automation rules warn against scripting the X website. Clue already uses Scrapling for reviewed public employer and ATS pages, but X is not an approved Scrapling target.

Links and post contents are untrusted. A server-side preview or automatic fetch could follow redirects or reach local network services; copied descriptions may also contain prompt-injection instructions.

## Decision

Use X as a **manual discovery and lead-provenance source only**:

1. Clue builds a search URL from role/location terms the owner chooses. Only an explicit click opens X in a new tab.
2. The owner inspects the post and the original employer/ATS listing in their browser. Clue asks for the X status permalink and the final HTTPS job page URL, plus job details copied from the posting.
3. Clue validates the URL shapes, displays the destination hostname, and stores those facts locally. Clue never calls the X API, scrapes X, resolves a short link, fetches/unfurls a pasted destination, or opens a link automatically.
4. Manual leads join the ordinary local job index and may be filtered/ranked with the existing flow. Jev remains opt-in and requires the separate score action; post text is not sent, and job/candidate text is treated as untrusted data.
5. Results identify manual X leads and do not imply Clue rechecked the vacancy.

## Consequences

- No API or feed cost is added; the source fits the owner's current $0 source budget.
- X search breadth, post relevance, destination trust, location eligibility, and vacancy status depend on the owner's review.
- X search is not automated or represented as integrated coverage. Scrapling and scheduled source refresh must never visit X.
- Destination-host checks reduce malformed and common shortened-link risks, but do not certify that a site or job is legitimate.
- Revisiting automated X access requires a new owner decision after reviewing current X policy, pricing, and terms.

## Evidence

- [X API pay-per-usage pricing](https://docs.x.com/x-api/getting-started/pricing)
- [X automation rules](https://help.x.com/en/rules-and-policies/x-automation)
- [X link safety guidance](https://help.x.com/en/using-x/how-to-post-a-link)
- [X search help](https://help.x.com/en/using-x/x-search)
- [OWASP SSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html)

## Reversibility

The manual page, source marker, and local lead provenance are additive and can be reverted without removing the existing feeds or employer/ATS connectors. Existing local data deletion clears all lead rows through the job/source relationships.
