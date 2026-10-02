from __future__ import annotations

import asyncio
import logging
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, ClassVar
from urllib.parse import parse_qs, quote, urljoin, urlsplit

from clue_ai.config import Settings
from clue_ai.crawl_policy import (
    COMPANY_CHILD_SITEMAP_LIMIT,
    COMPANY_DYNAMIC_RENDER_LIMIT,
    COMPANY_HTML_PAGE_LIMIT,
    COMPANY_SITEMAP_JOB_PAGE_LIMIT,
    PUBLIC_CRAWL_REFRESH_SECONDS,
    ROBOTS_TXT_OBEY,
    SCRAPLING_CONCURRENT_REQUESTS,
    SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN,
    SCRAPLING_DOWNLOAD_DELAY_SECONDS,
)
from clue_ai.domain import NormalizedJob, SearchCriteria
from clue_ai.jobs import canonical_url
from clue_ai.repository import companies_due, update_company_board
from clue_ai.sources import (
    SourceFetchError,
    _looks_blocked,
    _normalize_crawled_job,
    fetch_source,
    validate_career_url,
)

ATS_HOSTS = {
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "jobs.lever.co",
    "jobs.eu.lever.co",
    "jobs.ashbyhq.com",
    "careers.smartrecruiters.com",
}
ATS_SUFFIXES = (
    "teamtailor.com",
    "jobs.personio.de",
    "jobs.personio.com",
    "myworkdayjobs.com",
    "recruitee.com",
    "bamboohr.com",
    "jobvite.com",
)
ATS_LINK_DOMAINS = {*ATS_HOSTS, *ATS_SUFFIXES}
_CAREER_PATH = re.compile(
    r"(?i)(?:career|jobs?|roles?|openings?|vacancies|positions?|opportunities|"
    r"work[-_]?with[-_]?us|join[-_]?us|our[-_]?team)"
)
_JOB_DETAIL_PATH = re.compile(
    r"(?i)/(?:jobs?|positions?|roles?|openings?|vacancies|opportunities)/[^/?#]+"
)
_JOB_SITEMAP_PATH = re.compile(
    r"(?i)/(?:jobs?|positions?|roles?|openings?|vacancies|opportunities)/"
)


@dataclass
class CompanyCrawlSummary:
    companies_checked: int = 0
    boards_resolved: int = 0
    unavailable: int = 0
    blocked: int = 0
    pages_checked: int = 0
    response_bytes: int = 0
    raw_records: int = 0
    jobs_indexed: int = 0
    elapsed_seconds: float = 0.0
    errors: int = 0
    notes: list[str] = field(default_factory=list)


def detect_public_ats(url: str) -> dict[str, str] | None:
    """Resolve a public ATS only from an exact URL found on an employer's site."""
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        path = [part for part in parts.path.split("/") if part]
        if parts.scheme != "https" or not host:
            return None
        if host in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
            token = path[0] if path else parse_qs(parts.query).get("for", [""])[0]
            return _ats_result("greenhouse", token, url) if token else None
        if host in {"jobs.lever.co", "jobs.eu.lever.co"}:
            return _ats_result(
                "lever",
                path[0] if path else "",
                url,
                region="eu" if host.startswith("jobs.eu.") else "global",
            )
        if host == "jobs.ashbyhq.com":
            return _ats_result("ashby", path[0] if path else "", url)
        if host == "careers.smartrecruiters.com":
            return _ats_result("smartrecruiters", path[0] if path else "", url)
    except ValueError:
        return None
    return None


def _ats_result(provider: str, token: str, board_url: str, **extra: str) -> dict[str, str] | None:
    token = token.strip()
    if not token or len(token) > 160 or any(char in token for char in "?#"):
        return None
    return {
        "provider": provider,
        "board_name": token,
        "board_url": canonical_url(board_url),
        **extra,
    }


def public_ats_api(board: dict[str, str]) -> tuple[str, str] | None:
    """Build a documented public postings endpoint from a link actually found."""
    provider = board["provider"]
    token = quote(board["board_name"], safe="")
    if provider == "greenhouse":
        return provider, f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    if provider == "lever":
        host = "api.eu.lever.co" if board.get("region") == "eu" else "api.lever.co"
        return provider, f"https://{host}/v0/postings/{token}?mode=json"
    if provider == "ashby":
        return provider, f"https://api.ashbyhq.com/posting-api/job-board/{token}"
    if provider == "smartrecruiters":
        return (
            provider,
            f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100&offset=0",
        )
    return None


def _company_source(company: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": f"company-{company['id']}",
        "name": company["name"],
        "attribution": company["name"],
        "config": {"company": company["name"]},
    }


def _source_start(company: dict[str, Any]) -> str:
    return str(
        company.get("board_url") or company.get("careers_url") or company.get("homepage_url") or ""
    )


def _public_host(url: str) -> str:
    return (urlsplit(url).hostname or "").lower()


def _is_known_ats_host(host: str) -> bool:
    return host in ATS_HOSTS or any(host.endswith(f".{suffix}") for suffix in ATS_SUFFIXES)


def _html_ats_vendor(host: str) -> str:
    for suffix, label in (
        ("teamtailor.com", "Teamtailor"),
        ("jobs.personio.de", "Personio"),
        ("jobs.personio.com", "Personio"),
        ("myworkdayjobs.com", "Workday"),
        ("recruitee.com", "Recruitee"),
        ("bamboohr.com", "BambooHR"),
        ("jobvite.com", "Jobvite"),
    ):
        if host == suffix or host.endswith(f".{suffix}"):
            return label
    return "Employer-linked ATS"


def _valid_url(url: str) -> bool:
    return validate_career_url(url)[0]


def _safe_same_site_redirect(source_url: str, location: str) -> str:
    target = canonical_url(urljoin(source_url, location))
    try:
        source = urlsplit(source_url)
        destination = urlsplit(target)
        source_host = (source.hostname or "").lower()
        target_host = (destination.hostname or "").lower()
        same_host = target_host == source_host
        www_pair = target_host.removeprefix("www.") == source_host.removeprefix("www.")
        secure_target = (
            destination.scheme == "https"
            and not destination.username
            and not destination.password
            and destination.port in (None, 443)
        )
    except ValueError:
        return ""
    if (not same_host and not www_pair) or not secure_target:
        return ""
    return target if _valid_url(target) else ""


def _event(event: str, company_id: str, **payload: Any) -> dict[str, Any]:
    return {"_clue_event": event, "company_id": company_id, **payload}


def _candidate_start_urls(company: dict[str, Any]) -> list[str]:
    values = [_source_start(company)]
    return [url for url in values if url and _valid_url(url)]


def _make_company_spider(companies: list[dict[str, Any]], settings: Settings):
    try:
        from scrapling.fetchers import FetcherSession
        from scrapling.spiders import LinkExtractor, Request, Spider
    except ImportError as exc:
        raise SourceFetchError(
            "Scrapling is unavailable. Install the project dependencies."
        ) from exc

    owners = {str(company["id"]): company for company in companies}
    hosts = {
        host
        for company in companies
        for url in _candidate_start_urls(company)
        if (host := _public_host(url))
    }
    hosts.update(ATS_LINK_DOMAINS)

    class CompanyBoardSpider(Spider):
        name = "clue_ai_company_board_batch"
        robots_txt_obey = ROBOTS_TXT_OBEY
        allowed_domains: ClassVar[set[str]] = set(hosts)
        concurrent_requests = SCRAPLING_CONCURRENT_REQUESTS
        concurrent_requests_per_domain = SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN
        download_delay = SCRAPLING_DOWNLOAD_DELAY_SECONDS
        max_blocked_retries = 0
        logging_level = logging.INFO
        start_urls: ClassVar[tuple[str, ...]] = ()
        user_agent = settings.crawler_user_agent

        def __init__(self) -> None:
            super().__init__()
            self.allowed_domains = set(hosts)
            self.pages_by_company: dict[str, int] = {company_id: 0 for company_id in owners}
            self.scheduled: set[tuple[str, str]] = set()
            self.blocked_hosts: set[str] = set()
            self.careers_by_company = {
                str(company["id"]): str(company.get("careers_url") or "") for company in companies
            }
            self.boards_by_company: dict[str, dict[str, str]] = {}
            self.jobs_by_company: dict[str, int] = {company_id: 0 for company_id in owners}
            self.startup_events: list[dict[str, Any]] = []

        def configure_sessions(self, manager) -> None:
            manager.add(
                "ordinary",
                FetcherSession(
                    impersonate=None,
                    timeout=settings.network_timeout_seconds,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml,application/json,application/xml;q=0.9,*/*;q=0.5",
                    },
                    retries=0,
                    retry_delay=0,
                    follow_redirects=False,
                    verify=True,
                ),
            )

        async def start_requests(self):
            for company in companies:
                company_id = str(company["id"])
                start_url = _source_start(company)
                if not start_url or not _valid_url(start_url):
                    self.startup_events.append(
                        _event(
                            "status",
                            company_id,
                            state="unavailable",
                            last_state="invalid_url",
                            error="No public HTTPS careers URL is available.",
                        )
                    )
                    continue
                board = detect_public_ats(start_url)
                if board:
                    self.boards_by_company[company_id] = board
                    api = public_ats_api(board)
                    self.startup_events.append(
                        _event(
                            "board",
                            company_id,
                            board_url=board["board_url"],
                            provider=board["provider"],
                            board_name=board["board_name"],
                            region=board.get("region", ""),
                            careers_url=str(company.get("careers_url") or ""),
                        )
                    )
                    if api:
                        continue
                    request = self._request(
                        start_url,
                        company_id,
                        stage="html",
                        careers_url=str(company.get("careers_url") or ""),
                        expected_host=_public_host(start_url),
                    )
                    if request is not None:
                        yield request
                    continue
                start_host = _public_host(start_url)
                if _is_known_ats_host(start_host):
                    self.startup_events.append(
                        _event(
                            "board",
                            company_id,
                            board_url=start_url,
                            provider=_html_ats_vendor(start_host),
                            careers_url=str(company.get("careers_url") or ""),
                        )
                    )
                request = self._request(
                    start_url,
                    company_id,
                    stage="html",
                    careers_url=str(company.get("careers_url") or ""),
                )
                if request is not None:
                    yield request

        def _request(self, url: str, company_id: str, **meta: Any):
            normalized = canonical_url(url)
            key = (company_id, normalized)
            if (
                not normalized
                or key in self.scheduled
                or _public_host(normalized) in self.blocked_hosts
            ):
                return None
            if not _valid_url(normalized):
                return None
            self.allowed_domains.add(_public_host(normalized))
            if (
                meta.get("stage") == "html"
                and self.pages_by_company.get(company_id, 0) >= COMPANY_HTML_PAGE_LIMIT
            ):
                return None
            self.scheduled.add(key)
            if meta.get("stage") == "html":
                self.pages_by_company[company_id] = self.pages_by_company.get(company_id, 0) + 1
            return Request(
                normalized,
                sid=self._session_manager.default_session_id,
                callback=self.parse_page,
                meta={
                    "company_id": company_id,
                    "expected_host": meta.get("expected_host") or _public_host(normalized),
                    **meta,
                },
                headers={"User-Agent": self.user_agent},
            )

        async def is_blocked(self, response):
            # Callbacks record the owning company and stop adding requests to the blocked host.
            # The session and Spider have retries disabled.
            return False

        async def parse(self, response):
            async for item in self.parse_page(response):
                yield item

        async def parse_page(self, response):
            meta = dict(getattr(response, "meta", {}) or {})
            company_id = str(meta.get("company_id") or "")
            company = owners.get(company_id)
            if not company:
                return
            company_source = _company_source(company)
            response_url = str(getattr(response, "url", ""))
            response_host = _public_host(response_url)
            owner_hosts = {_public_host(url) for url in _candidate_start_urls(company)}
            status = int(getattr(response, "status", 0) or 0)
            body = getattr(response, "body", b"")
            if response_host != str(meta.get("expected_host") or ""):
                yield _event(
                    "status",
                    company_id,
                    state="unavailable",
                    last_state="off_host_response",
                    error="The source redirected outside its observed public hosts.",
                )
                return
            if status in {301, 302, 303, 307, 308}:
                location = getattr(response, "headers", {}).get("location", "")
                if isinstance(location, bytes):
                    location = location.decode("utf-8", errors="ignore")
                target = _safe_same_site_redirect(response_url, str(location))
                if target and int(meta.get("redirect_count") or 0) < 2:
                    request = self._request(
                        target,
                        company_id,
                        stage="html",
                        careers_url=meta.get("careers_url", ""),
                        redirect_count=int(meta.get("redirect_count") or 0) + 1,
                        expected_host=_public_host(target),
                    )
                    if request is not None:
                        yield request
                        return
                yield _event(
                    "status",
                    company_id,
                    state="unavailable",
                    last_state="redirect_not_followed",
                    error="The source redirected outside its observed host or exceeded the redirect limit.",
                )
                return
            if status in {401, 403, 429} or _looks_blocked(body):
                self.blocked_hosts.add(response_host)
                yield _event(
                    "status",
                    company_id,
                    state="blocked",
                    last_state="blocked",
                    error=f"HTTP {status or 'challenge'}; this host was paused for this search.",
                )
                return
            if status == 404:
                yield _event(
                    "status",
                    company_id,
                    state="unavailable",
                    last_state="not_found",
                    error="The observed careers or ATS URL returned HTTP 404.",
                )
                return
            if status < 200 or status >= 300:
                yield _event(
                    "status",
                    company_id,
                    state="unavailable",
                    last_state=f"http_{status}",
                    error=f"The public source returned HTTP {status}.",
                )
                return
            if len(body) > settings.max_page_bytes:
                yield _event(
                    "status",
                    company_id,
                    state="unavailable",
                    last_state="response_too_large",
                    error="The response exceeded the local size limit.",
                )
                return
            yield _event(
                "page",
                company_id,
                url=response_url,
                status=status,
                provider=meta.get("provider", ""),
                response_bytes=len(body),
            )
            structured = _extract_jsonld_job_postings(response, company_source, settings)
            for item in structured:
                job = _normalize_crawled_job(company_source, item, settings)
                if job:
                    self.jobs_by_company[company_id] += 1
                    yield _event("job", company_id, job=asdict(job))
            if structured:
                yield _event(
                    "status",
                    company_id,
                    state="checked",
                    last_state="jobposting_jsonld",
                    listing_count=self.jobs_by_company[company_id],
                )
            elif _JOB_DETAIL_PATH.search(urlsplit(response_url).path):
                item = _extract_html_job_posting(response, company_source, settings)
                if item:
                    job = _normalize_crawled_job(company_source, item, settings)
                    if job:
                        self.jobs_by_company[company_id] += 1
                        yield _event("job", company_id, job=asdict(job))
                        yield _event(
                            "status",
                            company_id,
                            state="checked",
                            last_state="html_job_detail",
                            listing_count=self.jobs_by_company[company_id],
                        )

            try:
                extract_links = LinkExtractor(
                    allow_domains=[*owner_hosts, *ATS_LINK_DOMAINS],
                    deny_domains=["x.com", "twitter.com", "t.co"],
                )
                links = extract_links.extract(response)
            except (AttributeError, TypeError, ValueError):
                links = []
            internal_careers: list[str] = []
            job_details: list[str] = []
            ats_links: list[dict[str, str]] = []
            for link in links:
                link = canonical_url(str(link))
                link_host = _public_host(link)
                if not link:
                    continue
                if link_host not in owner_hosts and not _is_known_ats_host(link_host):
                    continue
                ats = detect_public_ats(link)
                if ats:
                    if not _valid_url(link):
                        continue
                    ats_links.append(ats)
                    continue
                if _is_known_ats_host(link_host):
                    path = urlsplit(link).path
                    if _JOB_DETAIL_PATH.search(path):
                        if _valid_url(link):
                            job_details.append(link)
                    elif (
                        link_host == response_host
                        and _CAREER_PATH.search(path)
                        and _valid_url(link)
                    ):
                        internal_careers.append(link)
                    continue
                if link_host not in owner_hosts:
                    continue
                path = urlsplit(link).path
                if _JOB_DETAIL_PATH.search(path):
                    if _valid_url(link):
                        job_details.append(link)
                elif (
                    _CAREER_PATH.search(path)
                    and link != canonical_url(response_url)
                    and _valid_url(link)
                ):
                    internal_careers.append(link)

            # Follow official links only. A listed ATS is accepted only if the employer page linked it.
            for board in ats_links[:10]:
                existing = self.boards_by_company.get(company_id)
                if existing and existing["board_url"] == board["board_url"]:
                    continue
                self.boards_by_company[company_id] = board
                api = public_ats_api(board)
                yield _event(
                    "board",
                    company_id,
                    board_url=board["board_url"],
                    provider=board["provider"],
                    board_name=board["board_name"],
                    region=board.get("region", ""),
                    careers_url=self.careers_by_company.get(company_id, "") or response_url,
                )
                if not api:
                    request = self._request(
                        board["board_url"],
                        company_id,
                        stage="html",
                        careers_url=response_url,
                        expected_host=_public_host(board["board_url"]),
                    )
                    if request is not None:
                        yield request

            # Unsupported but recognizable ATS vendors remain useful as ordinary HTML sources.
            for link in links:
                linked_url = canonical_url(str(link))
                linked_host = _public_host(linked_url)
                if linked_host in owner_hosts or not _is_known_ats_host(linked_host):
                    continue
                if detect_public_ats(linked_url) or not _valid_url(linked_url):
                    continue
                path = urlsplit(linked_url).path
                if not (_CAREER_PATH.search(path) or _JOB_DETAIL_PATH.search(path)):
                    continue
                yield _event(
                    "board",
                    company_id,
                    board_url=linked_url,
                    provider=_html_ats_vendor(linked_host),
                    careers_url=response_url,
                )
                request = self._request(
                    linked_url,
                    company_id,
                    stage="html",
                    careers_url=response_url,
                    expected_host=linked_host,
                )
                if request is not None:
                    yield request

            for career_url in internal_careers[:10]:
                if not self.careers_by_company.get(company_id):
                    self.careers_by_company[company_id] = career_url
                yield _event("board", company_id, careers_url=career_url)
                request = self._request(
                    career_url, company_id, stage="html", careers_url=career_url
                )
                if request is not None:
                    yield request

            if self.jobs_by_company.get(company_id, 0) == 0:
                for job_url in job_details[:20]:
                    request = self._request(
                        job_url,
                        company_id,
                        stage="html",
                        careers_url=self.careers_by_company.get(company_id, ""),
                    )
                    if request is not None:
                        yield request
            if not structured and _looks_like_js_shell(body):
                yield _event("dynamic_candidate", company_id, url=response_url)
            if not structured and not ats_links and not internal_careers and not job_details:
                yield _event(
                    "status",
                    company_id,
                    state="checked",
                    last_state="no_static_listings",
                    listing_count=self.jobs_by_company[company_id],
                )

    return CompanyBoardSpider()


def _looks_like_js_shell(body: bytes) -> bool:
    text = body[:200_000].decode("utf-8", errors="ignore").casefold()
    markers = (
        'id="root"',
        "id='root'",
        'id="app"',
        "id='app'",
        "enable javascript",
        "__next_data__",
        "window.__initial_state__",
    )
    return any(marker in text for marker in markers)


def _make_sitemap_spider(companies: list[dict[str, Any]], settings: Settings):
    try:
        from scrapling.fetchers import FetcherSession
        from scrapling.spiders import CrawlRule, LinkExtractor, Request, SitemapSpider
    except ImportError as exc:
        raise SourceFetchError("Scrapling sitemap support is unavailable.") from exc

    owners = {str(company["id"]): company for company in companies}
    sitemap_hosts: dict[str, str] = {}
    for company in companies:
        company_id = str(company["id"])
        base = str(
            company.get("careers_url")
            or company.get("board_url")
            or company.get("homepage_url")
            or ""
        )
        if not base or not _valid_url(base):
            continue
        parts = urlsplit(base)
        host = (parts.hostname or "").lower()
        sitemap_hosts[company_id] = host

    class CompanySitemapSpider(SitemapSpider):
        name = "clue_ai_company_sitemap_batch"
        robots_txt_obey = ROBOTS_TXT_OBEY
        allowed_domains: ClassVar[set[str]] = set(sitemap_hosts.values())
        concurrent_requests = SCRAPLING_CONCURRENT_REQUESTS
        concurrent_requests_per_domain = SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN
        download_delay = SCRAPLING_DOWNLOAD_DELAY_SECONDS
        max_blocked_retries = 0
        logging_level = logging.INFO
        sitemap_urls: ClassVar[tuple[str, ...]] = ()
        sitemap_follow = None
        user_agent = settings.crawler_user_agent

        def __init__(self) -> None:
            super().__init__()
            self.allowed_domains = set(sitemap_hosts.values())
            self.sitemap_follow = LinkExtractor(
                allow=re.compile(
                    r"(?i)(?:job|career|work|open|position|vacanc|sitemap)[^/]*\.xml(?:\.gz)?(?:$|\?)"
                )
            )
            self.dispatched: dict[str, int] = {company_id: 0 for company_id in owners}
            self.child_sitemaps: dict[str, int] = {company_id: 0 for company_id in owners}

        def configure_sessions(self, manager) -> None:
            manager.add(
                "ordinary",
                FetcherSession(
                    impersonate=None,
                    timeout=settings.network_timeout_seconds,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/plain,application/xml,text/xml;q=0.9,*/*;q=0.5",
                    },
                    retries=0,
                    retry_delay=0,
                    follow_redirects=False,
                    verify=True,
                ),
            )

        async def start_requests(self):
            for company_id, host in sitemap_hosts.items():
                if not host:
                    continue
                company = owners[company_id]
                origin = urlsplit(
                    str(
                        company.get("careers_url")
                        or company.get("board_url")
                        or company.get("homepage_url")
                    )
                )
                url = f"{origin.scheme}://{origin.netloc}/robots.txt"
                yield Request(
                    url,
                    sid=self._session_manager.default_session_id,
                    callback=self._parse_sitemap,
                    meta={"company_id": company_id, "sitemap_host": host},
                    headers={"User-Agent": self.user_agent},
                )

        def rules(self):
            return [
                CrawlRule(
                    LinkExtractor(allow=_JOB_SITEMAP_PATH, allow_domains=self.allowed_domains),
                    callback=self.parse_sitemap_job,
                )
            ]

        @staticmethod
        def _get_type(element) -> str:
            # Scrapling 0.4.15's sitemap walker can pass XML comments to etree.QName.
            # Treat comments and processing nodes as empty so one sitemap cannot stop a batch.
            if not isinstance(element.tag, str):
                return ""
            from lxml import etree

            return etree.QName(element.tag).localname

        async def _parse_sitemap(self, response):
            meta = dict(getattr(response, "meta", {}) or {})
            company_id = str(meta.get("company_id") or "")
            expected_host = sitemap_hosts.get(company_id, "")
            response_host = _public_host(str(getattr(response, "url", "")))
            status = int(getattr(response, "status", 0) or 0)
            body = getattr(response, "body", b"")
            if not company_id or response_host != expected_host:
                return
            if status in {301, 302, 303, 307, 308}:
                location = getattr(response, "headers", {}).get("location", "")
                if isinstance(location, bytes):
                    location = location.decode("utf-8", errors="ignore")
                target = _safe_same_site_redirect(str(getattr(response, "url", "")), str(location))
                if target and int(meta.get("redirect_count") or 0) < 2:
                    target_host = _public_host(target)
                    request = response.follow(target, callback=self._parse_sitemap)
                    request.meta["company_id"] = company_id
                    request.meta["sitemap_host"] = target_host
                    request.meta["redirect_count"] = int(meta.get("redirect_count") or 0) + 1
                    sitemap_hosts[company_id] = target_host
                    self.allowed_domains.add(target_host)
                    yield request
                else:
                    yield _event(
                        "status",
                        company_id,
                        state="unavailable",
                        last_state="sitemap_redirect_not_followed",
                        error="The sitemap redirected outside its observed host or exceeded the redirect limit.",
                    )
                return
            if status in {401, 403, 429} or _looks_blocked(body):
                yield _event(
                    "status",
                    company_id,
                    state="blocked",
                    last_state="sitemap_blocked",
                    error=f"HTTP {status or 'challenge'} on the sitemap source.",
                )
                return
            if status < 200 or status >= 300 or len(body) > settings.max_feed_bytes:
                return
            yield _event(
                "page",
                company_id,
                url=str(getattr(response, "url", "")),
                status=status,
                stage="sitemap",
                response_bytes=len(body),
            )
            try:
                async for result in super()._parse_sitemap(response):
                    if isinstance(result, Request):
                        result_host = _public_host(result.url)
                        if result_host != expected_host:
                            continue
                        path = urlsplit(result.url).path.casefold()
                        if path.endswith(("robots.txt", ".xml", ".xml.gz")):
                            if (
                                self.child_sitemaps.get(company_id, 0)
                                >= COMPANY_CHILD_SITEMAP_LIMIT
                            ):
                                continue
                            self.child_sitemaps[company_id] += 1
                        result.meta["company_id"] = company_id
                        result.meta["sitemap_host"] = expected_host
                        yield result
                    elif result is not None:
                        yield result
            except ValueError:
                yield _event(
                    "status",
                    company_id,
                    state="checked",
                    last_state="sitemap_parse_error",
                    error="An official sitemap had malformed XML; other company sources continue.",
                )

        def _dispatch(self, response, url, rules):
            meta = dict(getattr(response, "meta", {}) or {})
            company_id = str(meta.get("company_id") or "")
            expected_host = sitemap_hosts.get(company_id, "")
            if (
                _public_host(str(url)) != expected_host
                or self.dispatched.get(company_id, 0) >= COMPANY_SITEMAP_JOB_PAGE_LIMIT
            ):
                return None
            request = super()._dispatch(response, url, rules)
            if request is not None:
                request.meta["company_id"] = company_id
                request.meta["sitemap_host"] = expected_host
                self.dispatched[company_id] = self.dispatched.get(company_id, 0) + 1
            return request

        async def parse_sitemap_job(self, response):
            meta = dict(getattr(response, "meta", {}) or {})
            company_id = str(meta.get("company_id") or "")
            expected_host = sitemap_hosts.get(company_id, "")
            if not company_id or _public_host(str(getattr(response, "url", ""))) != expected_host:
                return
            status = int(getattr(response, "status", 0) or 0)
            body = getattr(response, "body", b"")
            if status in {401, 403, 429} or _looks_blocked(body):
                yield _event(
                    "status",
                    company_id,
                    state="blocked",
                    last_state="sitemap_job_blocked",
                    error=f"HTTP {status or 'challenge'} on an official job URL.",
                )
                return
            if status < 200 or status >= 300 or len(body) > settings.max_page_bytes:
                return
            yield _event(
                "page",
                company_id,
                url=str(getattr(response, "url", "")),
                status=status,
                stage="sitemap_job",
                response_bytes=len(body),
            )
            company = owners[company_id]
            source = _company_source(company)
            structured = _extract_jsonld_job_postings(response, source, settings)
            for item in structured:
                job = _normalize_crawled_job(source, item, settings)
                if job:
                    yield _event("job", company_id, job=asdict(job))
            if not structured:
                item = _extract_html_job_posting(response, source, settings)
                if item:
                    job = _normalize_crawled_job(source, item, settings)
                    if job:
                        yield _event("job", company_id, job=asdict(job))

    return CompanySitemapSpider()


def _extract_jsonld_job_postings(
    response, source: dict[str, Any], settings: Settings
) -> list[dict[str, Any]]:
    from clue_ai.sources import _extract_jsonld_job_postings as extract

    return extract(response, source, settings)


def _extract_html_job_posting(
    response, source: dict[str, Any], settings: Settings
) -> dict[str, Any] | None:
    from clue_ai.sources import _extract_html_job_posting as extract

    return extract(response, source, settings)


def _run_spider_stream(spider, on_event: Callable[[dict[str, Any]], None]) -> None:
    async def consume() -> None:
        async for event in spider.stream():
            on_event(event)

    asyncio.run(consume())


def crawl_tracked_companies(
    database_path,
    settings: Settings,
    *,
    on_progress: Callable[[str], None] | None = None,
    save_jobs: Callable[[list[NormalizedJob]], int] | None = None,
    force: bool = False,
) -> CompanyCrawlSummary:
    started_at = time.monotonic()
    due = companies_due(
        database_path,
        limit=100,
        interval_seconds=PUBLIC_CRAWL_REFRESH_SECONDS,
        force=force,
    )
    summary = CompanyCrawlSummary(companies_checked=len(due))
    if not due:
        summary.elapsed_seconds = round(time.monotonic() - started_at, 2)
        return summary
    records = {str(company["id"]): company for company in due}
    statuses: dict[str, dict[str, Any]] = {}
    boards: dict[str, dict[str, str]] = {}
    jobs_seen: dict[str, int] = {company_id: 0 for company_id in records}
    dynamic_urls: dict[str, str] = {}
    blocked_api_hosts: set[str] = set()

    def process_event(event: dict[str, Any]) -> None:
        event_type = str(event.get("_clue_event") or "")
        company_id = str(event.get("company_id") or "")
        if company_id not in records:
            return
        company = records[company_id]
        if event_type == "job":
            try:
                job = NormalizedJob(**event["job"])
            except (KeyError, TypeError):
                summary.errors += 1
                return
            jobs_seen[company_id] = jobs_seen.get(company_id, 0) + 1
            summary.raw_records += 1
            if save_jobs:
                summary.jobs_indexed += save_jobs([job])
            return
        if event_type == "page":
            summary.pages_checked += 1
            summary.response_bytes += int(event.get("response_bytes") or 0)
            return
        if event_type == "board":
            boards[company_id] = {
                "board_url": str(event.get("board_url") or ""),
                "provider": str(event.get("provider") or ""),
                "board_name": str(event.get("board_name") or ""),
                "region": str(event.get("region") or ""),
            }
            if event.get("careers_url"):
                company["careers_url"] = str(event["careers_url"])
            if event.get("board_url"):
                company["board_url"] = str(event["board_url"])
            if event.get("provider"):
                company["provider"] = str(event["provider"])
            return
        if event_type == "dynamic_candidate":
            dynamic_urls.setdefault(company_id, str(event.get("url") or ""))
            return
        if event_type == "status":
            statuses[company_id] = dict(event)

    if on_progress:
        on_progress(f"Crawling public career pages for {len(due)} tracked companies.")
    spider = _make_company_spider(due, settings)
    _run_spider_stream(spider, process_event)
    for startup_event in getattr(spider, "startup_events", []):
        process_event(startup_event)

    # The public ATS adapters run only after a board URL was found in the catalog or linked by
    # the employer. Calls are grouped by provider host, rate limited, and a block stops that host.
    last_api_request: dict[str, float] = {}
    criteria = SearchCriteria()
    for company_id, board in boards.items():
        api = public_ats_api(board)
        if not api:
            continue
        provider, api_url = api
        company = records[company_id]
        api_host = _public_host(api_url)
        if api_host in blocked_api_hosts:
            statuses[company_id] = _event(
                "status",
                company_id,
                state="blocked",
                last_state="provider_host_paused",
                error="This public ATS host was paused after another board returned a block response.",
            )
            continue
        elapsed = time.monotonic() - last_api_request.get(api_host, 0.0)
        if api_host in last_api_request and elapsed < 2.0:
            time.sleep(2.0 - elapsed)
        if on_progress:
            on_progress(f"Reading {company['name']} listings from its linked {provider} board.")
        config = {
            "company": company["name"],
            "board_token": board.get("board_name", ""),
            "site": board.get("board_name", ""),
            "board_name": board.get("board_name", ""),
            "company_id": board.get("board_name", ""),
            "region": board.get("region") or "global",
        }
        source = {
            "id": f"company-{company_id}",
            "name": company["name"],
            "kind": provider,
            "endpoint": board["board_url"],
            "state": "approved",
            "enabled": True,
            "attribution": company["name"],
            "config": config,
        }
        try:
            outcome = fetch_source(source, criteria, settings)
            last_api_request[api_host] = time.monotonic()
            summary.pages_checked += outcome.checked
            summary.response_bytes += outcome.response_bytes
            for job in outcome.jobs:
                process_event(_event("job", company_id, job=asdict(job)))
            status = _event(
                "status",
                company_id,
                state="resolved",
                last_state="api_checked",
                provider=provider,
                listing_count=jobs_seen.get(company_id, 0),
                raw_records=outcome.raw_records,
            )
            statuses[company_id] = status
        except SourceFetchError as exc:
            last_api_request[api_host] = time.monotonic()
            if exc.blocked:
                blocked_api_hosts.add(api_host)
                statuses[company_id] = _event(
                    "status",
                    company_id,
                    state="blocked",
                    last_state="blocked",
                    error=str(exc),
                )
            else:
                statuses[company_id] = _event(
                    "status",
                    company_id,
                    state="unavailable",
                    last_state="api_error",
                    error=str(exc),
                )

    # SitemapSpider uses the employer's robots.txt as sitemap discovery metadata; per-company
    # sitemap and job-page requests remain explicitly bounded by crawl_policy.py.
    needs_sitemap = [
        company
        for company in due
        if jobs_seen.get(str(company["id"]), 0) == 0
        and bool(_candidate_start_urls(company))
        and statuses.get(str(company["id"]), {}).get("state") != "blocked"
        and statuses.get(str(company["id"]), {}).get("last_state") != "api_checked"
    ]
    if needs_sitemap:
        if on_progress:
            on_progress(
                f"Checking official robots.txt sitemaps for {len(needs_sitemap)} companies without parsed listings."
            )
        sitemap_spider = _make_sitemap_spider(needs_sitemap, settings)
        _run_spider_stream(sitemap_spider, process_event)

    # Render detected client-rendered career shells with a bounded public-page fallback.
    if dynamic_urls:
        try:
            from scrapling.fetchers import DynamicFetcher
        except ImportError:
            DynamicFetcher = None
        if DynamicFetcher:
            for company_id, url in list(dynamic_urls.items())[:COMPANY_DYNAMIC_RENDER_LIMIT]:
                if (
                    jobs_seen.get(company_id, 0)
                    or statuses.get(company_id, {}).get("state") == "blocked"
                    or not url
                    or not _valid_url(url)
                ):
                    continue
                try:
                    response = DynamicFetcher.fetch(
                        url,
                        max_pages=1,
                        headless=True,
                        disable_resources=True,
                        useragent=settings.crawler_user_agent,
                        network_idle=False,
                        load_dom=True,
                        google_search=False,
                        retries=0,
                        retry_delay=0,
                        proxy=None,
                        proxy_rotator=None,
                        cookies=None,
                        timeout=int(settings.network_timeout_seconds * 1000),
                    )
                    if _public_host(str(getattr(response, "url", ""))) != _public_host(url):
                        statuses[company_id] = _event(
                            "status",
                            company_id,
                            state="unavailable",
                            last_state="dynamic_off_host",
                            error="The rendered page changed to a different host and was ignored.",
                        )
                        continue
                    company = records[company_id]
                    source = _company_source(company)
                    for item in _extract_jsonld_job_postings(response, source, settings):
                        job = _normalize_crawled_job(source, item, settings)
                        if job:
                            process_event(_event("job", company_id, job=asdict(job)))
                    if jobs_seen.get(company_id, 0):
                        statuses[company_id] = _event(
                            "status",
                            company_id,
                            state="checked",
                            last_state="dynamic_fetch",
                            listing_count=jobs_seen[company_id],
                        )
                except Exception as exc:  # noqa: BLE001 - the optional browser runtime has varied backend errors.
                    statuses[company_id] = _event(
                        "status",
                        company_id,
                        state="checked",
                        last_state="dynamic_unavailable",
                        error=f"The optional browser fallback failed ({type(exc).__name__}).",
                    )

    summary.boards_resolved = len(
        {company_id for company_id, board in boards.items() if board.get("board_url")}
    )
    summary.blocked = sum(status.get("state") == "blocked" for status in statuses.values())
    summary.unavailable = sum(status.get("state") == "unavailable" for status in statuses.values())
    for company_id, company in records.items():
        status = statuses.get(company_id, {})
        board = boards.get(company_id, {})
        state = str(status.get("state") or ("resolved" if jobs_seen.get(company_id) else "checked"))
        if state not in {"blocked", "unavailable", "checked", "resolved"}:
            state = "checked"
        listing_count = jobs_seen.get(company_id, int(status.get("listing_count") or 0))
        update_company_board(
            database_path,
            company_id,
            board_state=state,
            last_state=str(
                status.get("last_state") or ("listings_found" if listing_count else "no_listings")
            ),
            careers_url=str(company.get("careers_url") or ""),
            board_url=str(company.get("board_url") or ""),
            provider=str(company.get("provider") or ""),
            error=str(status.get("error") or ""),
            listing_count=listing_count,
        )
        summary.notes.append(
            f"{company['name']}: {state}; {listing_count} listing(s); {status.get('last_state', 'checked')}."
        )
    if on_progress:
        on_progress(
            f"Company crawl checked {summary.companies_checked} boards and indexed {summary.jobs_indexed} listings."
        )
    summary.elapsed_seconds = round(time.monotonic() - started_at, 2)
    return summary
