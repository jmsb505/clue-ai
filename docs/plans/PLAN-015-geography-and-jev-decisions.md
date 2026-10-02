# PLAN-015 — Correct geography and retained Jev decisions

**Status:** M1 validated and delivered in this checkpoint
**Created / updated:** 2026-10-03

## Objective and evidence

Correct the owner's reported LATAM opportunity and systematic zero Matches. The saved completed run contains 908 scored listings: 651 conflicts and 257 reviews. Raw Jev answers contain four all-supported listings. A local 0.80 confidence gate demoted every one of the 440 additional-requirements matches, preventing any aggregate match. LATAM was not understood by the location parser; Jobicy's remote feed also lost its workplace metadata.

## Scope and constraints

One independently deliverable corrective milestone. Preserve Jev assessment of the full candidate set, paid junior/intern criteria, Italy eligibility, AI-weighted fit, contact redaction, budget and existing PLAN-007 edits. No new sources, dependencies, live crawl or paid assessment. Use implementation-plan and milestone-delivery, Conda gen, and the owner's standing direct-to-main milestone authorization.

## M1 — Honest filter decisions and explicit geography

- Preserve valid categorical Jev decisions regardless of uncalibrated numeric confidence; retain review for invalid/nonfinite confidence or missing evidence explicitly reported by Jev.
- Recognize bounded geographic regions with target membership; inspect explicit hiring restrictions throughout the stored description, without treating headquarters/customers or timezone preferences as restrictions. Explicit incompatible work regions override model review/match, with separate attribution and retained raw answers.
- Retain Jobicy remote-feed workplace metadata.
- Repair completed saved results transactionally from retained answers and existing job facts, with backup, idempotency and active-run refusal. Preserve scores, private profile, spend and source state; record policy/evidence without claiming a new Jev assessment.
- Update affected product/decision/operations documentation and requirement-check attribution.
- Validate low-confidence decisions, region unions/membership, late restrictions, nonrestrictive mentions, partial responses, parser behavior, backup/rollback/idempotency and saved-run rendering. Analyze the real 908-listing corpus offline before and after; do not promise a match count independent of evidence.

**Acceptance:** Airtm's LATAM job is a location conflict for Italy, not an opportunity. Valid low-confidence model matches/conflicts remain visible as their categorical decisions. Unknown pay stays review. No missing answer becomes a match. Saved data repair changes only derived filter/location decisions, count/message and correction notes, retaining original answers and scores. Targeted tests and staged-index validation pass before commit/push `fix: honor Jev decisions and exclude incompatible remote regions`.

## Recovery and limitations

Stop Clue before local repair and leave it stopped. SQLite backup can restore the previous snapshot with the server stopped. Reverting code does not restore data automatically. Jev decisions and confidence are not calibrated hiring probabilities; model errors remain possible. Region membership is deliberately bounded; unknown target geography stays uncertain rather than guessed. No live job availability check or new model-quality evaluation is performed.

## Progress

- Read-only investigation completed; no search or scoring request made.
- Implemented categorical interpretation, explicit region constraints, Jobicy remote metadata, separate override attribution and backup/transactional repair. Recorded ADR 0015 and updated product and operations documentation.
- Exported the staged Git index to `.cache/plan015-index`; Conda gen validation: **102 passed, 2 deselected**. The two deselected crawler-policy tests expect obsolete robots/concurrency settings; both were reproduced as failures against an exported unchanged HEAD (`cf4c1c1`). No regression in those controls is claimed or concealed. Ruff passed on changed Python modules/tests and `git diff --cached --check` passed.
- Offline preview of all 908 real saved results: **4 matches, 111 review, 793 conflicts**. Airtm AI Automation Engineer changed to location conflict with LATAM evidence; Jev's original review and 0.75 confidence remain inspectable. Confirmed exact retention of all fit scores/dimensions, raw model choices/confidence, profile, spend, source/company/query state and foreign-key integrity.
- Stopped the running Clue process tree with the existing helper; the sandbox initially denied process access, then the same authorized helper succeeded with process permission. Applied repair to the actual local database and repeated all retention/integrity checks successfully. Backup: ignored `.data/backups/before-matching-repair-20261002T225731Z-366e9a68.sqlite3`.
- App remains stopped and port 8000 is free. No paid Jev request or live source crawl was made. Existing PLAN-007 edits remain unstaged; checkpoint targets main under the owner's standing authorization.
