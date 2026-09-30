from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from clue_ai.external_links import (
    build_x_search_url,
    normalize_public_job_url,
    normalize_x_status_url,
)


def test_x_status_url_accepts_only_https_status_permalinks():
    assert normalize_x_status_url("https://twitter.com/Hiring/status/123?ref=post#top") == (
        "https://x.com/Hiring/status/123",
        "123",
    )
    assert normalize_x_status_url("https://x.com/i/web/status/456/") == (
        "https://x.com/i/web/status/456",
        "456",
    )
    for value in (
        "http://x.com/hiring/status/123",
        "https://x.com.evil.example/hiring/status/123",
        "https://x.com/home",
        "https://user@x.com/hiring/status/123",
        "https://x.com:8443/hiring/status/123",
    ):
        assert normalize_x_status_url(value) is None


@pytest.mark.parametrize(
    "value",
    (
        "http://jobs.example.com/123",
        "https://user:pass@jobs.example.com/123",
        "https://t.co/short",
        "https://careers.local/jobs/123",
        "https://127.0.0.1/jobs/123",
        "https://x.com/hiring/status/123",
        "https://careers.x.com/openings/123",
        "https://jobs.example.com:8443/123",
    ),
)
def test_job_url_requires_https_public_direct_host(value):
    assert normalize_public_job_url(value) is None


def test_job_url_returns_canonical_link_and_display_host():
    assert normalize_public_job_url(
        "https://careers.example.com/jobs/123?utm_source=x&gh_jid=123"
    ) == ("https://careers.example.com/jobs/123?gh_jid=123", "careers.example.com")


def test_x_search_query_uses_selected_terms_and_no_user_supplied_url():
    url = build_x_search_url("Product Designer, UX Designer", "Milan, Italy", "remote")
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)["q"][0]

    assert parsed.scheme == "https"
    assert parsed.netloc == "x.com"
    assert '"Product Designer" OR "UX Designer"' in query
    assert '"Milan" OR "Italy" OR "Europe" OR "EU" OR "worldwide"' in query
    assert '"hiring" OR "job opening" OR "apply"' in query
    assert query.endswith("remote")
    assert build_x_search_url("", "Italy") == ""
