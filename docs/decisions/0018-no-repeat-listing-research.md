# ADR 0018 — Do not repeat unchanged listing research

- Status: Accepted
- Date: 2026-10-04
- Decision owners: Clue owner

## Context

Job boards must be revisited to find new vacancies, but cached postings were being placed in each new search again and sent to Jev. Different feeds can also refer to one posting through the same public URL. The current database index deduplicates cached rows; it does not distinguish a new listing from an unchanged URL the owner has already reviewed.

## Decision

Keep a small local URL registry, separate from expiring job rows and search snapshots. Store each canonical listing URL, a signature of material posting fields, and its last successful Jev assessment time. Add known listing URLs from each source attached to the same indexed job as aliases. Do not include a parent/category `context_url` as a job identity.

Refresh publisher indexes on their existing schedules. Exclude an unchanged researched URL from a later run's candidate snapshot and Jev request. JustRemote and company Scrapling crawlers also skip fetching a researched detail URL while continuing to refresh their public index, careers, and sitemap pages. If a refreshed API/feed returns materially changed title, description, location, employment, compensation, or expiry data for the same URL, offer it as an updated listing. A detail-only page is not refetched automatically after assessment; the owner can include previously reviewed links in a search to bring those saved postings back for assessment.

Write a URL to the registry only when that listing has a fit score and complete filter decision. Source failures, interrupted work, missing/incomplete Jev answers, and runs with Jev disabled must not mark candidates as researched. Deduplicate the exact same listing URL within one run as well as across runs. Preserve different URLs because they can represent distinct vacancies, employers, or location variants.

An ordinary search reset clears cached listings, result snapshots, and refresh timers but preserves the minimal URL/signature registry. Full personal-data deletion removes it. Show this distinction in the reset output and provide an explicit include-reviewed option on the search form.

## Consequences

- Search results focus on new and materially changed posting URLs without stopping source refreshes.
- Jev requests and spend are avoided for unchanged postings already assessed.
- Previous run snapshots remain available through search history.
- A publisher that silently reuses a URL without exposing changed content will not automatically reveal a repost. The owner can deliberately include previously reviewed listings; public feeds that expose updates can trigger a fresh assessment.
- The URL/signature ledger is local and has no foreign key to cache rows, so ordinary cache expiry/reset cannot erase no-repeat behavior. It contains no CV text or Jev decision rationale.
