from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import Any, ClassVar
from urllib.parse import urljoin, urlsplit

from clue_ai.config import Settings
from clue_ai.crawl_policy import (
    ROBOTS_TXT_OBEY,
    SCRAPLING_CONCURRENT_REQUESTS,
    SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN,
    SCRAPLING_DOWNLOAD_DELAY_SECONDS,
    TECHEUROPE_PAGE_LIMIT,
)
from clue_ai.domain import NormalizedJob
from clue_ai.jobs import canonical_url, parse_date, plain_text
from clue_ai.sources import (
    FetchOutcome,
    SourceFetchError,
    _extract_jsonld_job_postings,
    _looks_blocked,
    _normalize_crawled_job,
)

_HOST = "jobs.techeurope.io"
_HOSTS = {_HOST}
_JOB_DETAIL = re.compile(r"^/jobs/[^/?#]+/?$", re.IGNORECASE)
_LISTING_PATHS = {"/", "/ops"}
_DATE_HINT = re.compile(
    r"\b(?:today|yesterday|\d+\s+(?:hours?|days?|weeks?|months?)\s+ago|"
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2})\b",
    re.IGNORECASE,
)


def crawl_techeurope(source: dict[str, Any], settings: Settings) -> FetchOutcome:
    """Read Tech Europe's public role indexes and their directly linked details."""
    endpoint = str(source.get("endpoint") or f"https://{_HOST}/")
    parts = urlsplit(endpoint)
    if parts.scheme != "https" or (parts.hostname or "").lower() != _HOST:
        raise SourceFetchError(
            "Tech Europe crawl URL is outside its approved public host.", blocked=True
        )
    try:
        from scrapling.fetchers import FetcherSession
        from scrapling.spiders import LinkExtractor, Request, Spider
    except ImportError as exc:
        raise SourceFetchError("Scrapling is unavailable. Install the project dependencies.") from exc

    listing_urls = [canonical_url(endpoint), canonical_url(urljoin(endpoint, "/ops"))]

    class TechEuropeSpider(Spider):
        name = "clue_ai_techeurope_public_jobs"
        robots_txt_obey = ROBOTS_TXT_OBEY
        allowed_domains: ClassVar[set[str]] = set(_HOSTS)
        concurrent_requests = SCRAPLING_CONCURRENT_REQUESTS
        concurrent_requests_per_domain = SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN
        download_delay = SCRAPLING_DOWNLOAD_DELAY_SECONDS
        max_blocked_retries = 0
        logging_level = logging.INFO
        start_urls: ClassVar[list[str]] = []
        user_agent = settings.crawler_user_agent

        def __init__(self) -> None:
            super().__init__()
            self.start_urls = listing_urls
            self.allowed_domains = set(_HOSTS)
            self.urls_scheduled = set(listing_urls)
            self.job_pages_scheduled = 0
            self.hit_block = False
            self.page_count = 0
            self.response_bytes = 0
            self.parse_failures = 0
            self.not_found_count = 0

        def configure_sessions(self, manager) -> None:
            manager.add(
                "ordinary",
                FetcherSession(
                    impersonate=None,
                    stealthy_headers=False,
                    timeout=settings.network_timeout_seconds,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                    retries=0,
                    retry_delay=0,
                    follow_redirects=False,
                    verify=True,
                ),
            )

        async def start_requests(self):
            for url in self.start_urls:
                yield Request(
                    url,
                    sid=self._session_manager.default_session_id,
                    callback=self.parse,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml",
                    },
                )

        async def is_blocked(self, response):
            status = int(getattr(response, "status", 0) or 0)
            if status in {401, 403, 429} or _looks_blocked(getattr(response, "body", b"")):
                self.hit_block = True
                return True
            return False

        def _schedule_detail(self, response, url: str):
            normalized = canonical_url(url)
            target = urlsplit(normalized)
            if (
                not normalized
                or target.scheme != "https"
                or (target.hostname or "").lower() not in _HOSTS
                or not _JOB_DETAIL.fullmatch(target.path)
                or normalized in self.urls_scheduled
                or len(self.urls_scheduled) >= TECHEUROPE_PAGE_LIMIT
            ):
                return None
            self.urls_scheduled.add(normalized)
            self.job_pages_scheduled += 1
            return response.follow(
                normalized,
                callback=self.parse,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                },
            )

        async def parse(self, response):
            response_url = str(getattr(response, "url", ""))
            current = urlsplit(response_url)
            if current.scheme != "https" or (current.hostname or "").lower() not in _HOSTS:
                return
            status = int(getattr(response, "status", 0) or 0)
            body = getattr(response, "body", b"")
            if status in {401, 403, 429} or _looks_blocked(body):
                self.hit_block = True
                return
            if status == 404:
                self.not_found_count += 1
                return
            if status < 200 or status >= 300:
                return
            if len(body) > settings.max_page_bytes:
                self.parse_failures += 1
                return

            self.page_count += 1
            self.response_bytes += len(body)
            path = current.path.rstrip("/") or "/"
            if _JOB_DETAIL.fullmatch(path):
                postings = _extract_jsonld_job_postings(response, source, settings)
                jobs: list[NormalizedJob] = []
                for item in postings:
                    # Keep the source-board detail URL as the user-facing listing link.
                    item["url"] = response_url
                    job = _normalize_crawled_job(source, item, settings)
                    if job:
                        jobs.append(job)
                if not jobs:
                    item = _parse_techeurope_detail(response, source, settings)
                    if item:
                        job = _normalize_crawled_job(source, item, settings)
                        if job:
                            jobs.append(job)
                if not jobs:
                    self.parse_failures += 1
                for job in jobs:
                    yield asdict(job)
                return

            # Only the two public directory views may discover job pages. Detail
            # pages can show related jobs, but following them would walk beyond the
            # directory's newsletter-gated result set.
            if path not in _LISTING_PATHS:
                return
            try:
                links = LinkExtractor(allow_domains=_HOSTS).extract(response)
            except (AttributeError, TypeError, ValueError):
                links = []
            for link in dict.fromkeys(str(link) for link in links):
                request = self._schedule_detail(response, link)
                if request is not None:
                    yield request

    try:
        spider = TechEuropeSpider()
        result = spider.start()
    except Exception as exc:
        raise SourceFetchError(f"Scrapling Tech Europe crawl failed: {type(exc).__name__}.") from exc

    stats = getattr(result, "stats", None)
    status_counts = getattr(stats, "response_status_count", {}) if stats else {}
    blocked_status = any(
        key in status_counts for key in ("status_401", "status_403", "status_429")
    )
    jobs: list[NormalizedJob] = []
    for item in getattr(result, "items", []):
        if isinstance(item, NormalizedJob):
            jobs.append(item)
        elif isinstance(item, dict):
            try:
                jobs.append(NormalizedJob(**item))
            except TypeError:
                continue
    checked = (
        int(getattr(stats, "requests_count", 0) or spider.page_count)
        if stats
        else spider.page_count
    )
    response_bytes = (
        int(getattr(stats, "response_bytes", 0) or spider.response_bytes)
        if stats
        else spider.response_bytes
    )
    if blocked_status or spider.hit_block:
        return FetchOutcome(
            jobs=jobs,
            checked=checked,
            message="Tech Europe returned an access block; the source was paused without retry.",
            blocked=True,
            response_bytes=response_bytes,
            raw_records=len(jobs),
            parse_failures=spider.parse_failures,
            not_found_count=spider.not_found_count,
            status_counts=dict(status_counts or {}),
        )
    return FetchOutcome(
        jobs=jobs,
        checked=checked,
        message=(
            f"Scrapling checked {checked} public pages (60-page ceiling; "
            f"{spider.job_pages_scheduled} linked job-detail pages scheduled)."
        ),
        response_bytes=response_bytes,
        raw_records=len(jobs) + spider.parse_failures,
        parse_failures=spider.parse_failures,
        not_found_count=spider.not_found_count,
        status_counts=dict(status_counts or {}),
    )


def _parse_techeurope_detail(
    response, source: dict[str, Any], settings: Settings
) -> dict[str, Any] | None:
    main_html = response.css("main").get() or response.css("article").get()
    if not main_html:
        return None
    content = plain_text(main_html, settings.max_job_description_chars)
    if len(content) < 80:
        return None

    title = plain_text(
        response.css("main h3::text").get()
        or response.css("h3::text").get()
        or response.css("h1::text").get()
        or response.css("title::text").get()
        or "",
        300,
    )
    page_title = plain_text(response.css("h1::text").get() or "", 500)
    if not title:
        return None
    title = re.sub(
        r"\s+at\s+.+?\s+\|\s+Jobs by\s+.+$", "", title, flags=re.IGNORECASE
    ).strip()

    company_candidates = response.css('main a[href*="/companies/"]::text').getall()
    company = next(
        (plain_text(value, 250) for value in company_candidates if plain_text(value, 250)),
        "",
    )
    if not company:
        match = re.search(r"\bat\s+(.+?)\s*\|\s*Jobs by\b", page_title, re.IGNORECASE)
        company = plain_text(match.group(1), 250) if match else ""
    if not company:
        return None

    location = ""
    for selector in (
        "[itemprop='jobLocation']::text",
        ".job-location::text",
        "[class*='location']::text",
        "[data-testid*='location']::text",
    ):
        location = plain_text(" ".join(response.css(selector).getall()), 1_000)
        if location:
            break
    if not location:
        for value in response.css("main p::text").getall():
            line = plain_text(value, 500)
            if _DATE_HINT.search(line):
                location = re.split(r"\s[-–—]\s", line, maxsplit=1)[0].strip()
                if location:
                    break

    employment = re.search(
        r"\b(internship|intern|full[- ]?time|part[- ]?time|contract|freelance|temporary)\b",
        content[:2_000],
        re.IGNORECASE,
    )
    posted = (
        response.css("time[datetime]::attr(datetime)").get()
        or response.css("meta[property='article:published_time']::attr(content)").get()
        or ""
    )
    return {
        "title": title,
        "hiringOrganization": {"name": company},
        "description": main_html,
        "jobLocation": {"address": {"addressLocality": location}} if location else {},
        "employmentType": employment.group(1) if employment else "",
        "datePosted": parse_date(posted) if posted else "",
        "url": str(getattr(response, "url", "")),
        "_response_url": str(getattr(response, "url", "")),
        "_source_id": source["id"],
        "_source_name": source["name"],
    }
