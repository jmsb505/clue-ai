# Clue AI — Personal Job Search

A local, single-user job-discovery and review app. Search free feeds and approved public career pages, filter jobs against your criteria, and optionally ask TypeSafe Jev for fit signals. Clue never applies for you.

The first search defaults to remote work explicitly eligible from Italy, but you can choose another location per search. CV, profile, preferences, indexed listings, and results stay in .data/ on this device. Without a TypeSafe key, listings remain visible and unscored.

## Run locally

Requirements: Python 3.10 or newer. In PowerShell, activate the existing Conda `gen` environment, then run from the project folder:

```powershell
conda activate gen
python -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python -m clue_ai
```

Then open http://127.0.0.1:8000. The server binds to this computer only. A fresh copy of `.env.example` starts with a blank key; the app works without one. This local checkout's ignored `.env` is owner-configured and is never committed.

To enable Jev later, add your key to .env and restart Clue. Review TypeSafe's terms and the disclosure in Settings first. Scoring happens only after you explicitly choose Score with Jev. The app reserves at most USD 4 over 30 days, leaving USD 1 as a buffer inside the USD 5 owner ceiling. Keep TypeSafe auto-refills off; the app cannot limit other uses of the same key.

## What is wired

- Local PDF/DOCX extraction and editable profile review.
- Jobicy, RemoteJobs.org, Remote OK, role-specific Remote First Jobs RSS, and Startup Jobs RSS. RemoteJobs.org listings display the requested “Powered by RemoteJobs.org” credit.
- Owner-added Greenhouse, Lever, SmartRecruiters, and Scrapling careers connectors. They start disabled in Review.
- Location and sponsorship evidence, deduplication, freshness labels, search coverage, results, saved/hidden jobs, source controls, and local deletion.
- Optional Jev batches with retries disabled, contact redaction, English-language gating, and a persistent usage ledger.

The initial feeds do not cover the whole internet. Open the original listing and verify it is still available and the employer can hire where you live.

## Local setup

The `.env` file, `.data/`, CV uploads, databases, and development caches are ignored by Git. Do not commit your key, CV, or `.data/` folder. Deletion cannot remove data already processed by TypeSafe. M1 automated validation used local fixtures and a mocked Jev client. M2 then made one separately authorized live request with synthetic profile and job facts only: Jev 1.13.0 returned rubric `fit-v1.1.0`, used 1,574 input tokens, and the local ledger estimated `$0.00006611`. No real CV or live job-source data was sent.

## Project documents

- [Product definition](docs/product-definition.md)
- [Definition gate](docs/readiness/definition-gate.md)
- [Market and reference review](docs/research/market-and-reference-review.md)
- [Source discovery and Scrapling review](docs/research/source-discovery-and-crawl-review.md)
- [Architecture overview](docs/architecture/overview.md)
- [Roadmap](docs/roadmap.md)
- [Detailed implementation plan](docs/plans/PLAN-001-free-local-source-discovery.md)
- [Local app implementation plan](docs/plans/PLAN-002-local-first-job-search-app.md)
- [UI/UX implementation review](docs/research/ui-ux-implementation-review.md)
