from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from types import SimpleNamespace
from urllib.parse import parse_qs, urlsplit

import pytest
from conftest import make_job
from scrapling.spiders import Request as ScraplingRequest

from clue_ai import company_sources
from clue_ai.company_sources import crawl_tracked_companies, detect_public_ats, public_ats_api
from clue_ai.crawl_policy import COMPANY_HTML_PAGE_LIMIT, COMPANY_SITEMAP_JOB_PAGE_LIMIT
from clue_ai.domain import SearchCriteria
from clue_ai.repository import list_companies, list_sources
from clue_ai.sources import (
    FetchOutcome,
    SourceFetchError,
    _extract_html_job_posting,
    _normalize_crawled_job,
    fetch_source,
)


@pytest.mark.parametrize(
    ("url", "provider", "board_name", "region"),
    (
        ("https://boards.greenhouse.io/acme", "greenhouse", "acme", None),
        ("https://jobs.lever.co/acme", "lever", "acme", "global"),
        ("https://jobs.eu.lever.co/acme", "lever", "acme", "eu"),
        ("https://jobs.ashbyhq.com/acme", "ashby", "acme", None),
        ("https://careers.smartrecruiters.com/acme", "smartrecruiters", "acme", None),
    ),
)
def test_public_ats_adapter_is_derived_from_the_observed_board_url(
    url, provider, board_name, region
):
    board = detect_public_ats(url)

    assert board["provider"] == provider
    assert board["board_name"] == board_name
    if region:
        assert board["region"] == region
    assert public_ats_api(board)[0] == provider


def test_public_ats_rejects_lookalike_and_non_https_hosts():
    assert detect_public_ats("https://jobs.ashbyhq.com.evil.example/acme") is None
    assert detect_public_ats("http://jobs.ashbyhq.com/acme") is None
    assert detect_public_ats("https://jobs.ashbyhq.com/") is None


def test_redirect_following_stays_https_and_on_the_same_company_host(monkeypatch):
    monkeypatch.setattr(company_sources, "validate_career_url", lambda _url: (True, ""))

    assert (
        company_sources._safe_same_site_redirect("https://www.example.com/careers", "/jobs")
        == "https://www.example.com/jobs"
    )
    assert (
        company_sources._safe_same_site_redirect(
            "https://www.example.com/careers", "https://example.com/jobs"
        )
        == "https://example.com/jobs"
    )
    assert not company_sources._safe_same_site_redirect(
        "https://www.example.com/careers", "https://jobs.evil.com/open"
    )
    assert not company_sources._safe_same_site_redirect(
        "https://www.example.com/careers", "http://www.example.com/open"
    )


def test_scrapling_batch_starts_only_requests_and_carries_observed_board_metadata(
    settings, monkeypatch
):
    monkeypatch.setattr(company_sources, "validate_career_url", lambda _url: (True, ""))
    company = {
        "id": "qdrant",
        "name": "Qdrant",
        "homepage_url": "https://qdrant.tech/",
        "careers_url": "",
        "board_url": "https://jobs.ashbyhq.com/qdrant.tech",
    }
    spider = company_sources._make_company_spider([company], settings, set())
    assert spider.robots_txt_obey is False
    assert spider.concurrent_requests == 8
    assert spider.concurrent_requests_per_domain == 2
    assert spider.download_delay == 1.0
    assert spider.max_blocked_retries == 0

    async def collect_start_requests():
        return [request async for request in spider.start_requests()]

    requests = asyncio.run(collect_start_requests())

    assert requests == []
    assert spider.startup_events[0]["provider"] == "ashby"
    assert spider.startup_events[0]["board_name"] == "qdrant.tech"

    company["board_url"] = ""
    spider = company_sources._make_company_spider([company], settings, set())
    requests = asyncio.run(collect_start_requests())

    assert len(requests) == 1
    assert isinstance(requests[0], ScraplingRequest)
    assert urlsplit(requests[0].url).hostname == "qdrant.tech"
    assert spider.pages_by_company["qdrant"] == 1
    for index in range(1, 5):
        request = spider._request(
            f"https://qdrant.tech/careers/role-{index}", "qdrant", stage="html"
        )
        assert request is not None
    assert spider.pages_by_company["qdrant"] == 5
    for index in range(5, COMPANY_HTML_PAGE_LIMIT):
        request = spider._request(
            f"https://qdrant.tech/careers/role-{index}", "qdrant", stage="html"
        )
        assert request is not None
    assert spider.pages_by_company["qdrant"] == COMPANY_HTML_PAGE_LIMIT
    assert (
        spider._request("https://qdrant.tech/careers/role-over-limit", "qdrant", stage="html")
        is None
    )


def test_scrapling_sitemap_spider_ignores_xml_comments(settings, monkeypatch):
    from lxml import etree
    from scrapling.spiders import Request, SitemapSpider

    monkeypatch.setattr(company_sources, "validate_career_url", lambda _url: (True, ""))
    monkeypatch.setattr(
        SitemapSpider,
        "_dispatch",
        lambda _spider, _response, url, _rules: Request(url),
    )
    spider = company_sources._make_sitemap_spider(
        [
            {
                "id": "test",
                "name": "Test",
                "homepage_url": "https://example.org/",
                "careers_url": "https://example.org/careers",
                "board_url": "",
            }
        ],
        settings,
        set(),
    )

    assert spider._get_type(etree.Comment("sitemap comment")) == ""
    assert spider._get_type(etree.Element("urlset")) == "urlset"
    assert spider.robots_txt_obey is False
    assert spider.concurrent_requests_per_domain == 2
    assert spider.download_delay == 1.0
    assert spider.max_blocked_retries == 0
    response = type(
        "Response",
        (),
        {"meta": {"company_id": "test"}, "url": "https://example.org/sitemap.xml"},
    )()
    for index in range(1, COMPANY_SITEMAP_JOB_PAGE_LIMIT + 1):
        request = spider._dispatch(
            response, f"https://example.org/jobs-{index}.xml", []
        )
        assert request is not None
    assert spider.dispatched["test"] == COMPANY_SITEMAP_JOB_PAGE_LIMIT
    assert (
        spider._dispatch(
            response, "https://example.org/jobs-over-limit.xml", []
        )
        is None
    )
    assert spider._dispatch(response, "https://elsewhere.example/jobs.xml", []) is None


def test_ashby_public_api_keeps_listed_roles_and_full_remote_evidence(settings, monkeypatch):
    payload = (
        b'{"jobs":['
        b'{"title":"Senior ML Engineer","jobUrl":"https://jobs.ashbyhq.com/acme/role-1",'
        b'"isListed":true,"isRemote":true,"workplaceType":"Remote",'
        b'"descriptionPlain":"Build PyTorch systems available to workers in Italy.",'
        b'"location":"Remote - Italy","employmentType":"Full-time"},'
        b'{"title":"Unlisted Role","jobUrl":"https://jobs.ashbyhq.com/acme/role-2",'
        b'"isListed":false,"descriptionPlain":"This role is not publicly listed."}'
        b"]}"
    )
    calls = []

    def fake_fetch(url, allowed_hosts, _settings):
        calls.append((url, allowed_hosts))
        return payload

    monkeypatch.setattr("clue_ai.sources._fetch_bytes", fake_fetch)
    source = {
        "id": "company-acme",
        "name": "Acme",
        "kind": "ashby",
        "endpoint": "https://jobs.ashbyhq.com/acme",
        "state": "approved",
        "enabled": True,
        "attribution": "Acme",
        "config": {"company": "Acme", "board_name": "acme"},
    }

    outcome = fetch_source(source, SearchCriteria(), settings)

    assert len(calls) == 1
    assert calls[0][1] == {"api.ashbyhq.com"}
    assert len(outcome.jobs) == 1
    assert outcome.jobs[0].company == "Acme"
    assert outcome.jobs[0].title == "Senior ML Engineer"
    assert outcome.jobs[0].workplace_type == "remote"
    assert "Italy" in outcome.jobs[0].location_raw
    assert outcome.jobs[0].canonical_url == "https://jobs.ashbyhq.com/acme/role-1"
    assert outcome.raw_records == 1


def test_plain_company_career_detail_fallback_keeps_content_and_canonical_url(settings):
    class Selector:
        def __init__(self, value="", values=None):
            self.value = value
            self.values = values or ([value] if value else [])

        def get(self):
            return self.value

        def getall(self):
            return self.values

    class Response:
        url = "https://www.aindo.com/careers/jobs/senior-data-engineer"

        def css(self, selector):
            values = {
                "h1::text": "Senior Data Engineer | Aindo",
                "title::text": "",
                "[itemprop='jobLocation']::text": "Italy / Remote",
                ".job-location::text": "",
                ".location::text": "",
                "[data-testid*='location']::text": "",
                "article": (
                    "<article><h2>Responsibilities</h2><p>Build reliable data pipelines "
                    "for clinical machine learning products, improve quality checks, "
                    "and partner with researchers and product engineers across Italy.</p>"
                    "<p>Use Python, SQL, cloud data tools, and production monitoring.</p></article>"
                ),
                "main": "",
                "time[datetime]::attr(datetime)": "2026-09-30T10:00:00Z",
                "meta[property='article:published_time']::attr(content)": "",
                "meta[name='date']::attr(content)": "",
            }
            return Selector(values.get(selector, ""))

    source = {
        "id": "company-aindo",
        "name": "Aindo",
        "attribution": "Aindo",
        "config": {"company": "Aindo"},
    }
    item = _extract_html_job_posting(Response(), source, settings)

    assert item is not None
    job = _normalize_crawled_job(source, item, settings)
    assert job is not None
    assert job.title == "Senior Data Engineer"
    assert job.company == "Aindo"
    assert job.location_raw == "Italy / Remote"
    assert "clinical machine learning products" in job.description
    assert job.source_url == Response.url
    assert job.canonical_url == Response.url
    assert job.posted_at == "2026-09-30T10:00:00+00:00"


def test_smartrecruiters_connector_walks_public_pages_with_a_fixed_cap(settings, monkeypatch):
    calls = []

    def record(index):
        return {
            "id": f"job-{index}",
            "name": f"Data Engineer {index}",
            "ref": f"https://careers.smartrecruiters.com/acme/{index}",
            "jobAd": {"sections": {"jobDescription": {"text": "Python data platform role."}}},
            "location": {"city": "Milan", "region": "Lombardy", "country": "Italy"},
        }

    def fake_fetch(url, _hosts, _settings):
        calls.append(url)
        offset = int(parse_qs(urlsplit(url).query)["offset"][0])
        records = [record(i) for i in range(100)] if offset == 0 else [record(100)]
        return json.dumps({"content": records, "totalFound": 101}).encode()

    monkeypatch.setattr("clue_ai.sources._fetch_bytes", fake_fetch)
    monkeypatch.setattr("clue_ai.sources.time.sleep", lambda _seconds: None)
    source = {
        "id": "company-acme",
        "name": "Acme",
        "kind": "smartrecruiters",
        "endpoint": "https://careers.smartrecruiters.com/acme",
        "state": "approved",
        "enabled": True,
        "attribution": "Acme",
        "config": {"company": "Acme", "company_id": "acme"},
    }

    outcome = fetch_source(source, SearchCriteria(), settings)

    assert len(calls) == 2
    assert [parse_qs(urlsplit(url).query)["offset"][0] for url in calls] == ["0", "100"]
    assert len(outcome.jobs) == 101
    assert outcome.raw_records == 101


def test_company_batch_pauses_only_blocked_ats_host_and_streams_other_jobs(
    database, settings, monkeypatch
):
    by_id = {company["id"]: company for company in list_companies(database)}
    selected = [by_id[company_id] for company_id in ("qdrant", "deepset", "aindo")]
    boards = {
        "qdrant": {
            "board_url": "https://jobs.ashbyhq.com/qdrant",
            "provider": "ashby",
            "board_name": "qdrant",
        },
        "deepset": {
            "board_url": "https://jobs.ashbyhq.com/deepset",
            "provider": "ashby",
            "board_name": "deepset",
        },
        "aindo": {
            "board_url": "https://boards.greenhouse.io/aindo",
            "provider": "greenhouse",
            "board_name": "aindo",
        },
    }
    monkeypatch.setattr(company_sources, "companies_due", lambda *_args, **_kwargs: selected)
    monkeypatch.setattr(
        company_sources,
        "_make_company_spider",
        lambda *_args: SimpleNamespace(reviewed_details_skipped=0),
    )
    monkeypatch.setattr(
        company_sources,
        "_make_sitemap_spider",
        lambda *_args: pytest.fail("No sitemap fallback needed"),
    )
    monkeypatch.setattr(
        company_sources,
        "_run_spider_stream",
        lambda spider, callback: [
            callback(
                {
                    "_clue_event": "board",
                    "company_id": company_id,
                    **board,
                }
            )
            for company_id, board in boards.items()
        ],
    )
    api_calls = []

    def fake_fetch(source, *_args):
        api_calls.append(source["id"])
        if source["id"] == "company-qdrant":
            raise SourceFetchError("HTTP 429", status_code=429, blocked=True)
        job = replace(make_job(source_id=source["id"]), company=source["name"])
        return FetchOutcome(jobs=[job], checked=1, raw_records=1)

    monkeypatch.setattr(company_sources, "fetch_source", fake_fetch)
    saved = []

    report = crawl_tracked_companies(
        database,
        settings,
        save_jobs=lambda jobs: saved.extend(jobs) or len(jobs),
    )

    assert api_calls == ["company-qdrant", "company-aindo"]
    assert report.companies_checked == 3
    assert report.boards_resolved == 3
    assert report.blocked == 2
    assert report.jobs_indexed == 1
    assert saved[0].source_id == "company-aindo"
    states = {company["id"]: company for company in list_companies(database)}
    assert states["qdrant"]["board_state"] == "blocked"
    assert states["deepset"]["board_state"] == "blocked"
    assert states["aindo"]["listing_count"] == 1
    assert not any(source["kind"] == "company_board" for source in list_sources(database))
