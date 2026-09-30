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
