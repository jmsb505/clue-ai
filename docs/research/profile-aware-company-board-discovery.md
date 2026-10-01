# Profile-aware company board discovery

**Reviewed:** 2026-10-01  
**User focus:** AI/ML engineering, applied AI, data analysis/engineering, and product-facing AI roles; jobs the owner can perform while based in Milan, Italy.  
**Product:** Local, single-user Clue app. CV/profile stay local; job descriptions and selected profile fields go to Jev only under the existing consent and budget controls. No automatic applications.

## Executive finding

Clue already uses Scrapling, but its use is much narrower than the requested search. `crawl_career_page()` starts from one URL already entered into the source registry, allows one host, and follows at most 25 links that match a small `/careers|jobs|positions|vacancies|openings/...` pattern. It does not find companies, discover their career pages, follow an official link to a separate ATS host, consult a job sitemap, or crawl a broad set of boards as a batch. `run_search()` only fetches approved registry entries that are due. This is why the current app can search a few remote-job feeds but cannot yet “look under every rock” in the owner's field.

The right search shape is **discover companies by field → resolve each company's official careers/ATS board → fetch published listings → filter Italy eligibility → ask Jev to rank evidence-backed fits**. A directory of companies is a seed catalog, not a vacancy feed. The employer or its ATS remains the source of each vacancy.

The most useful discovery seeds for this profile are:

1. **Sifted AI 100** for a broad, Europe-wide set of AI-native companies. Its 2025 ranking covers 100 companies in 32 European countries and includes models, enterprise AI, developer infrastructure, robotics, biotech, and applied vertical AI. It is a company discovery list, not a job listing source. [Sifted AI 100](https://sifted.eu/rankings/ai-100-2025)
2. **AIxIA Italian AI Ecosystem** for Italian companies developing or heavily using AI. AIxIA describes its map as a survey of participating companies, updated regularly; it is useful to seed and expand an Italian employer list, but the current published maps are not a complete machine-readable company/career-board feed. [AIxIA map](https://aixia.it/en/ricerca/ecosistema-ai-italiano/)
3. **Politecnico di Milano's AI Observatory** for breadth beyond AI-native startups. Its 2025 research reports 1,010 Italian companies offering AI solutions/services and 135 funded AI startups. It reports a 93% year-over-year increase in Italian job ads requiring AI skills and AI skills in 76% of highly qualified white-collar postings. That supports searching across finance, healthcare, manufacturing, telecom, consulting, and public/industrial technology employers as well as AI labs. [Osservatori Digital Innovation](https://www.osservatori.net/comunicato/artificial-intelligence/intelligenza-artificiale-italia/)

The initial in-app catalog should contain an intentionally broad seed set, not imply that every company has an opening or can hire in Italy. It should show which company board has been found and checked. On each actual job, location eligibility must come from the posting itself; company headquarters and generic “remote” labels are not enough.

## Candidate and market mapping

The saved profile fields point to a wider role family than “machine learning engineer” alone. The useful company/role search families are:

| Search family | Example titles and work | Profile evidence to match |
|---|---|---|
| AI/ML engineering | ML Engineer, AI Engineer, Machine Learning Engineer, NLP/LLM Engineer, Applied Scientist | Python, PyTorch, TensorFlow, scikit-learn, Hugging Face, CUDA, quantization |
| Applied/LLM systems | Applied AI Engineer, LLM Engineer, AI Product Engineer, RAG Engineer, Agent Engineer | RAG, embeddings, LangGraph/LangChain, evaluation, APIs, product delivery |
| Data and analytics | Data Analyst, Product/Data Analyst, Analytics Engineer, Data Scientist | SQL, Python, Pandas, NumPy, statistics, business/product communication |
| Data/ML platforms | Data Engineer, ML Platform Engineer, MLOps Engineer, AI Infrastructure Engineer | Python, SQL, PostgreSQL, Docker, Linux, CI, APIs, model serving, optimization |
| Technical product implementation | Forward Deployed Engineer, Solutions Engineer, AI Implementation Engineer | Python/API fluency, customer problem-solving, product/business translation |

These are **search families**, not five user-defined titles that the app should hard-filter to. The company catalog and keyword expansion should use the owner's saved roles and skills, then Jev should assess a particular vacancy from its full description. The employer-directory match itself is a transparent local seed ranking, not a JEV score and not a claim of job fit.

### Broad company seed set

Names below are investigation seeds from company ecosystems and product/technology segments. They are not claims of current vacancies, remote eligibility, or endorsement. Company status and board URLs change, so the app should retain `candidate`, `board found`, `checked`, `paused`, and `unavailable` states with dates.

**Italian AI-native and AI-product companies:** Domyn (formerly iGenius), Aindo, Expert.ai, Almawave, Datrix, Akamas, Axyon AI, AIKO, Aptus.AI, Babelscape, Clearbox AI, Indigo.ai, Latitudo 40, Next Vision, QuestIT, Intuendi, Tuidi, BigProfiles, and other companies in the AIxIA/Italian AI landscape.

**Italian employers with substantial AI/data work:** Bending Spoons, Reply/Data Reply, NTT DATA Italia, Engineering Ingegneria Informatica, Accenture Italia, Capgemini Italia, Deloitte Italia, Leonardo, STMicroelectronics, TIM Enterprise, Eni, Intesa Sanpaolo, Satispay, Banca Sella, D-Orbit, and major healthcare/manufacturing/financial employers. Use current job descriptions to establish whether a particular team and role match; do not include an employer simply because it uses the word “AI.”

**European AI products and model companies:** Mistral AI, DeepL, Hugging Face, Aleph Alpha, Cohere, Black Forest Labs, Multiverse Computing, CuspAI, PhysicsX, NEURA Robotics, Cradle, PolyAI, Encord, Nabla, FlexAI, H Company, Basecamp Research, Photoroom, Tandem Health, Bioptimus, LightOn, Axelera AI, Sereact, Synthesia, ElevenLabs, Poolside, and selected other Sifted AI 100 companies.

**Data/ML infrastructure and developer tools:** Qdrant, deepset/Haystack, Weaviate, Langfuse, Dataiku, Databricks, Snowflake, MongoDB, Elastic, Confluent, Grafana Labs, dbt Labs, Prefect, Dagster, and relevant cloud/compute organizations. Keep these in the same catalog because strong applied AI roles often sit in data platforms, observability, deployment, inference, and developer tooling rather than a company branded as an AI lab.

**Global employers with Italy or Europe hiring:** Google/DeepMind, Microsoft, NVIDIA, Amazon/AWS, Meta, IBM, Adobe, Salesforce, Oracle, SAP, ServiceNow, and other cloud, chip, enterprise software, and industrial research employers. A global employer is only a candidate seed. Each role must say whether Italy is an eligible work location.

The initial curated catalog should start with the strongest Italian/European role-family matches and then expand from Sifted's broader AI cohort, AIxIA, and the Italian AI Observatory. The catalog should be maintainable as plain local data; it must not depend on a paid corporate database or a subscription.

### Career-board paths confirmed during research

These official links show that companies do publish vacancies on their own sites or public ATS-hosted boards. They are concrete seed examples for the catalog; their current jobs and role locations need refresh on every search.

| Employer | Official careers/board URL | Board path observed | Why it belongs in the seed set |
|---|---|---|---|
| Mistral AI | [Careers](https://mistral.ai/careers/) | Ashby-hosted listings | Frontier models, applied AI, science, and product engineering. The live examples include region-specific roles, including a North America-only remote vacancy; remote must be location-filtered. |
| DeepL | [Careers](https://www.deepl.com/en/careers) | Ashby-hosted listings | Language AI, ML product, data and platform roles; the company careers page links directly to its open-role board. |
| Domyn | [Open roles](https://www.domyn.com/careers/roles) | Employer-hosted careers page | Current role feed includes an AI Research Engineer in Italy and platform/AI roles. Its careers page states some work-from-anywhere-within-Italy flexibility; the condition applies to role/team details, not every vacancy. |
| Aindo | [Careers](https://www.aindo.com/careers/) | Employer-hosted careers page | Italian generative-AI/synthetic-data company. Current page shows a hybrid role in Trieste or Milan and marks all areas “remote-friendly”; a vacancy's own terms still control. |
| Akamas | [Careers](https://careers.akamas.io/) | Teamtailor-hosted board | Current page lists a fully remote Solutions Engineer in Milan alongside a hybrid Milan role. This is an example of strong location/workplace evidence on a company board. |
| Axyon AI | [Careers](https://axyon.ai/careers) | Employer-hosted page with opportunities | Italian AI/ML company with explicit AI/ML, engineering, data engineering/MLOps, NLP/LLM, and quantitative role families. |
| Expert.ai | [Careers](https://www.expert.ai/careers/) | Employer-hosted page | Italian language-AI company; official careers page invites technical, software, and computational-linguistics candidates. |
| Almawave | [Join us](https://www.almawave.com/join-us/) | Employer-hosted page | Italian AI/NLP company with an R&D workforce and hybrid-work information. |
| Axelera AI | [Careers](https://axelera.ai/careers) | Employer-hosted role list | AI inference/hardware company with current engineering roles, including Europe/UK remote/hybrid scope and an on-site Florence internship; role-level location remains necessary. |
| Multiverse Computing | [Official board](https://multiversecomputing.teamtailor.com/) | Teamtailor-hosted board | European AI/model-compression company; board lists ML engineering, platform, and data-adjacent openings with concrete Spanish/European locations. |
| deepset | [Official board](https://deepset.jobs.personio.com/) | Personio-hosted board | Applied NLP/LLM platform company. Personio's XML vacancy feed is a potential structured connector. |
| Qdrant | [Ashby board](https://jobs.ashbyhq.com/qdrant.tech) | Ashby-hosted listings | Vector-search/RAG/AI infrastructure. A live EMEA remote role cited Europe and work-hour requirements, while its selectable locations were narrower than “all Europe”; do not infer Italy eligibility from the label. |
| Dataiku | [Careers](https://www.dataiku.com/company/careers) | Official careers page / job system links | Enterprise data and AI, engineering, analytics, and customer implementation roles across European offices. |
| Cohere Technology | [SmartRecruiters board](https://careers.smartrecruiters.com/CohereTechnology) | SmartRecruiters-hosted board | Enterprise language AI; add only after confirming this board belongs to the intended Cohere entity and current listings. |
| Bending Spoons | [Careers](https://www.jobs.bendingspoons.com/) | Employer-hosted job board | Milan-based software/product company; broader data and product engineering search, not assumed to be AI-native. |

The research viewer returned currently live examples on several of these boards on 2026-10-01. They are illustrative source observations, not a personalized ranked result list; no CV was sent to a website or Jev during this research.

## Listing-source inventory

The existing five free remote-job feeds should stay as broad catchers. They are not a substitute for employer boards: they miss companies, can have thin descriptions, and may not encode work-country rules.

| Source family | Best use | Coverage gap / next action |
|---|---|---|
| Current remote feeds: Jobicy, RemoteJobs.org, Remote OK, Remote First Jobs, Startup Jobs | Broad remote leads, fast discovery, and cross-company recall | Keep source credits and limits already documented. Use employer page/ATS as canonical and verify remote-from-Italy on the job. |
| Greenhouse Job Board API | Per-company published jobs and full descriptions from a documented public GET API; `content=true` includes descriptions/offices/departments; no auth is required for GET | Board token is company-specific. Discover it from the official careers link, not guessed tokens. [Official docs](https://docs.greenhouse.io/job-board.html) |
| Lever Postings API | Public published jobs, descriptions, categories, workplace type, optional salary; global and EU hosts | Company-specific site slug; no cross-company full-text search. Use the official link to identify slug and correct region. [Official docs](https://github.com/lever/postings-api) |
| Ashby lightweight public job-posting API | Published jobs with HTML/plain descriptions, workplace, remote flag, `isListed`, location and job links | Slug comes from its official hosted board URL. Use this public job-board route, not the authenticated admin endpoint. [Official docs](https://developers.ashbyhq.com/docs/public-job-posting-api) |
| SmartRecruiters Posting API | Active postings and job details for a company, with query/location support | Official authentication docs list Posting API under “No authentication”; its overview also discusses API keys/OAuth for customer integrations. Use only the public unauthenticated endpoint and never send or request employer credentials. [Authentication](https://developers.smartrecruiters.com/docs/authentication), [endpoints](https://developers.smartrecruiters.com/docs/endpoints) |
| Personio public company careers XML | Structured current jobs and descriptions from `{company}.jobs.personio.de/xml` | Company-specific hostname and some docs disagree about whether an `X-Company-ID` header is needed. Validate the documented public feed per board; do not use a customer's authenticated recruiting API. [Official feed docs](https://developer.personio.de/v1.0/reference/get_xml) |
| Employer career page + JobPosting JSON-LD | Best fallback and canonical direct employer evidence; parse full description, location, remote geography, dates, salary, and canonical link | Many pages expose jobs via a different ATS hostname or JavaScript. Discover that route through the official career link; don't stop at the root careers landing page. Google's schema guidance explains job-location requirements and expiration; it is a schema reference, not a permission grant. [JobPosting documentation](https://developers.google.com/search/docs/appearance/structured-data/job-posting) |
| Sitemaps, RSS/Atom, and XML feeds | Broad URL discovery, efficient change detection, and structured postings | Must be found from the official domain's `robots.txt`, sitemap references, page metadata, or employer-linked source, then parsed without following unrelated site pages. |
| Workday and other employer-specific career systems | Important coverage for large Italian employers and enterprises | No universal public cross-company API was verified. Use the employer's public career page, sitemap, and structured data; save a site-specific adapter only when repeat traffic justifies it. |
| LinkedIn, login-only boards, and paid aggregators | Not an initial connector under this local $0 source-cost requirement | No logged-in browser scraping, hidden endpoints, paid feeds, or API quota purchase. Use an employer's official source when a post is discovered elsewhere. |

The 2025 Sifted list, AIxIA, and Italian AI market study should supply company candidates. They should not be mistaken for reusable job feeds. A discovery list contains company names and official websites; Clue must resolve an official careers link and then search the actual board.

## Scrapling capability plan

Scrapling should become the crawler engine for the **company discovery and career-page path**, not a one-off fallback. Current official Scrapling documentation describes ordinary static fetching, async Spider crawls, request sessions, per-domain scheduling, robots handling, link extractors, sitemap crawling, streamed results, pause/resume, dynamic rendering, and adaptive selectors. Use capabilities where they address a measured board pattern:

1. **Seed and resolve:** Start from the curated company catalog and official employer site. Use Scrapling to discover the linked career page and linked ATS board, then persist the canonical provider URL/slug locally. Do not invent ATS tokens or crawl unrelated site areas.
2. **Provider-first ingestion:** Use the documented public Greenhouse, Lever, Ashby, SmartRecruiters, and Personio public listing endpoints when the official career page identifies them. This obtains complete job text with fewer HTML requests. Keep job-link URLs on the original employer/ATS host.
3. **Career-site crawling:** Use `SitemapSpider` or sitemap discovery for job URLs, then a `Spider` plus `LinkExtractor` rules scoped to the official careers and job paths. Include ATS host only when the company's own careers page links there. Parse listing-level JSON-LD and fetch job-detail pages where full text is absent.
4. **Selector resilience:** Prefer structured data and provider responses. Add adaptive CSS selectors only for recurring employer templates where a stable normal selector breaks; persist the learned selector per domain and keep a deterministic fallback. Adaptive parsing must never turn arbitrary page text into a job without title, employer, description, and canonical job URL evidence.
5. **Selective browser rendering:** Try static HTTP first. Use Scrapling's ordinary dynamic fetcher only when the public page demonstrably renders the vacancy list with JavaScript and no structured/feed route exists. Do not use stealth fetchers, proxy rotation, impersonation, CAPTCHA solving, or antibot bypass.
6. **Bounded throughput:** Batch many separate employer domains in one async crawl rather than running one Spider per company serially. Keep the existing global concurrency 4, one per domain, two-second base delay, robots handling, ordinary identifying User-Agent, response-size/page-depth caps, and zero retries around explicit blocks. Use source freshness and conditional request/cache mechanisms where the target supports them.
7. **Incremental recovery:** Stream parsed jobs into the local upsert path so a long multi-board crawl can report progress and recover useful records when one board fails. Keep per-domain outcomes, request counts, status counts, parse failures, duplicates, and last-checked time visible in search history.
8. **Location and trust filtering:** Extract `applicantLocationRequirements`, `jobLocationType`, country, location, remote regions, and exact location text before Jev. A remote role open to North America only must be excluded from an Italy-eligible set even if its title/skills fit. Crawl only public pages; on explicit access denial, challenge, rate limit, or block, stop that connector and mark it unavailable for that run.

The source safety behavior should be operational and quiet: public official pages and public feeds are the normal search path; the user should not have to complete a five-checkbox legal review for every company. If a connector's published rules or response makes the planned fetch unsuitable, the software should mark that source unavailable and continue with other companies. This is not a product-wide approval gate and should not dominate the search UI.

## Product behavior target

The local app should have a **Companies** page, built around the Jobbie-style approachable workflow already chosen for Clue:

- Profile-matched company groups with an obvious “AI/ML”, “Data & ML platform”, “Italian AI & tech”, and “Europe AI startups” filter.
- Searchable/sortable company rows/cards with role-family tags, official careers link, detected ATS type, board URL, remote/Italy evidence source when known, last check, number of current listings, and crawl state.
- Company-board catalog seeded with an initial verified set and expandable through ecosystem directory research; candidates never imply current openings.
- No need for the owner to find or type ATS slugs. Clue resolves slugs/board URLs from official careers links and records provenance.
- The CV-first action searches profile-relevant tracked company boards plus the existing remote sources automatically. Search page shows real per-source progress and coverage, then applies deterministic eligibility filters and Jev scoring.
- Company-site lead discovery should be broad enough to produce more than a handful of aggregator matches, while per-job location eligibility and date freshness prevent irrelevant “remote” results from crowding the list.
- “Open original posting” remains the user's action. Clue does not apply.

## Coverage measurements

The crawler's progress should be measurable; “scoured the web” is not a testable claim. Report, by search run and by source family:

- employer seeds considered, official boards resolved, boards visited, and sources skipped/blocked;
- requests, response bytes, HTTP status counts, raw jobs, parsed jobs, duplicate merges, parser failures, and job details fetched;
- unique employers and listings checked; listings with full descriptions;
- explicit Italy-eligible, Europe/EEA-eligible, remote-with-region-unknown, location-unknown, and ineligible listing counts;
- posted-date age, last-check age, stale/expired counts, and source family;
- run elapsed time and cache hits.

For owner relevance feedback, save the owner's keep/hide decisions locally and use them to calibrate the deterministic prefilter and test set. Keep Jev score, evidence, and confidence visible and avoid calling the score a hiring probability.

## Decision and scope

Build an in-app company-board catalog from broad public ecosystem sources, then use Scrapling and official ATS endpoints to find live company vacancies. The first target is Italy/Milan and Italy-eligible remote work; Europe-wide jobs are candidates only when the role explicitly accepts an Italy-based worker. Existing remote-job feeds remain supplemental. There is no paid search feed or crawling service. Jev remains the only recurring paid service.

This extends the initial source plan. It does not claim complete web coverage and does not begin a full crawl of unrelated domains at every page load. Search should use profile-matched, locally cataloged official company sources and incremental refresh, with transparent source coverage.
