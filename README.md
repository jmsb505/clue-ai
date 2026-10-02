# Clue AI — Personal Job Search

A local, single-user job-discovery and review app. Upload a CV to parse it locally, search free feeds and approved public career pages, filter jobs against your criteria, and automatically ask TypeSafe Jev for fit signals when you enable it. Clue never applies for you.

The first search defaults to remote work from Italy, but you can choose another location per search. CV, parsed profile, preferences, indexed listings, and results stay in `.data/` on this device. Jev scoring requires a one-time opt-in, a configured key, supported English text, and available app-side budget; otherwise, listings remain visible and unscored.

## Run locally

Requirements: Python 3.10 or newer and the existing Conda `gen` environment. Run from the project folder:

```powershell
conda run -n gen python -m pip install -e ".[dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
.\scripts\clue.ps1 start
```

Then open http://127.0.0.1:8000. The server binds to this computer only and stays in the foreground; press Ctrl+C in that PowerShell window when you finish. A fresh copy of `.env.example` starts with a blank key; the app works without one. This local checkout's ignored `.env` is owner-configured and is never committed.

Use the same PowerShell window, or another one, to manage the local server:

```powershell
.\scripts\clue.ps1 status
.\scripts\clue.ps1 stop
.\scripts\clue.ps1 restart
```

The helper always runs against Conda `gen`. `stop` and `restart` close a Python server from that environment if it occupies port 8000. They refuse to stop a non-Python process or a process launched from another environment. Stopping the server does not delete the profile or `.data/` files. The app is not installed as a background service and does not start automatically.

To enable Jev, add your key to `.env` and restart Clue. Read the data disclosure in Settings; Clue does not inspect TypeSafe account terms, billing/refill settings, or other uses of the key. Automatic scoring requires your one-time in-app opt-in and runs after searches while the app-side key, language, and budget gates pass. The app reserves at most USD 4 over 30 days toward your USD 5 owner ceiling; that local limit does not guarantee account-wide charges.

## What is wired

- Local PDF/DOCX parsing, saved editable profile, immediate CV-first search, and repeat searches using the saved profile.
- Jobicy, RemoteJobs.org, Remote OK, role-specific Remote First Jobs RSS, and Startup Jobs RSS. RemoteJobs.org listings display the requested “Powered by RemoteJobs.org” credit.
- Owner-added Greenhouse, Lever, SmartRecruiters, and Scrapling careers connectors. Supported public HTTPS sources are enabled after host validation and can be paused or removed.
- Broad Scrapling crawl of public careers pages: robots.txt exclusions ignored, eight global requests, two per host, one-second base delay, 25 company pages, 10 child sitemaps, 50 sitemap job pages, and 20 dynamic pages per company batch. Standalone career pages allow 100 same-host pages; JustRemote allows 200 pages per six-hour refresh.
- Frequently updated feeds refresh hourly; publisher-daily APIs stay daily. Company pages and JustRemote refresh every six hours. Failed sources can retry after five minutes.
- Profile-matched directory of 80+ Italian, European, AI/data-platform, and global technology employers, with local search-set controls. Automatic multi-company board refresh from this list is tracked in [PLAN-006](docs/plans/PLAN-006-profile-aware-company-board-discovery.md).
- Location and sponsorship evidence, deduplication, freshness labels, search coverage, results, saved/hidden jobs, source controls, and local deletion.
- Automatic Jev batches after searches when enabled, with retries disabled, contact redaction, English-language gating, and a persistent usage ledger.
- Manual X.com search links and owner-reviewed job leads. Clue does not scrape X, call its API, or open/resolve pasted links; see [the X lead decision](docs/decisions/0007-x-manual-lead-discovery.md).

The initial feeds do not cover the whole internet. Open the original listing and verify it is still available and the employer can hire where you live.

Clue does not stop crawling solely because a public page is excluded by `robots.txt`. It does stop a host after an explicit access denial, rate limit, or anti-bot challenge. It does not use login-only content, CAPTCHA solving, proxy rotation, or browser impersonation. See the [current crawl decision](docs/decisions/0009-broader-local-public-crawling.md).

## Local setup

The `.env` file, `.data/`, CV uploads, databases, and development caches are ignored by Git. Do not commit your key, CV, or `.data/` folder. Deletion cannot remove data already processed by TypeSafe. PLAN-002 M1/M2 and PLAN-001 M3a used synthetic candidate data only. M3a scored five synthetic listings in one Jev request; Jev and a simple keyword baseline both achieved `nDCG@5 = 1.0` on assistant-authored grades. This validates the scoring/evaluation path, not personal relevance or Jev superiority. Its methodology, result, and cost limitations are recorded in [the M3a evaluation](docs/evaluations/PLAN-001-M3-synthetic-jev.md). PLAN-001 M2 separately fetched one public Lever API and job page into process memory for parser comparison; no source listing was persisted to `.data/`.

A synthetic backup/restore check confirms that the local profile and CV can be restored from a copy of `.data/`. Backups are manual and local; encryption is optional under the owner's scope decision. Backups do not include `.env`; see the [backup and deletion guide](docs/operations/local-data-backup-and-deletion.md).

## Project documents

- [Product definition](docs/product-definition.md)
- [Definition gate](docs/readiness/definition-gate.md)
- [Market and reference review](docs/research/market-and-reference-review.md)
- [Source discovery and Scrapling review](docs/research/source-discovery-and-crawl-review.md)
- [Profile-aware company-board research](docs/research/profile-aware-company-board-discovery.md)
- [Company-board discovery implementation plan](docs/plans/PLAN-006-profile-aware-company-board-discovery.md)
- [Company-board discovery decision](docs/decisions/0008-profile-aware-company-board-discovery.md)
- [Architecture overview](docs/architecture/overview.md)
- [Roadmap](docs/roadmap.md)
- [Detailed implementation plan](docs/plans/PLAN-001-free-local-source-discovery.md)
- [Synthetic Jev benchmark](docs/evaluations/PLAN-001-M3-synthetic-jev.md)
- [Local backup and deletion guide](docs/operations/local-data-backup-and-deletion.md)
- [Local app implementation plan](docs/plans/PLAN-002-local-first-job-search-app.md)
- [UI/UX implementation review](docs/research/ui-ux-implementation-review.md)
- [CV-first workflow plan](docs/plans/PLAN-004-cv-first-automated-search.md)
- [CV-first workflow decision](docs/decisions/0008-cv-first-automatic-search.md)
