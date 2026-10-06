"""Small public-page crawler tools reserved exclusively for the Researcher stage."""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any, ClassVar
from urllib.parse import urljoin, urlsplit

from clue_ai.config import Settings
from clue_ai.crawl_policy import (
    ROBOTS_TXT_OBEY,
    SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN,
    SCRAPLING_DOWNLOAD_DELAY_SECONDS,
)
from clue_ai.domain import utc_now
from clue_ai.external_links import normalize_public_job_url
from clue_ai.jobs import plain_text
from clue_ai.sources import _looks_blocked

RESEARCH_PAGE_LIMIT = 4
RESEARCH_CHAR_LIMIT = 12_000


class ResearchCrawlError(ValueError):
    pass


class BoundedResearchCrawler:
    def __init__(
        self,
        settings: Settings,
        allowed_urls: list[str],
    ):
        self.settings = settings
        self.allowed_urls = set()
        self.allowed_hosts = set()
        self.seed_hosts = set()
        self.linked_external_urls = set()
        self.link_candidates = set()
        for value in allowed_urls:
            validated = normalize_public_job_url(value)
            if validated:
                url, host = validated
                self.allowed_urls.add(url)
                self.allowed_hosts.add(host)
                self.seed_hosts.add(host)
        self.link_candidates.update(self.allowed_urls)
        self.pages: dict[str, dict[str, Any]] = {}

    def crawl(self, url: str, research_question: str) -> dict[str, Any]:
        validated = normalize_public_job_url(url)
        if not validated:
            raise ResearchCrawlError("Use a direct public HTTPS page URL.")
        normalized, host = validated
        if normalized not in self.link_candidates or (
            host not in self.allowed_hosts and normalized not in self.linked_external_urls
        ):
            raise ResearchCrawlError(
                "That URL was not supplied or linked by an allowed public source page."
            )
        if normalized in self.pages:
            return self.pages[normalized]
        if len(self.pages) >= RESEARCH_PAGE_LIMIT:
            raise ResearchCrawlError("The four-page research limit for this listing was reached.")
        _require_public_resolution(host)
        page = _scrapling_fetch(normalized, host, self.settings)
        self.pages[normalized] = page
        if host not in self.allowed_hosts:
            self.allowed_hosts.add(host)
        for item in page["links"]:
            linked_url = item["url"]
            linked_host = urlsplit(linked_url).hostname
            if linked_host == host:
                self.link_candidates.add(linked_url)
            elif host in self.seed_hosts:
                self.link_candidates.add(linked_url)
                self.linked_external_urls.add(linked_url)
        return {**page, "research_question": str(research_question or "")[:240]}


def _scrapling_fetch(url: str, host: str, settings: Settings) -> dict[str, Any]:
    try:
        from scrapling.fetchers import FetcherSession
        from scrapling.spiders import Request, Spider
    except ImportError as exc:
        raise ResearchCrawlError("Scrapling is unavailable in this installation.") from exc

    class PublicPageSpider(Spider):
        name = "clue_ai_application_research"
        robots_txt_obey = ROBOTS_TXT_OBEY
        allowed_domains: ClassVar[set[str]] = {host}
        concurrent_requests = 1
        concurrent_requests_per_domain = SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN
        download_delay = SCRAPLING_DOWNLOAD_DELAY_SECONDS
        max_blocked_retries = 0
        logging_level = logging.WARNING
        user_agent = settings.crawler_user_agent

        def __init__(self) -> None:
            super().__init__()
            self.start_urls = [url]
            self.allowed_domains = {host}
            self.item: dict[str, Any] | None = None

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
            return status in {401, 403, 429} or _looks_blocked(
                getattr(response, "body", b"")
            )

        async def parse(self, response):
            response_url = str(getattr(response, "url", ""))
            parts = urlsplit(response_url)
            status = int(getattr(response, "status", 0) or 0)
            body = getattr(response, "body", b"")
            if (
                parts.scheme != "https"
                or (parts.hostname or "").casefold() != host
                or status in {401, 403, 429}
                or _looks_blocked(body)
            ):
                return
            if status < 200 or status >= 300 or len(body) > settings.max_page_bytes:
                return
            main_html = response.css("main").get() or response.css("article").get()
            page_html = main_html or response.css("body").get() or ""
            page_text = plain_text(page_html, min(settings.max_job_description_chars, RESEARCH_CHAR_LIMIT))
            links = []
            hrefs = response.css("a::attr(href)").getall()
            labels = response.css("a::text").getall()
            seen = set()
            for index, raw_href in enumerate(hrefs):
                candidate = normalize_public_job_url(urljoin(response_url, str(raw_href)))
                if not candidate:
                    continue
                target = candidate[0]
                if target == response_url or target in seen:
                    continue
                seen.add(target)
                links.append({
                    "label": plain_text(labels[index] if index < len(labels) else "", 120),
                    "url": target,
                })
                if len(links) >= 40:
                    break
            self.item = {
                "url": response_url,
                "title": plain_text(
                    response.css("title::text").get() or response.css("h1::text").get() or "",
                    240,
                ),
                "text": page_text,
                "links": links,
                "observed_at": utc_now(),
            }
            yield self.item

    try:
        spider = PublicPageSpider()
        spider.start()
    except Exception as exc:
        raise ResearchCrawlError(
            f"The public page could not be read ({type(exc).__name__}); Clue did not retry or follow redirects."
        ) from exc
    if spider.item is None:
        raise ResearchCrawlError("The public page was blocked, unavailable, or outside the crawl limits.")
    return spider.item


def _require_public_resolution(host: str) -> None:
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise ResearchCrawlError("The page host could not be resolved safely.") from exc
    if not addresses:
        raise ResearchCrawlError("The page host has no public address.")
    for value in addresses:
        try:
            address = ipaddress.ip_address(value)
        except ValueError as exc:
            raise ResearchCrawlError("The page host returned an invalid address.") from exc
        if not address.is_global:
            raise ResearchCrawlError("Private and local network addresses are not crawlable.")
