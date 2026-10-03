# PLAN-017 — AI engineering discovery before Jev

Status: M1 validated and delivered in this checkpoint
Created / updated: 2026-10-03

## Objective and motivation

The owner now wants AI engineering and closely related technical work, not generic transferable jobs. Junior/intern and paid requirements remain. Filter obvious noise locally before spending on Jev. This explicitly supersedes the earlier all-listings policy in ADR 0010 and the optional AI preference in ADR 0013.

## Current and desired state

The crawler normalizes every fetched listing and the service sends all active non-hidden/non-applied jobs to Jev. CV-derived target titles include past analyst work. Desired: a transparent, inexpensive AI engineering gate for board/company ingestion, cached candidates and scoring retries; focused discovery queries and stronger AI ranking. Jev retains final nuanced fit, geography and uncertain compensation/level checks.

## Scope, constraints and tools

Use existing Python/Scrapling architecture and Conda gen. No new dependency, paid service, automatic application, external CV upload or broad site crawl change. Preserve original CV/profile, application tracker, existing saved scores/history and unrelated PLAN-007 edits. Review attached CV with the PDF skill and the owner's public GitHub READMEs. Implementation-plan and milestone-delivery govern this checkpoint. No formal tests requested; use static checks and documented isolated runtime/corpus inspection.

## M1 — Focused ingestion and assessment

- Add a pure local classifier accepting AI/ML, agents/LLM/RAG, computer vision, ML deployment/platform and technical adjacent work with actual AI implementation evidence. Do not require literal junior or a salary amount.
- Reject explicit senior titles, explicit unpaid work and clearly unrelated/non-engineering titles before indexing or Jev. Report counts/reasons separately from deduplication.
- Apply the same gate to the existing cache and scoring retry, without deleting history or fabricating Jev decisions.
- Replace noisy derived search titles with supported AI role families; keep custom relevant titles. Increase defaults to AI 50, role 25, skills 15, experience 5, preferences 5, migrating only the previous standard defaults.
- Update Jev instructions, UI wording, README, product definition, architecture and ADR 0017.

Acceptance: AI/ML/agent/CV/inference engineering examples reach Jev; generic admin/analyst/sales/manual AI annotation jobs, senior engineering titles and explicit unpaid internships do not. Adjacent engineering with specific AI implementation remains eligible. Missing pay/seniority remains uncertain for Jev. Board and company parsed jobs, indexed jobs and retry jobs share the gate. Counts explain the reduced shortlist. Existing scores, raw cached records and applications remain intact. Custom weights remain intact.

Validation: Python compilation, Ruff and whitespace checks; read-only actual indexed-corpus review; isolated local service workflow with synthetic source/company outcomes and a captured Jev boundary (no live API/crawl); inspect the staged snapshot independently of PLAN-007. Record limitations and evidence before direct-main commit/push under standing authorization.

Expected checkpoint: `feat: focus discovery on entry-level AI engineering`.

## Risks, recovery and source of truth

Rule-based screening can miss unusual titles; accept technical adjacent roles with implementation evidence and sparse direct AI titles, and document that filtering is a relevance heuristic rather than a model assessment. Preserve cached records for recovery. Code rollback restores prior candidate selection; no schema migration is needed. Old saved runs retain their historical results; new searches use the focused policy, and scoring retries skip unrelated old candidates. No current search is automatically restarted and no additional Jev spend occurs during delivery.

## Progress and evidence

- Reviewed CV and public SmartOps-Agents, FPGA_Inference, CNN2FPGA and nlp-polimillionaire READMEs. Supported role families: AI agents/LLMs, model development, computer vision and inference/deployment. Generic analyst work is experience evidence, not the desired job target.
- Implemented the shared local screening gate, explicit exclusion reasons, focused alternative discovery queries, stronger default weights and revised fit rubric. Missing pay, unlabeled seniority, equivalent titles and sparse direct AI titles remain eligible. Role evidence excludes company introduction/closing marketing where recognizable. Sparse data scientist titles remain uncertain; detailed data scientist descriptions require model implementation evidence.
- Read-only inspection of the actual 931-row index retained 50 candidates and excluded 881: 501 explicit senior titles, 137 non-engineering roles and 243 without AI engineering evidence. This is a local shortlist, not 50 confirmed paid/junior/Italy-compatible matches. Existing two runs, 1,862 result rows, application state and 1,481 usage ledger rows were retained. No actual database change, crawl or paid call occurred.
- Isolated local service workflow: 17 synthetic board records yielded nine indexed focused jobs; two company records yielded one. One prior AI cache entry joined the run and one prior analyst entry stayed stored but was excluded. New run and captured Jev boundary both contained 11 focused jobs. Old broad retry retained all 12 historical rows while only passing the 11 relevant jobs to the scoring boundary. Coverage distinguished exclusions, records parsed and duplicate identities; usage ledger stayed zero and foreign-key check was empty.
- Manual classifier review retained ML/LLM/CV/MLOps/inference jobs and adjacent RAG backend/FPGA model deployment; rejected senior ML, unpaid AI internship, generic analyst, AI trainer, office internship, generic backend/company pitch, generic frontend and AI sales. Unlisted salary and negated unpaid wording remained eligible. Former standard weights migrated to 50/25/15/5/5; a custom AI weight of 41 was preserved. Captured Himalayas URLs used four separate alternative titles with Italy, not one combined title string.
- Python compilation and full-package Ruff passed. No formal tests were added or run. Live publisher recall and personal Jev relevance remain unverified; implementation verification made no network/model calls.
- Exported the staged Git index independently of unrelated PLAN-007 work and repeated the isolated workflow, compilation and Ruff with the same outcomes. Staged whitespace checks passed. Prompt engineering remained eligible; paid volunteer leave and explicit "not an unpaid internship" wording did not cause unpaid exclusions. No verification server was started and the owner's app remains stopped.
- Direct-to-main delivery uses standing owner authorization; the milestone changes, plan and ADR are included together. Unrelated search-history changes remain unstaged. No GitHub CI workflow is configured in this repository.
