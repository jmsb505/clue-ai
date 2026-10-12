"""Small public-page crawler tools reserved exclusively for the Researcher stage."""

from __future__ import annotations

import ipaddress
import logging
import re
import socket
from html.parser import HTMLParser
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
FORM_FIELD_LIMIT = 25
FORM_OPTION_LIMIT = 8
MAX_RESEARCH_FORM_FIELDS = 40
MAX_RESEARCH_FORM_OPTIONS = 100


class _PublicFormParser(HTMLParser):
    """Read public field labels and choices without retaining submitted/default values."""

    _VOID: ClassVar[set[str]] = {
        "area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
        "param", "source", "track", "wbr",
    }
    _IGNORED_INPUTS: ClassVar[set[str]] = {
        "hidden", "password", "submit", "button", "reset", "image",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fields: list[dict[str, Any]] = []
        self.labels: dict[str, list[str]] = {}
        self.label_stack: list[dict[str, Any]] = []
        self.tag_stack: list[tuple[str, bool]] = []
        self.form_depth = 0
        self.select_field: dict[str, Any] | None = None
        self.active_option: list[str] | None = None
        self.fields_truncated = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        values = {key.casefold(): value or "" for key, value in attrs}
        inherited_hidden = any(hidden for _, hidden in self.tag_stack)
        style = values.get("style", "").replace(" ", "").casefold()
        own_hidden = (
            "hidden" in values
            or values.get("aria-hidden", "").casefold() == "true"
            or "display:none" in style
            or "visibility:hidden" in style
        )
        if tag not in self._VOID:
            self.tag_stack.append((tag, inherited_hidden or own_hidden))
        if tag == "form":
            self.form_depth += 1
        if tag == "label":
            self.label_stack.append({"for": values.get("for", ""), "text": []})
        if not self.form_depth or inherited_hidden or own_hidden:
            return
        if tag == "input":
            input_type = values.get("type", "text").casefold() or "text"
            if input_type in self._IGNORED_INPUTS:
                return
            self._add_field(
                values,
                input_type,
                self.label_stack[-1] if self.label_stack else None,
            )
        elif tag == "textarea":
            self._add_field(
                values,
                "textarea",
                self.label_stack[-1] if self.label_stack else None,
            )
        elif tag == "select":
            self.select_field = self._add_field(
                values,
                "select",
                self.label_stack[-1] if self.label_stack else None,
            )
        elif tag == "option" and self.select_field is not None:
            self.active_option = []

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if tag == "option" and self.active_option is not None:
            text = " ".join(" ".join(self.active_option).split())[:120]
            if text and len(self.select_field["options"]) < FORM_OPTION_LIMIT:
                self.select_field["options"].append(text)
            self.active_option = None
        if tag == "select":
            self.select_field = None
        if tag == "label" and self.label_stack:
            label = self.label_stack.pop()
            text = " ".join(" ".join(label["text"]).split())[:180]
            if label["for"] and text:
                self.labels.setdefault(label["for"], []).append(text)
        if tag == "form" and self.form_depth:
            self.form_depth -= 1
        for index in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[index][0] == tag:
                del self.tag_stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.active_option is not None:
            self.active_option.append(data)
        for label in self.label_stack:
            label["text"].append(data)

    def _add_field(
        self,
        attrs: dict[str, str],
        control_type: str,
        wrapped_label: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if len(self.fields) >= FORM_FIELD_LIMIT:
            self.fields_truncated = True
            return None
        field = {
            "label": "",
            "control_type": control_type,
            "required": "required" in attrs or attrs.get("aria-required", "").casefold() == "true",
            "options": [],
            "field_id": attrs.get("id", ""),
            "aria-label": attrs.get("aria-label", ""),
            "placeholder": attrs.get("placeholder", ""),
        }
        if wrapped_label is not None:
            field["wrapped_label"] = wrapped_label
        self.fields.append(field)
        return field

    def result(self) -> list[dict[str, Any]]:
        clean = []
        for index, field in enumerate(self.fields, start=1):
            id_label = self.labels.get(field.get("field_id", ""), [])
            wrapped = field.get("wrapped_label")
            wrapped_label = " ".join(" ".join(wrapped["text"]).split()) if wrapped else ""
            label = next(iter(id_label), "") or wrapped_label
            label = label or next(
                (
                    value
                    for value in (field.get("aria-label"), field.get("placeholder"))
                    if value
                ),
                "",
            )
            # Only keep user-facing labels and choice text. Never retain input names,
            # IDs, default values, or anything typed into a field.
            if not label:
                continue
            clean.append(
                {
                    "field_id": f"F{index:03d}",
                    "label": label[:180],
                    "control_type": field["control_type"],
                    "required": bool(field["required"]),
                    "options": field["options"][:FORM_OPTION_LIMIT],
                    "is_open_question": _is_open_question(label),
                }
            )
        return clean


def _is_open_question(label: str) -> bool:
    return bool(
        "?" in label
        or re.search(
            r"\b(?:why|what|how|describe|explain|tell us|walk us through|motivation|cover letter|personal statement|relevant experience|technical challenge)\b",
            label,
            re.IGNORECASE,
        )
    )


class ResearchCrawlError(ValueError):
    pass


class ResearchCrawlBlockedError(ResearchCrawlError):
    def __init__(self, message: str, *, request_sent: bool) -> None:
        super().__init__(message)
        self.request_sent = request_sent


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
        self.blocked_hosts: set[str] = set()
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
        if host in self.blocked_hosts:
            raise ResearchCrawlBlockedError(
                "Clue skipped this page because the site already denied access during this "
                "application. No request was sent to that host.",
                request_sent=False,
            )
        if len(self.pages) >= RESEARCH_PAGE_LIMIT:
            raise ResearchCrawlError("The four-page research limit for this listing was reached.")
        _require_public_resolution(host)
        try:
            page = _scrapling_fetch(normalized, host, self.settings)
        except ResearchCrawlBlockedError:
            self.blocked_hosts.add(host)
            raise
        fields_remaining = max(
            0,
            MAX_RESEARCH_FORM_FIELDS
            - sum(len(item.get("form_fields", [])) for item in self.pages.values()),
        )
        options_remaining = max(
            0,
            MAX_RESEARCH_FORM_OPTIONS
            - sum(
                len(field.get("options", []))
                for item in self.pages.values()
                for field in item.get("form_fields", [])
            ),
        )
        raw_fields = page.get("form_fields", [])
        page["form_fields"] = raw_fields[:fields_remaining]
        for field in page["form_fields"]:
            field["options"] = field.get("options", [])[:options_remaining]
            options_remaining -= len(field["options"])
        page["form_fields_truncated"] = bool(
            page.get("form_fields_truncated") or len(page["form_fields"]) < len(raw_fields)
        )
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
            self.access_denied = False

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
            self.access_denied = status in {401, 403, 429} or _looks_blocked(
                getattr(response, "body", b"")
            )
            return self.access_denied

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
            form_parser = _PublicFormParser()
            form_parser.feed("".join(response.css("form").getall()))
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
                "form_fields": form_parser.result(),
                "form_fields_truncated": form_parser.fields_truncated,
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
        if spider.access_denied:
            raise ResearchCrawlBlockedError(
                "The site denied the public-page request or returned an anti-bot challenge. "
                "Clue stopped requests to this host for this application.",
                request_sent=True,
            )
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
