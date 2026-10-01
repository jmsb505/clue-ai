from __future__ import annotations

import json
import socket
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import make_job

from clue_ai.domain import SearchCriteria
from clue_ai.repository import get_source
from clue_ai.sources import (
    FetchOutcome,
    SourceFetchError,
    _allowed_hosts,
    _connector_url,
    _looks_blocked,
    _normalize_crawled_job,
    _parse_json_feed,
    _parse_rss_feed,
    _url_is_allowed,
    fetch_source,
    validate_career_url,
)


def test_jobicy_feed_normalizes_source_credit_original_url_and_eligibility_text(
    settings, database, monkeypatch
):
    payload = json.dumps(
        {
            "jobs": [
                {
                    "id": 12,
                    "jobTitle": "Software Engineer",
                    "companyName": "Example Labs",
                    "jobDescription": "<p>Work remotely from Italy with Python.</p><script>discard()</script>",
                    "jobGeo": "Italy",
                    "url": "https://jobs.example.org/software?utm_source=feed",
                    "pubDate": "2026-09-29T12:00:00Z",
                    "jobType": "Full-time",
                }
            ]
        }
    ).encode()
    monkeypatch.setattr("clue_ai.sources._fetch_bytes", lambda *args: payload)
    source = get_source(database, "jobicy")

    outcome = fetch_source(source, SearchCriteria(), settings, database)

    assert outcome.checked == 1
    assert len(outcome.jobs) == 1
    job = outcome.jobs[0]
    assert job.canonical_url == "https://jobs.example.org/software"
    assert job.source_credit == "Jobicy"
    assert "discard" not in job.description
    assert job.workplace_type == "remote"
    assert job.posted_at.startswith("2026-09-29")
    assert outcome.response_bytes == len(payload)
    assert outcome.raw_records == 1
    assert outcome.parse_failures == 0


def test_rss_parser_keeps_direct_link_and_credit(settings, database):
    source = get_source(database, "startupjobs")
    payload = b"""<rss><channel><item>
      <title>Remote Software Engineer</title>
      <link>https://jobs.example.org/openings/1?utm_source=rss</link>
      <description>Remote role available in Europe with Python and SQL.</description>
      <company>Example Labs</company><guid>posting-1</guid>
    </item></channel></rss>"""

    jobs = _parse_rss_feed(source, payload, settings)

    assert len(jobs) == 1
    assert jobs[0].source_url == "https://jobs.example.org/openings/1"
    assert jobs[0].source_credit == "Startup Jobs"
    assert jobs[0].company == "Example Labs"


def test_we_work_remotely_rss_splits_company_and_role_title(settings, database):
    source = get_source(database, "weworkremotely")
    payload = b"""<rss><channel><item>
      <title>Example AI: Senior Machine Learning Engineer</title>
      <link>https://weworkremotely.com/remote-jobs/example-ai-senior-ml-engineer</link>
      <description>Remote role available worldwide. Build Python and PyTorch services.</description>
      <pubDate>Tue, 29 Sep 2026 12:00:00 GMT</pubDate>
    </item></channel></rss>"""

    jobs = _parse_rss_feed(source, payload, settings)

    assert len(jobs) == 1
    assert jobs[0].title == "Senior Machine Learning Engineer"
    assert jobs[0].company == "Example AI"
    assert jobs[0].workplace_type == "remote"
    assert jobs[0].source_credit == "We Work Remotely"


def test_manual_board_sources_are_never_fetched(settings, database):
    source = get_source(database, "wellfound_manual")

    outcome = fetch_source(source, SearchCriteria(), settings, database)

    assert outcome.skipped
    assert "never fetched" in outcome.message


def test_remotive_public_api_keeps_company_country_salary_and_tags(settings, database, monkeypatch):
    payload = json.dumps(
        {
            "jobs": [
                {
                    "id": 42,
                    "title": "Senior Data Engineer",
                    "company_name": "Example Analytics",
                    "candidate_required_location": "Europe",
                    "description": "Build production Python and SQL data pipelines.",
                    "url": "https://remotive.com/remote-jobs/data/senior-data-engineer-42",
                    "publication_date": "2026-09-29T12:00:00",
                    "job_type": "full_time",
                    "salary": "€70k - €90k per year",
                    "category": "Data and Analytics",
                    "tags": ["Python", "SQL"],
                }
            ],
            "job-count": 1,
        }
    ).encode()
    monkeypatch.setattr("clue_ai.sources._fetch_bytes", lambda *_args: payload)
    source = get_source(database, "remotive")

    outcome = fetch_source(source, SearchCriteria(), settings, database)

    assert outcome.raw_records == 1
    assert len(outcome.jobs) == 1
    job = outcome.jobs[0]
    assert job.company == "Example Analytics"
    assert job.title == "Senior Data Engineer"
    assert job.location_raw == "Europe"
    assert job.workplace_type == "remote"
    assert job.salary_min == 70_000
    assert job.salary_max == 90_000
    assert job.salary_currency == "EUR"
    assert job.salary_period == "annual"
    assert "Tags: Python, SQL" in job.description
    assert job.source_credit == "Remotive"


def test_himalayas_api_searches_role_and_country_and_normalizes_location_expiry_salary(
    settings, database, monkeypatch
):
    pages = {
        "1": {
            "jobs": [
                {
                    "guid": "himalayas-1",
                    "title": "ML Platform Engineer",
                    "companyName": "Example AI",
                    "locationRestrictions": [{"alpha2": "IT", "name": "Italy"}],
                    "description": "Build ML infrastructure with Python and Kubernetes.",
                    "applicationLink": "https://himalayas.app/jobs/ml-platform-engineer",
                    "pubDate": 1790792682,
                    "expiryDate": 1793384682,
                    "employmentType": "Full Time",
                    "minSalary": 60_000,
                    "maxSalary": 80_000,
                    "currency": "EUR",
                    "salaryPeriod": "annual",
                    "categories": ["Engineering", "Machine Learning"],
                }
            ],
            "totalCount": 21,
        },
        "2": {
            "jobs": [
                {
                    "guid": "himalayas-2",
                    "title": "Data Analyst",
                    "companyName": "Example Data",
                    "locationRestrictions": [],
                    "description": "Analyze product data with SQL.",
                    "applicationLink": "https://himalayas.app/jobs/data-analyst",
                    "pubDate": 1790792682,
                }
            ],
            "totalCount": 21,
        },
    }
    calls = []

    def fake_fetch(url, *_args):
        calls.append(url)
        page = parse_qs(urlsplit(url).query).get("page", ["1"])[0]
        return json.dumps(pages[page]).encode()

    monkeypatch.setattr("clue_ai.sources._fetch_bytes", fake_fetch)
    monkeypatch.setattr("clue_ai.sources.time.sleep", lambda _seconds: None)
    source = get_source(database, "himalayas")

    outcome = fetch_source(
        source,
        SearchCriteria(roles="Machine Learning Engineer", work_from="Milan, Italy"),
        settings,
        database,
    )

    assert outcome.checked == 2
    assert len(calls) == 2
    assert [parse_qs(urlsplit(url).query)["page"] for url in calls] == [["1"], ["2"]]
    assert all(urlsplit(url).path == "/jobs/api/search" for url in calls)
    assert all(parse_qs(urlsplit(url).query)["q"] == ["Machine Learning Engineer"] for url in calls)
    assert all(parse_qs(urlsplit(url).query)["country"] == ["Italy"] for url in calls)
    assert len(outcome.jobs) == 2
    job = outcome.jobs[0]
    assert job.company == "Example AI"
    assert job.location_raw == "Italy"
    assert job.salary_min == 60_000
    assert job.salary_max == 80_000
    assert job.salary_period == "annual"
    assert job.valid_through
    assert "Machine Learning" in job.description
    assert outcome.jobs[1].location_raw == "Worldwide"


def test_himalayas_api_stops_at_daily_page_budget(settings, database, monkeypatch):
    calls = []

    def fake_fetch(url, *_args):
        calls.append(url)
        page = parse_qs(urlsplit(url).query).get("page", ["1"])[0]
        return json.dumps({"jobs": [{}] * 20, "page": int(page), "totalCount": 1000}).encode()

    monkeypatch.setattr("clue_ai.sources._fetch_bytes", fake_fetch)
    monkeypatch.setattr("clue_ai.sources.time.sleep", lambda _seconds: None)
    source = get_source(database, "himalayas")

    from clue_ai.sources import _fetch_himalayas

    outcome = _fetch_himalayas(source, SearchCriteria(roles="Data Engineer"), settings)

    assert outcome.checked == 25
    assert len(calls) == 25
    assert "25-page daily cap" in outcome.message


def test_himalayas_rate_limit_keeps_completed_search_pages(settings, database, monkeypatch):
    calls = []

    def fake_fetch(url, *_args):
        calls.append(url)
        page = parse_qs(urlsplit(url).query).get("page", ["1"])[0]
        if page == "2":
            from clue_ai.sources import SourceFetchError

            raise SourceFetchError("rate limited", status_code=429, blocked=True)
        return json.dumps(
            {
                "jobs": [
                    {
                        "guid": "himalayas-partial",
                        "title": "Data Engineer",
                        "companyName": "Example",
                        "applicationLink": "https://himalayas.app/jobs/data-engineer",
                    }
                ],
                "totalCount": 21,
            }
        ).encode()

    monkeypatch.setattr("clue_ai.sources._fetch_bytes", fake_fetch)
    monkeypatch.setattr("clue_ai.sources.time.sleep", lambda _seconds: None)
    source = get_source(database, "himalayas")

    outcome = fetch_source(source, SearchCriteria(roles="Data Engineer"), settings, database)

    assert outcome.blocked is True
    assert outcome.checked == 2
    assert len(outcome.jobs) == 1
    assert outcome.status_counts == {"status_200": 1, "status_429": 1}


def test_working_nomads_public_api_normalizes_country_and_tags(settings, database):
    source = get_source(database, "workingnomads")
    raw = [
        {
            "url": "https://www.workingnomads.com/job/go/12345/",
            "title": "AI Research Engineer",
            "description": "Build evaluation pipelines for language models.",
            "company_name": "Example Research",
            "category_name": "Engineering",
            "tags": "Python, LLM, evaluation",
            "location": "Italy",
            "pub_date": "2026-09-29T10:30:00-04:00",
        }
    ]

    jobs = _parse_json_feed("workingnomads_api", source, raw, settings)

    assert len(jobs) == 1
    assert jobs[0].company == "Example Research"
    assert jobs[0].location_raw == "Italy"
    assert jobs[0].workplace_type == "remote"
    assert "Tags: Python, LLM, evaluation" in jobs[0].description
    assert jobs[0].source_url == "https://www.workingnomads.com/job/go/12345/"


def test_justremote_detail_parser_preserves_country_restrictions(settings, database):
    from clue_ai.scrapling_boards import _parse_justremote_detail

    class Selector:
        def __init__(self, value="", values=None):
            self.value = value
            self.values = values or ([value] if value else [])

        def get(self):
            return self.value

        def getall(self):
            return self.values

    class Response:
        url = "https://justremote.co/remote-developer-jobs/ml-engineer-example-123"

        def css(self, selector):
            values = {
                "h1::text": "Machine Learning Engineer",
                "main": (
                    "<main><a href='/remote-companies/example-ai'>Example AI</a>"
                    "<p>Fully Remote</p><p>Only accepting applications from: Italy</p>"
                    "<h2>Responsibilities</h2><p>Build Python machine learning services and "
                    "work with a distributed product engineering team.</p></main>"
                ),
                "article": "",
                "main a[href*='/remote-companies/']::text": "Example AI",
                "main a::text": "Example AI",
                "time[datetime]::attr(datetime)": "",
                "meta[property='article:published_time']::attr(content)": "",
            }
            return Selector(values.get(selector, ""))

    source = get_source(database, "justremote")
    item = _parse_justremote_detail(Response(), source, settings)

    assert item is not None
    normalized = _normalize_crawled_job(source, item, settings)
    assert normalized is not None
    assert normalized.company == "Example AI"
    assert set(normalized.location_raw.replace(";", ",").split(", ")) == {"Italy", "Remote"}
    assert normalized.workplace_type == "remote"
    assert normalized.source_url == Response.url


def test_justremote_spider_is_robot_aware_and_stays_within_daily_page_caps(
    settings, database, monkeypatch
):
    from scrapling.spiders import Spider

    captured = {}

    def no_network_start(spider):
        captured["spider"] = spider
        captured["robots"] = spider.robots_txt_obey
        captured["concurrent"] = spider.concurrent_requests
        captured["per_domain"] = spider.concurrent_requests_per_domain
        captured["delay"] = spider.download_delay
        captured["retries"] = spider.max_blocked_retries
        return SimpleNamespace(
            stats=SimpleNamespace(response_status_count={}, requests_count=1), items=[]
        )

    monkeypatch.setattr(Spider, "start", no_network_start)
    outcome = fetch_source(
        get_source(database, "justremote"),
        SearchCriteria(roles="AI Engineer", work_from="Italy"),
        settings,
        database,
    )

    spider = captured["spider"]
    assert outcome.checked == 1
    assert captured["robots"] is True
    assert captured["concurrent"] == 4
    assert captured["per_domain"] == 1
    assert captured["delay"] == 2.0
    assert captured["retries"] == 0
    assert spider.start_urls == ["https://justremote.co/remote-jobs"]
    assert spider.listing_pages_scheduled == 1
    assert spider.job_pages_scheduled == 0

    class Response:
        def follow(self, url, **_kwargs):
            return url

    response = Response()
    listing = spider._schedule(response, "https://justremote.co/remote-ai-engineer-jobs?page=2")
    external = spider._schedule(response, "https://jobs.example.org/role/1")
    assert listing == "https://justremote.co/remote-ai-engineer-jobs?page=2"
    assert external is None
    assert spider.listing_pages_scheduled == 2
    assert spider.job_pages_scheduled == 0

    for index in range(1, 70):
        spider._schedule(response, f"https://justremote.co/remote-ml-engineer-{index}-jobs")
    assert spider.listing_pages_scheduled <= 24
    assert len(spider.urls_scheduled) <= 60


def test_remotejobs_api_normalizes_direct_link_and_refreshes_up_to_four_roles(
    settings, database, monkeypatch
):
    payload = json.dumps(
        {
            "data": [
                {
                    "id": "remotejobs-1",
                    "title": "Senior Data Engineer",
                    "company": {"name": "Example Labs"},
                    "location": "Remote (Worldwide)",
                    "description": "Remote data engineering role open to candidates anywhere in the world.",
                    "url": "https://remotejobs.org/remote-jobs/senior-data-engineer-example",
                    "apply_url": "https://remotejobs.org/remote-jobs/senior-data-engineer-example",
                    "salary_min": 120000,
                    "salary_max": 160000,
                    "salary_text": "USD 120,000 - USD 160,000",
                    "type": "Full-time",
                    "posted_at": "2026-09-29T12:00:00Z",
                }
            ],
            "pagination": {"total": 1, "limit": 50, "offset": 0, "has_more": False},
        }
    ).encode()
    calls = []

    def fake_fetch(url, *_args):
        calls.append(url)
        return payload

    monkeypatch.setattr("clue_ai.sources._fetch_bytes", fake_fetch)
    monkeypatch.setattr("clue_ai.sources.time.sleep", lambda _seconds: None)
    source = get_source(database, "remotejobs")
    criteria = SearchCriteria(
        roles="Data Engineer, Product Manager, Data Engineer; C++ Engineer, UX Researcher"
    )

    outcome = fetch_source(source, criteria, settings, database)

    assert outcome.checked == 4
    assert len(calls) == 4
    assert [parse_qs(urlsplit(url).query)["q"][0] for url in calls] == [
        "Data Engineer", "Product Manager", "C++ Engineer", "UX Researcher"
    ]
    assert all(urlsplit(url).hostname == "remotejobs.org" for url in calls)
    assert all(parse_qs(urlsplit(url).query)["limit"] == ["50"] for url in calls)
    assert len(outcome.jobs) == 4
    job = outcome.jobs[0]
    assert job.source_id == "remotejobs"
    assert job.company == "Example Labs"
    assert job.location_raw == "Remote (Worldwide)"
    assert job.canonical_url == "https://remotejobs.org/remote-jobs/senior-data-engineer-example"
    assert job.source_credit == "Powered by RemoteJobs.org"
    assert job.salary_min == 120000
    assert job.salary_currency == "USD"
    assert job.posted_at.startswith("2026-09-29")

    repeated = fetch_source(source, criteria, settings, database)
    assert repeated.skipped
    assert len(calls) == 4

    new_role = fetch_source(
        source, SearchCriteria(roles="Platform Engineer"), settings, database
    )
    assert new_role.checked == 1
    assert len(calls) == 5
    assert parse_qs(urlsplit(calls[-1]).query)["q"] == ["Platform Engineer"]


def test_review_source_is_skipped_without_fetching(settings, monkeypatch):
    called = False

    def unexpected_fetch(*args):
        nonlocal called
        called = True
        raise AssertionError("Review sources must not be fetched")

    monkeypatch.setattr("clue_ai.sources._fetch_bytes", unexpected_fetch)
    outcome = fetch_source(
        {"id": "review", "name": "Review", "kind": "jobicy_api", "state": "review", "enabled": 0},
        SearchCriteria(),
        settings,
    )

    assert outcome.skipped
    assert not called


def test_source_endpoint_host_is_allowlisted_before_any_fetch(settings, monkeypatch):
    monkeypatch.setattr(
        "clue_ai.sources._fetch_bytes",
        lambda *args: pytest.fail("Unexpected request to a non-source host"),
    )
    with pytest.raises(SourceFetchError, match="outside its registered host"):
        fetch_source(
            {
                "id": "jobicy",
                "name": "Jobicy",
                "kind": "jobicy_api",
                "endpoint": "https://attacker.example/api",
                "state": "approved",
                "enabled": 1,
            },
            SearchCriteria(),
            settings,
        )


def test_denied_and_challenge_signals_are_detected_without_evasion():
    assert _looks_blocked(b"<html>Access denied - verify you are human</html>")
    assert not _looks_blocked(b"<rss><channel><title>Remote roles</title></channel></rss>")
    assert not _looks_blocked(b"<script src='/static/recaptcha-application-form.js'></script>")
    assert _looks_blocked(b"<div>Please complete the captcha to continue.</div>")
    assert _url_is_allowed("https://jobicy.com/api/v2/jobs", {"jobicy.com"})
    assert not _url_is_allowed("http://jobicy.com/api/v2/jobs", {"jobicy.com"})


def test_lever_region_selects_its_documented_public_api_host():
    source = {"config": {"site": "prima", "region": "eu"}}
    assert _connector_url({"kind": "lever", **source}) == (
        "https://api.eu.lever.co/v0/postings/prima?mode=json"
    )
    assert _allowed_hosts(source, "lever", "https://api.eu.lever.co/v0/postings/prima") == {
        "api.eu.lever.co"
    }

    global_source = {"config": {"site": "example"}}
    assert _connector_url({"kind": "lever", **global_source}) == (
        "https://api.lever.co/v0/postings/example?mode=json"
    )
    assert _allowed_hosts(global_source, "lever", "https://api.lever.co/v0/postings/example") == {
        "api.lever.co"
    }

    with pytest.raises(SourceFetchError, match="supported Lever site region"):
        _connector_url({"kind": "lever", "config": {"site": "example", "region": "other"}})


def test_career_url_rejects_private_dns_and_accepts_public_dns(monkeypatch):
    def dns_result(ip):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443))]

    monkeypatch.setattr(
        "clue_ai.sources.socket.getaddrinfo", lambda *args, **kwargs: dns_result("127.0.0.1")
    )
    assert validate_career_url("https://careers.example.org/jobs")[0] is False

    monkeypatch.setattr(
        "clue_ai.sources.socket.getaddrinfo", lambda *args, **kwargs: dns_result("93.184.216.34")
    )
    assert validate_career_url("https://careers.example.org/jobs") == (True, "")
    assert validate_career_url("http://careers.example.org/jobs")[0] is False


@pytest.mark.parametrize(
    "url",
    (
        "https://x.com/search?q=jobs",
        "https://www.x.com/jobs",
        "https://api.x.com/2/tweets/search/recent",
        "https://help.twitter.com/en/rules",
        "https://t.co/short",
    ),
)
def test_scrapling_source_rejects_x_hosts_before_dns_lookup(monkeypatch, url):
    monkeypatch.setattr(
        "clue_ai.sources.socket.getaddrinfo",
        lambda *_args, **_kwargs: pytest.fail("X domains must not be resolved by Clue"),
    )

    valid, message = validate_career_url(url)

    assert valid is False
    assert "manual-only" in message


def test_scrapling_spider_uses_robots_and_bounded_ordinary_crawl(
    settings, monkeypatch
):
    from scrapling.spiders import Spider

    seen = {}

    def no_network_start(spider):
        seen.update(
            robots=spider.robots_txt_obey,
            concurrent=spider.concurrent_requests,
            per_domain=spider.concurrent_requests_per_domain,
            delay=spider.download_delay,
            retries=spider.max_blocked_retries,
            logging_level=spider.logging_level,
            host=spider.allowed_domains,
            url=spider.start_urls,
        )
        return SimpleNamespace(
            stats=SimpleNamespace(response_status_count={}, requests_count=1), items=[]
        )

    monkeypatch.setattr(Spider, "start", no_network_start)
    monkeypatch.setattr("clue_ai.sources.validate_career_url", lambda _url: (True, ""))
    source = {
        "id": "reviewed-careers",
        "name": "Example Careers",
        "kind": "scrapling",
        "endpoint": "https://careers.example.org/jobs",
        "config": {"career_url": "https://careers.example.org/jobs"},
        "state": "approved",
        "enabled": 1,
    }

    outcome = fetch_source(source, SearchCriteria(), settings)

    assert isinstance(outcome, FetchOutcome)
    assert outcome.checked == 1
    assert seen == {
        "robots": True,
        "concurrent": 4,
        "per_domain": 1,
        "delay": 2.0,
        "retries": 0,
        "logging_level": 20,
        "host": {"careers.example.org"},
        "url": ["https://careers.example.org/jobs"],
    }


def test_scrapling_marks_blocked_status_without_followup_request(
    settings, monkeypatch
):
    from scrapling.spiders import Spider

    monkeypatch.setattr("clue_ai.sources.validate_career_url", lambda _url: (True, ""))
    monkeypatch.setattr(
        Spider,
        "start",
        lambda _spider: SimpleNamespace(
            stats=SimpleNamespace(response_status_count={"status_403": 1}, requests_count=1),
            items=[],
        ),
    )
    outcome = fetch_source(
        {
            "id": "careers",
            "name": "Careers",
            "kind": "scrapling",
            "endpoint": "https://careers.example.org/jobs",
            "config": {"career_url": "https://careers.example.org/jobs"},
            "state": "approved",
            "enabled": 1,
        },
        SearchCriteria(),
        settings,
    )

    assert outcome.blocked


def test_scrapling_reports_404_and_response_metrics(settings, monkeypatch):
    from scrapling.spiders import Spider

    monkeypatch.setattr("clue_ai.sources.validate_career_url", lambda _url: (True, ""))
    monkeypatch.setattr(
        Spider,
        "start",
        lambda _spider: SimpleNamespace(
            stats=SimpleNamespace(
                response_status_count={"status_404": 1},
                requests_count=1,
                response_bytes=246,
            ),
            items=[],
        ),
    )
    outcome = fetch_source(
        {
            "id": "careers",
            "name": "Careers",
            "kind": "scrapling",
            "endpoint": "https://careers.example.org/jobs/example",
            "config": {"career_url": "https://careers.example.org/jobs/example"},
            "state": "approved",
            "enabled": 1,
        },
        SearchCriteria(),
        settings,
    )

    assert outcome.not_found_count == 1
    assert outcome.response_bytes == 246
    assert outcome.status_counts == {"status_404": 1}


def test_fresh_fixture_job_helper_has_direct_source_links():
    assert make_job().source_url.startswith("https://")
