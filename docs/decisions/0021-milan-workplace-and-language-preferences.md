# ADR 0021 — Prefer remote work; allow Milan roles without Italian requirements

- Status: Accepted; ambiguous-location treatment superseded in part by ADR 0022
- Date: 2026-10-05
- Decision owners: Clue owner

## Context

The previous search default treated remote as a hard workplace constraint. The owner prefers remote work but accepts hybrid and on-site AI engineering roles located in Milan. An English requirement is acceptable; an explicit Italian-language requirement is not.

## Decision

1. New searches default to `workplace=remote_preferred`. Remote roles must still be eligible from the selected `work_from` country. Remote-only remains an explicit option.
2. Add an editable local office city, defaulting to Milan. Under remote-preferred mode, confirmed hybrid/on-site roles in that city are eligible. Explicit other-city physical roles conflict. Missing or ambiguous city/workplace evidence stays in review when unknown locations are enabled.
3. Exclude listings that explicitly require Italian language ability. English-language requirements are acceptable. Italian as a bonus, preferred, or optional skill is not a conflict. Ambiguous or absent language evidence remains eligible for Jev review.
4. Use a conservative local detector for explicit Italian requirements to avoid Jev calls on known-ineligible roles. Add a typed Jev language filter for remaining listings and keep remote preference in the existing preference dimension.
5. Report local exclusions by reason in search coverage. Preserve the original listing and its source URL for every retained role. Store the complete workplace, local-city, and language criteria in each run snapshot.
6. Existing historical search snapshots keep their original criteria. Reassessment of unchanged exact URLs under the new scope uses the existing “Include previously reviewed listing links” option.

## Consequences

- Eligible local Milan office roles can join the AI engineering shortlist while remote roles retain a preference advantage.
- Remote location eligibility remains independent of workplace type; an unqualified “remote” label does not prove a company can employ someone in Italy.
- A posting can omit language conditions or phrase them unusually. The local detector may miss a requirement; Jev and the result's qualification evidence handle remaining cases, and the employer listing is authoritative.
- When the local city or physical work location is ambiguous, the result remains reviewable instead of being treated as a confirmed match.
- ADR 0022 supersedes this ambiguity behavior for the default `remote_preferred` search: unverified remote geography and workplace/city evidence are excluded before Jev. The rest of this decision, including the Milan exception and language rule, remains active.

## Validation evidence

Static Python compilation, Ruff, template compilation, and whitespace checks; no live crawl, Jev call, app session, or test suite during this milestone.
