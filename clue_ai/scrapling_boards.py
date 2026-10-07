from __future__ import annotations

import logging
import re
from dataclasses import asdict
from typing import Any, ClassVar
from urllib.parse import parse_qs, urlsplit

from clue_ai.config import Settings
from clue_ai.crawl_policy import (
    JUSTREMOTE_JOB_PAGE_LIMIT,
    JUSTREMOTE_LISTING_PAGE_LIMIT,
    JUSTREMOTE_PAGE_LIMIT,
    JUSTREMOTE_RESULT_PAGE_LIMIT,
    ROBOTS_TXT_OBEY,
    SCRAPLING_CONCURRENT_REQUESTS,
    SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN,
    SCRAPLING_DOWNLOAD_DELAY_SECONDS,
)
from clue_ai.domain import NormalizedJob
from clue_ai.jobs import canonical_url, plain_text
from clue_ai.sources import (
    FetchOutcome,
    SourceFetchError,
    _extract_jsonld_job_postings,
    _looks_blocked,
    _normalize_crawled_job,
)

_JUSTREMOTE_HOSTS = {"justremote.co", "www.justremote.co"}
_JUSTREMOTE_DETAIL = re.compile(r"^/remote-[a-z0-9-]+-jobs/[^/]+/?$", re.IGNORECASE)
_JUSTREMOTE_CATEGORY = re.compile(r"^/remote-[a-z0-9-]+-jobs/?$", re.IGNORECASE)
def crawl_justremote(
    source: dict[str, Any],
    settings: Settings,
    researched_urls: set[str] | None = None,
) -> FetchOutcome:
    """Crawl public JustRemote listing pages and their linked detail pages with Scrapling."""
    endpoint = str(source.get("endpoint") or "https://justremote.co/remote-jobs")
    parts = urlsplit(endpoint)
    if parts.scheme != "https" or (parts.hostname or "").lower() not in _JUSTREMOTE_HOSTS:
        raise SourceFetchError("JustRemote crawl URL is outside its approved public host.", blocked=True)
    try:
        from scrapling.fetchers import FetcherSession
        from scrapling.spiders import LinkExtractor, Request, Spider
    except ImportError as exc:
        raise SourceFetchError("Scrapling is unavailable. Install the project dependencies.") from exc

    class JustRemoteSpider(Spider):
        name = "clue_ai_justremote_public_board"
        robots_txt_obey = ROBOTS_TXT_OBEY
        allowed_domains: ClassVar[set[str]] = set(_JUSTREMOTE_HOSTS)
        concurrent_requests = SCRAPLING_CONCURRENT_REQUESTS
        concurrent_requests_per_domain = SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN
        download_delay = SCRAPLING_DOWNLOAD_DELAY_SECONDS
        max_blocked_retries = 0
        logging_level = logging.INFO
        start_urls: ClassVar[list[str]] = []
        user_agent = settings.crawler_user_agent

        def __init__(self) -> None:
            super().__init__()
            self.start_urls = [endpoint]
            self.allowed_domains = set(_JUSTREMOTE_HOSTS)
            self.researched_urls = researched_urls or set()
            self.researched_details_skipped = 0
            self.urls_scheduled = {canonical_url(endpoint)}
            self.listing_pages_scheduled = 1
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
            yield Request(
                self.start_urls[0],
                sid=self._session_manager.default_session_id,
                callback=self.parse,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                },
            )

        async def is_blocked(self, response):
            status = int(getattr(response, "status", 0) or 0)
            body = getattr(response, "body", b"")
            if status in {401, 403, 429} or _looks_blocked(body):
                self.hit_block = True
                return True
            return False

        def _schedule(self, response, url: str):
            normalized = canonical_url(url)
            parts = urlsplit(normalized)
            host = (parts.hostname or "").lower()
            if (
                not normalized
                or parts.scheme != "https"
                or host not in _JUSTREMOTE_HOSTS
                or normalized in self.urls_scheduled
                or len(self.urls_scheduled) >= JUSTREMOTE_PAGE_LIMIT
            ):
                return None
            path = parts.path.rstrip("/") or "/"
            if path == "/remote-jobs" or _JUSTREMOTE_CATEGORY.fullmatch(path):
                if self.listing_pages_scheduled >= JUSTREMOTE_LISTING_PAGE_LIMIT:
                    return None
                self.listing_pages_scheduled += 1
            elif _JUSTREMOTE_DETAIL.fullmatch(path):
                if normalized in self.researched_urls:
                    self.researched_details_skipped += 1
                    return None
                if self.job_pages_scheduled >= JUSTREMOTE_JOB_PAGE_LIMIT:
                    return None
                self.job_pages_scheduled += 1
            else:
                return None
            self.urls_scheduled.add(normalized)
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
            response_host = (urlsplit(response_url).hostname or "").lower()
            status = int(getattr(response, "status", 0) or 0)
            body = getattr(response, "body", b"")
            if response_host not in _JUSTREMOTE_HOSTS:
                return
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

            path = urlsplit(response_url).path.rstrip("/") or "/"
            if _JUSTREMOTE_DETAIL.fullmatch(path):
                structured = _extract_jsonld_job_postings(response, source, settings)
                normalized_jobs: list[NormalizedJob] = []
                for item in structured:
                    job = _normalize_crawled_job(source, item, settings)
                    if job:
                        normalized_jobs.append(job)
                if not normalized_jobs:
                    item = _parse_justremote_detail(response, source, settings)
                    if item:
                        job = _normalize_crawled_job(source, item, settings)
                        if job:
                            normalized_jobs.append(job)
                if not normalized_jobs:
                    self.parse_failures += 1
                for job in normalized_jobs:
                    yield asdict(job)
                return

            try:
                links = LinkExtractor(allow_domains=_JUSTREMOTE_HOSTS).extract(response)
            except (AttributeError, TypeError, ValueError):
                links = []
            listing_links: list[str] = []
            job_links: list[str] = []
            for link in links:
                normalized = canonical_url(str(link))
                if not normalized:
                    continue
                parts = urlsplit(normalized)
                if (parts.hostname or "").lower() not in _JUSTREMOTE_HOSTS:
                    continue
                clean_path = parts.path.rstrip("/") or "/"
                if clean_path == "/remote-jobs" or _JUSTREMOTE_CATEGORY.fullmatch(clean_path):
                    page = parse_qs(parts.query).get("page", ["1"])[0]
                    try:
                        if int(page) <= JUSTREMOTE_RESULT_PAGE_LIMIT:
                            listing_links.append(normalized)
                    except ValueError:
                        continue
                elif _JUSTREMOTE_DETAIL.fullmatch(clean_path):
                    job_links.append(normalized)

            # Visit category/result pages first to discover a wider set of role families.
            for target in dict.fromkeys(listing_links):
                request = self._schedule(response, target)
                if request is not None:
                    yield request
            for target in dict.fromkeys(job_links):
                request = self._schedule(response, target)
                if request is not None:
                    yield request

    try:
        spider = JustRemoteSpider()
        result = spider.start()
    except Exception as exc:
        raise SourceFetchError(f"Scrapling JustRemote crawl failed: {type(exc).__name__}.") from exc
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
    checked = int(getattr(stats, "requests_count", 0) or spider.page_count) if stats else spider.page_count
    response_bytes = int(getattr(stats, "response_bytes", 0) or spider.response_bytes) if stats else spider.response_bytes
    if blocked_status or spider.hit_block:
        return FetchOutcome(
            jobs=jobs,
            checked=checked,
            message="JustRemote returned an access block; the source was paused without retry.",
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
            f"Scrapling checked {checked} public pages (200-page ceiling; "
            f"{spider.listing_pages_scheduled} listing pages and "
            f"{spider.job_pages_scheduled} job-detail pages scheduled; "
            f"{spider.researched_details_skipped} previously researched detail URLs not refetched)."
        ),
        response_bytes=response_bytes,
        raw_records=len(jobs) + spider.parse_failures,
        parse_failures=spider.parse_failures,
        not_found_count=spider.not_found_count,
        status_counts=dict(status_counts or {}),
    )


def _parse_justremote_detail(
    response, source: dict[str, Any], settings: Settings
) -> dict[str, Any] | None:
    title = plain_text(response.css("h1::text").get() or "", 300)
    if not title:
        return None
    main_html = response.css("main").get() or response.css("article").get() or ""
    if not main_html:
        return None
    full_text = plain_text(main_html, settings.max_job_description_chars)
    if len(full_text) < 80:
        return None
    company_candidates = response.css("main a[href*='/remote-companies/']::text").getall()
    if not company_candidates:
        company_candidates = response.css("main a::text").getall()
    ignored = {
        "quick apply",
        "apply now",
        "all",
        "workster",
        "discover workster",
        "power search",
        "discover power search",
    }
    company = next(
        (
            plain_text(value, 250)
            for value in company_candidates
            if plain_text(value, 250).casefold() not in ignored
            and len(plain_text(value, 250)) > 1
        ),
        "",
    )
    if not company:
        return None
    restrictions_match = re.search(
        r"Only accepting applications from:\s*(.+?)(?=\s+(?:What we offer|Responsibilities|Requirements|Experience|Salary and Perks|About the Company)\b|$)",
        full_text,
        re.IGNORECASE,
    )
    restrictions = plain_text(restrictions_match.group(1), 2_000) if restrictions_match else ""
    employment_match = re.search(
        r"\b(full[- ]?time|part[- ]?time|contract|freelance|internship|temporary)\b",
        full_text[:1_500],
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
        "applicantLocationRequirements": [{"name": restrictions}] if restrictions else [],
        "jobLocation": {"address": {"addressLocality": "Remote"}},
        "employmentType": employment_match.group(1) if employment_match else "",
        "datePosted": posted,
        "url": str(getattr(response, "url", "")),
        "_response_url": str(getattr(response, "url", "")),
        "_source_id": source["id"],
        "_source_name": source["name"],
    }
