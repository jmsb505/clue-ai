from __future__ import annotations

import ipaddress
import json
import re
import socket
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Any, ClassVar
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from clue_ai.config import Settings
from clue_ai.domain import NormalizedJob, SearchCriteria
from clue_ai.jobs import canonical_url, infer_workplace, parse_date, plain_text
from clue_ai.repository import record_role_feed_check, role_feed_due


class SourceFetchError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, blocked: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.blocked = blocked


@dataclass
class FetchOutcome:
    jobs: list[NormalizedJob] = field(default_factory=list)
    checked: int = 0
    message: str = ""
    blocked: bool = False
    skipped: bool = False


SOURCE_HOSTS = {
    "jobicy_api": {"jobicy.com"},
    "remotejobs_api": {"remotejobs.org"},
    "remoteok_json": {"remoteok.com"},
    "remote_first_rss": {"remotefirstjobs.com"},
    "startup_rss": {"startup.jobs"},
    "greenhouse": {"boards-api.greenhouse.io"},
    "lever": {"api.lever.co"},
    "smartrecruiters": {"api.smartrecruiters.com"},
}


def fetch_source(
    source: dict[str, Any],
    criteria: SearchCriteria,
    settings: Settings,
    database_path=None,
) -> FetchOutcome:
    """Fetch only an enabled, already-approved source supplied by the registry."""
    if source.get("state") != "approved" or not source.get("enabled"):
        return FetchOutcome(message="This source is not approved and enabled.", skipped=True)
    kind = str(source.get("kind") or "")
    if kind == "scrapling":
        return crawl_career_page(source, settings)
    if kind not in SOURCE_HOSTS:
        return FetchOutcome(message="No connector is available for this source.", skipped=True)
    if kind == "remote_first_rss":
        if database_path is None:
            raise SourceFetchError("The role-feed refresh ledger is unavailable.")
        return _fetch_remote_first(source, criteria, settings, database_path)
    if kind == "remotejobs_api":
        if database_path is None:
            raise SourceFetchError("The role-query refresh ledger is unavailable.")
        return _fetch_remotejobs(source, criteria, settings, database_path)

    url = _connector_url(source)
    allowed_hosts = _allowed_hosts(source, kind, url)
    if not _url_is_allowed(url, allowed_hosts):
        raise SourceFetchError("The source endpoint is outside its registered host.", blocked=True)
    payload = _fetch_bytes(url, allowed_hosts, settings)
    try:
        if kind in {"jobicy_api", "remotejobs_api", "remoteok_json", "greenhouse", "lever", "smartrecruiters"}:
            raw = json.loads(payload.decode("utf-8-sig"))
            jobs = _parse_json_feed(kind, source, raw, settings)
        else:
            jobs = _parse_rss_feed(source, payload, settings)
    except (UnicodeDecodeError, json.JSONDecodeError, ET.ParseError) as exc:
        raise SourceFetchError("The listing feed could not be parsed.") from exc
    return FetchOutcome(jobs=jobs, checked=1, message=f"Retrieved {len(jobs)} listing records.")


def _connector_url(source: dict[str, Any]) -> str:
    kind = source["kind"]
    config = source.get("config") or {}
    if kind == "greenhouse":
        token = quote(str(config.get("board_token") or ""), safe="")
        return f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    if kind == "lever":
        site = quote(str(config.get("site") or ""), safe="")
        return f"https://api.lever.co/v0/postings/{site}?mode=json"
    if kind == "smartrecruiters":
        company_id = quote(str(config.get("company_id") or ""), safe="")
        return f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings?limit=100&offset=0"
    return str(source.get("endpoint") or "")


def _allowed_hosts(source: dict[str, Any], kind: str, url: str) -> set[str]:
    if kind in SOURCE_HOSTS:
        return SOURCE_HOSTS[kind]
    host = (urlsplit(url).hostname or "").lower()
    return {host} if host else set()


def _url_is_allowed(url: str, hosts: set[str]) -> bool:
    try:
        parts = urlsplit(url)
        return (
            parts.scheme == "https"
            and parts.hostname is not None
            and parts.hostname.lower() in hosts
            and not parts.username
            and not parts.password
            and parts.port in (None, 443)
        )
    except ValueError:
        return False


class _SameHostRedirect(HTTPRedirectHandler):
    def __init__(self, allowed_hosts: set[str]):
        super().__init__()
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, request, fp, code, message, headers, new_url):
        if not _url_is_allowed(new_url, self.allowed_hosts):
            raise URLError("Cross-host or non-HTTPS redirect blocked.")
        return super().redirect_request(request, fp, code, message, headers, new_url)


def _fetch_bytes(url: str, allowed_hosts: set[str], settings: Settings) -> bytes:
    if not _url_is_allowed(url, allowed_hosts):
        raise SourceFetchError("The request URL is not approved.", blocked=True)
    req = Request(
        url,
        headers={
            "User-Agent": settings.crawler_user_agent,
            "Accept": "application/json, application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9, */*;q=0.5",
        },
    )
    opener = build_opener(_SameHostRedirect(allowed_hosts))
    try:
        with opener.open(req, timeout=settings.network_timeout_seconds) as response:
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > settings.max_feed_bytes:
                raise SourceFetchError("The source response exceeds the local size limit.")
            body = response.read(settings.max_feed_bytes + 1)
            if len(body) > settings.max_feed_bytes:
                raise SourceFetchError("The source response exceeds the local size limit.")
            if _looks_blocked(body):
                raise SourceFetchError("The source returned a bot or access challenge.", blocked=True)
            return body
    except HTTPError as exc:
        blocked = exc.code in {401, 403, 429}
        raise SourceFetchError(
            f"The source returned HTTP {exc.code}.",
            status_code=exc.code,
            blocked=blocked,
        ) from exc
    except (TimeoutError, URLError, OSError) as exc:
        raise SourceFetchError(f"The source could not be reached: {type(exc).__name__}.") from exc


def _looks_blocked(payload: bytes) -> bool:
    sample = payload[:120_000].decode("utf-8", errors="ignore").casefold()
    markers = (
        "captcha",
        "verify you are human",
        "access denied",
        "unusual traffic",
        "automated requests",
        "bot detection",
        "cf-chl-",
        "cloudflare ray id",
    )
    return any(marker in sample for marker in markers)


def _parse_json_feed(
    kind: str,
    source: dict[str, Any],
    raw: Any,
    settings: Settings,
) -> list[NormalizedJob]:
    items: list[dict[str, Any]] = []
    if kind == "jobicy_api":
        items = raw.get("jobs", []) if isinstance(raw, dict) else []
    elif kind == "remotejobs_api":
        items = raw.get("data", []) if isinstance(raw, dict) else []
    elif kind == "remoteok_json":
        items = raw if isinstance(raw, list) else []
        items = [item for item in items if isinstance(item, dict) and item.get("position")]
    elif kind == "greenhouse":
        items = raw.get("jobs", []) if isinstance(raw, dict) else []
    elif kind == "lever":
        items = raw if isinstance(raw, list) else []
    elif kind == "smartrecruiters":
        items = raw.get("content", []) if isinstance(raw, dict) else []
    result = []
    for item in items:
        if not isinstance(item, dict):
            continue
        job = _normalize_api_job(kind, source, item, settings)
        if job:
            result.append(job)
    return result


def _normalize_api_job(
    kind: str,
    source: dict[str, Any],
    item: dict[str, Any],
    settings: Settings,
) -> NormalizedJob | None:
    if kind == "jobicy_api":
        title = item.get("jobTitle") or item.get("title")
        company = item.get("companyName") or item.get("company")
        description = item.get("jobDescription") or item.get("description")
        location = item.get("jobGeo") or item.get("location")
        url = item.get("url") or item.get("jobUrl")
        ext = item.get("id") or item.get("jobSlug") or url
        posted = item.get("pubDate") or item.get("datePosted")
        employment = item.get("jobType") or item.get("employmentType")
        salary_min, salary_max = _number(item.get("salaryMin")), _number(item.get("salaryMax"))
        currency = item.get("salaryCurrency") or ""
        period = item.get("salaryPeriod") or ""
    elif kind == "remotejobs_api":
        title = item.get("title")
        company_obj = item.get("company") or {}
        company = company_obj.get("name", "") if isinstance(company_obj, dict) else company_obj
        description = item.get("description") or ""
        location = item.get("location") or ""
        url = item.get("url") or item.get("apply_url")
        ext = item.get("id") or url
        posted = item.get("posted_at")
        employment = item.get("type") or ""
        salary_min, salary_max = _number(item.get("salary_min")), _number(item.get("salary_max"))
        salary_text = str(item.get("salary_text") or "")
        currency = item.get("salary_currency") or _salary_currency_from_text(salary_text)
        if not currency:
            salary_min = salary_max = None
        period = item.get("salary_period") or ""
    elif kind == "remoteok_json":
        title = item.get("position")
        company = item.get("company")
        description = item.get("description") or item.get("apply_url") or ""
        location = item.get("location") or "Remote"
        url = item.get("url") or item.get("apply_url")
        ext = item.get("id") or url
        posted = item.get("date") or item.get("created_at")
        employment = item.get("employment_type") or ""
        salary_min, salary_max = _number(item.get("salary_min")), _number(item.get("salary_max"))
        currency, period = item.get("salary_currency") or "", item.get("salary_period") or ""
    elif kind == "greenhouse":
        title = item.get("title")
        company = (source.get("config") or {}).get("company") or source.get("name")
        description = item.get("content") or ""
        location = (item.get("location") or {}).get("name", "")
        url = item.get("absolute_url")
        ext = item.get("id") or url
        posted = item.get("updated_at") or item.get("created_at")
        employment = item.get("employment_type") or ""
        salary_min = salary_max = None
        currency = period = ""
    elif kind == "lever":
        categories = item.get("categories") or {}
        title = item.get("text")
        company = (source.get("config") or {}).get("company") or source.get("name")
        description = item.get("descriptionPlain") or item.get("description") or ""
        location = categories.get("location", "")
        url = item.get("hostedUrl") or item.get("applyUrl")
        ext = item.get("id") or url
        posted = item.get("createdAt") or item.get("updatedAt")
        employment = categories.get("commitment") or ""
        salary_min = salary_max = None
        currency = period = ""
    else:
        company = (source.get("config") or {}).get("company") or source.get("name")
        title = item.get("name")
        description = item.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "")
        location_obj = item.get("location") or {}
        location = ", ".join(
            str(value) for value in (location_obj.get("city"), location_obj.get("region"), location_obj.get("country"))
            if value
        )
        url = item.get("ref") or item.get("applyUrl")
        ext = item.get("id") or url
        posted = item.get("releasedDate")
        employment = item.get("typeOfEmployment", {}).get("label", "")
        salary_min = salary_max = None
        currency = period = ""

    safe_url = canonical_url(str(url or ""))
    if not title or not safe_url:
        return None
    description_text = plain_text(description, settings.max_job_description_chars)
    raw_location = plain_text(location, 1_000)
    return NormalizedJob(
        source_id=str(source["id"]),
        source_name=str(source["name"]),
        external_id=str(ext or safe_url)[:300],
        title=plain_text(title, 300),
        company=plain_text(company, 250),
        description=description_text,
        source_url=safe_url,
        canonical_url=safe_url,
        location_raw=raw_location,
        workplace_type=infer_workplace(raw_location, description_text),
        employment_type=_normalize_employment(employment),
        visa_sponsorship=infer_visa_sponsorship(description_text),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=str(currency or "").upper()[:8],
        salary_period=str(period or "")[:40],
        posted_at=parse_date(posted),
        eligibility_status="unknown",
        source_credit=str(source.get("attribution") or source["name"]),
    )


def _fetch_remote_first(
    source: dict[str, Any],
    criteria: SearchCriteria,
    settings: Settings,
    database_path,
) -> FetchOutcome:
    roles = _role_slugs(criteria.roles or str((source.get("config") or {}).get("profile_roles", "")))
    if not roles:
        return FetchOutcome(
            message="Add one or more target roles to search this role-specific RSS source.",
            skipped=True,
        )
    jobs: list[NormalizedJob] = []
    checked = 0
    hosts = {"remotefirstjobs.com"}
    due_roles = [
        role_slug for role_slug in roles[:4]
        if role_feed_due(database_path, str(source["id"]), role_slug, int(source.get("interval_seconds") or 21_600))
    ]
    if not due_roles:
        return FetchOutcome(
            message="The selected role feeds are still inside their refresh interval.",
            skipped=True,
        )
    for index, role_slug in enumerate(due_roles):
        if index:
            time.sleep(2.0)
        url = f"https://remotefirstjobs.com/rss/jobs/{quote(role_slug, safe='')}.rss"
        try:
            payload = _fetch_bytes(url, hosts, settings)
        except Exception:
            record_role_feed_check(database_path, str(source["id"]), role_slug)
            raise
        record_role_feed_check(database_path, str(source["id"]), role_slug)
        jobs.extend(_parse_rss_feed(source, payload, settings))
        checked += 1
    return FetchOutcome(jobs=jobs, checked=checked, message=f"Retrieved {len(jobs)} role-feed records.")


def _fetch_remotejobs(
    source: dict[str, Any],
    criteria: SearchCriteria,
    settings: Settings,
    database_path,
) -> FetchOutcome:
    queries = _role_queries(criteria.roles)
    if not queries:
        queries = [""]
    interval = int(source.get("interval_seconds") or 86_400)
    source_id = str(source["id"])
    query_keys = [(query, query or "latest-50") for query in queries[:4]]
    due_queries = [
        (query, query_key)
        for query, query_key in query_keys
        if role_feed_due(database_path, source_id, query_key, interval)
    ]
    if not due_queries:
        return FetchOutcome(
            message="The selected RemoteJobs.org queries are still inside their daily refresh interval.",
            skipped=True,
        )

    endpoint = str(source.get("endpoint") or "https://remotejobs.org/api/v1/jobs")
    allowed_hosts = SOURCE_HOSTS["remotejobs_api"]
    if not _url_is_allowed(endpoint, allowed_hosts):
        raise SourceFetchError("The source endpoint is outside its registered host.", blocked=True)

    jobs: list[NormalizedJob] = []
    checked = 0
    for index, (query, query_key) in enumerate(due_queries):
        if index:
            time.sleep(2.0)
        params = {"limit": 50, "offset": 0}
        if query:
            params["q"] = query
        separator = "&" if "?" in endpoint else "?"
        url = f"{endpoint}{separator}{urlencode(params)}"
        try:
            payload = _fetch_bytes(url, allowed_hosts, settings)
            raw = json.loads(payload.decode("utf-8-sig"))
            jobs.extend(_parse_json_feed("remotejobs_api", source, raw, settings))
        except Exception:
            record_role_feed_check(database_path, source_id, query_key)
            raise
        record_role_feed_check(database_path, source_id, query_key)
        checked += 1
    return FetchOutcome(
        jobs=jobs,
        checked=checked,
        message=f"Retrieved {len(jobs)} RemoteJobs.org records across {checked} query pages.",
    )


def _role_queries(raw_roles: str) -> list[str]:
    queries: list[str] = []
    for raw in re.split(r"[,;\n]+", raw_roles or ""):
        query = " ".join(re.sub(r"[\r\t]+", " ", raw).split())[:80]
        if len(query) >= 2 and query.casefold() not in {value.casefold() for value in queries}:
            queries.append(query)
    return queries


def _role_slugs(raw_roles: str) -> list[str]:
    slugs = []
    for role in re.split(r"[,;\n]+", raw_roles or ""):
        cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", role.strip().casefold()).strip("-")
        if len(cleaned) >= 3 and cleaned not in slugs:
            slugs.append(cleaned[:80])
    return slugs


def _parse_rss_feed(
    source: dict[str, Any],
    payload: bytes,
    settings: Settings,
) -> list[NormalizedJob]:
    root = ET.fromstring(payload)
    items = []
    for node in root.iter():
        if _xml_local_name(node.tag) in {"item", "entry"}:
            item: dict[str, Any] = {}
            for child in list(node):
                name = _xml_local_name(child.tag)
                if name == "link":
                    item[name] = child.attrib.get("href") or child.text or item.get(name, "")
                elif name in {"title", "description", "summary", "content", "pubdate", "published", "updated", "guid", "id", "category", "company", "location"}:
                    value = child.attrib.get("term") or "".join(child.itertext())
                    if name in item and name == "category":
                        item[name] = f"{item[name]}, {value}"
                    else:
                        item[name] = value
            items.append(item)
    result = []
    for item in items:
        title = plain_text(item.get("title"), 300)
        link = canonical_url(str(item.get("link") or item.get("guid") or item.get("id") or ""))
        if not title or not link:
            continue
        content = item.get("description") or item.get("summary") or item.get("content") or ""
        description = plain_text(content, settings.max_job_description_chars)
        company = plain_text(item.get("company") or "", 250)
        location = plain_text(item.get("location") or ("Remote" if "remote" in title.casefold() else ""), 1_000)
        posted = parse_date(
            item.get("pubdate") or item.get("published") or item.get("updated") or ""
        )
        result.append(
            NormalizedJob(
                source_id=str(source["id"]),
                source_name=str(source["name"]),
                external_id=str(item.get("guid") or item.get("id") or link)[:300],
                title=title,
                company=company,
                description=description,
                source_url=link,
                canonical_url=link,
                location_raw=location,
                workplace_type=infer_workplace(location, description),
                visa_sponsorship=infer_visa_sponsorship(description),
                posted_at=posted,
                source_credit=str(source.get("attribution") or source["name"]),
            )
        )
    return result


def _xml_local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].casefold()


def _number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return number if 0 <= number <= 1_000_000_000 else None


def _salary_currency_from_text(value: str) -> str:
    text = value.upper()
    for marker, currency in (
        ("USD", "USD"),
        ("EUR", "EUR"),
        ("GBP", "GBP"),
        ("CAD", "CAD"),
        ("AUD", "AUD"),
    ):
        if marker in text:
            return currency
    for marker, currency in (
        ("CA$", "CAD"),
        ("C$", "CAD"),
        ("AU$", "AUD"),
        ("A$", "AUD"),
        ("US$", "USD"),
        ("€", "EUR"),
        ("£", "GBP"),
    ):
        if marker in value:
            return currency
    return ""


def _normalize_employment(value: Any) -> str:
    text = plain_text(value, 80).casefold()
    if not text:
        return "unknown"
    if "full" in text:
        return "full-time"
    if "part" in text:
        return "part-time"
    if "contract" in text or "freelance" in text:
        return "contract"
    if "intern" in text:
        return "internship"
    if "temporary" in text or "fixed" in text:
        return "temporary"
    return text[:40]


def infer_visa_sponsorship(description: str) -> str:
    text = plain_text(description, 20_000).casefold()
    negative = (
        r"\bno visa sponsorship\b",
        r"\bvisa sponsorship (?:is )?not available\b",
        r"\b(?:cannot|can't|unable to|will not|won't) sponsor\b",
        r"\bnot able to sponsor\b",
        r"\bwithout (?:the )?need for (?:visa )?sponsorship\b",
        r"\bmust (?:already )?be authorized to work\b",
    )
    if any(re.search(pattern, text) for pattern in negative):
        return "no"
    positive = (
        r"\bvisa sponsorship (?:is )?(?:available|provided|offered)\b",
        r"\b(?:we|employer) (?:will|can|may) sponsor\b",
        r"\bsponsorship (?:is )?(?:available|provided|offered)\b",
        r"\bwill consider sponsoring\b",
    )
    if any(re.search(pattern, text) for pattern in positive):
        return "yes"
    return "unknown"


def validate_career_url(url: str) -> tuple[bool, str]:
    """Reject malformed, local, or non-public crawl targets before they enter Scrapling."""
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
        if parts.scheme != "https" or not host or parts.username or parts.password:
            return False, "Use an HTTPS careers or public job URL without embedded credentials."
        if parts.port not in (None, 443):
            return False, "Only standard HTTPS port 443 is supported."
        addresses = {ipaddress.ip_address(info[4][0]) for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
        if not addresses or any(not address.is_global for address in addresses):
            return False, "The careers URL must resolve only to public internet addresses."
        return True, ""
    except (ValueError, OSError):
        return False, "The careers hostname could not be verified as a public address."


def crawl_career_page(source: dict[str, Any], settings: Settings) -> FetchOutcome:
    if source.get("state") != "approved" or not source.get("enabled"):
        return FetchOutcome(message="The career page has not been approved.", skipped=True)
    config = source.get("config") or {}
    start_url = str(config.get("career_url") or source.get("endpoint") or "")
    valid, message = validate_career_url(start_url)
    if not valid:
        raise SourceFetchError(message, blocked=True)
    host = urlsplit(start_url).hostname or ""
    try:
        from scrapling.fetchers import FetcherSession
        from scrapling.spiders import Request as ScraplingRequest
        from scrapling.spiders import Spider
    except ImportError as exc:
        raise SourceFetchError("Scrapling is unavailable. Install the project dependencies.") from exc

    class BoundedCareerSpider(Spider):
        name = "clue_ai_public_careers"
        robots_txt_obey = True
        allowed_domains: ClassVar[set[str]] = {host}
        concurrent_requests = 4
        concurrent_requests_per_domain = 1
        download_delay = 2.0
        max_blocked_retries = 0
        start_urls: ClassVar[list[str]] = []
        user_agent: ClassVar[str] = settings.crawler_user_agent

        def __init__(self) -> None:
            super().__init__()
            self.start_urls = [start_url]
            self.allowed_domains = {host}
            self.hit_block = False
            self.page_limit = 25

        def configure_sessions(self, manager) -> None:
            manager.add(
                "ordinary",
                FetcherSession(
                    impersonate=None,
                    stealthy_headers=False,
                    timeout=settings.network_timeout_seconds,
                    headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
                    retries=0,
                    retry_delay=0,
                    follow_redirects=False,
                    verify=True,
                ),
            )

        async def start_requests(self):
            yield ScraplingRequest(
                self.start_urls[0],
                sid=self._session_manager.default_session_id,
                callback=self.parse,
                headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
            )

        async def is_blocked(self, response):
            status = getattr(response, "status", 0)
            body = getattr(response, "body", b"")
            if status in {401, 403, 429} or _looks_blocked(body):
                self.hit_block = True
                return True
            return False

        async def parse(self, response):
            status = getattr(response, "status", 0)
            body = getattr(response, "body", b"")
            response_host = (urlsplit(getattr(response, "url", "")).hostname or "").lower()
            if response_host != host:
                return
            if status in {401, 403, 429} or _looks_blocked(body):
                self.hit_block = True
                return
            if len(body) > settings.max_page_bytes:
                return
            entries = _extract_jsonld_job_postings(response, source, settings)
            for entry in entries:
                yield entry
            if entries:
                return
            seen: set[str] = set()
            for href in response.css("a::attr(href)").getall():
                absolute = urljoin(response.url, str(href))
                parts = urlsplit(absolute)
                if parts.scheme != "https" or (parts.hostname or "").lower() != host:
                    continue
                path = parts.path.casefold()
                if not re.search(r"/(?:careers?|jobs?|positions?|vacancies|openings?)/[^/]+", path):
                    continue
                normalized = canonical_url(absolute)
                if not normalized or normalized in seen or normalized == canonical_url(start_url):
                    continue
                seen.add(normalized)
                if len(seen) >= self.page_limit:
                    break
                yield response.follow(
                    normalized,
                    callback=self.parse_job_page,
                    headers={"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"},
                )

        async def parse_job_page(self, response):
            status = getattr(response, "status", 0)
            body = getattr(response, "body", b"")
            response_host = (urlsplit(getattr(response, "url", "")).hostname or "").lower()
            if response_host != host:
                return
            if status in {401, 403, 429} or _looks_blocked(body):
                self.hit_block = True
                return
            if len(body) > settings.max_page_bytes:
                return
            structured = _extract_jsonld_job_postings(response, source, settings)
            for entry in structured:
                yield entry
            if not structured:
                entry = _extract_html_job_posting(response, source, settings)
                if entry:
                    yield entry

    try:
        spider = BoundedCareerSpider()
        result = spider.start()
    except Exception as exc:
        raise SourceFetchError(f"Scrapling crawl failed: {type(exc).__name__}.") from exc
    stats = getattr(result, "stats", None)
    status_counts = getattr(stats, "response_status_count", {}) if stats else {}
    blocked_status = any(
        key in status_counts for key in ("status_401", "status_403", "status_429")
    )
    if blocked_status or getattr(spider, "hit_block", False):
        return FetchOutcome(message="The source returned an access or bot challenge.", blocked=True)
    jobs = []
    for item in getattr(result, "items", []):
        if isinstance(item, dict):
            job = _normalize_crawled_job(source, item, settings)
            if job:
                jobs.append(job)
    return FetchOutcome(
        jobs=jobs,
        checked=int(getattr(stats, "requests_count", 1) or 1) if stats else 1,
        message=f"Retrieved {len(jobs)} career-page listings.",
    )


def _extract_jsonld_job_postings(response, source: dict[str, Any], settings: Settings) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for raw in response.css('script[type="application/ld+json"]::text').getall():
        try:
            data = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            item = stack.pop()
            if not isinstance(item, dict):
                continue
            if isinstance(item.get("@graph"), list):
                stack.extend(item["@graph"])
            kind = item.get("@type", "")
            types = kind if isinstance(kind, list) else [kind]
            if not any(str(value).rstrip("/").rsplit("/", 1)[-1] == "JobPosting" for value in types):
                continue
            item.setdefault("url", response.url)
            item.setdefault("_response_url", response.url)
            item.setdefault("_source_id", source["id"])
            item.setdefault("_source_name", source["name"])
            entries.append(item)
    return entries


def _normalize_crawled_job(
    source: dict[str, Any], item: dict[str, Any], settings: Settings
) -> NormalizedJob | None:
    org = item.get("hiringOrganization") or {}
    title = item.get("title")
    company = org.get("name") if isinstance(org, dict) else ""
    url = canonical_url(str(item.get("url") or item.get("_response_url") or ""))
    if not title or not url:
        return None
    location_obj = item.get("jobLocation") or []
    if not isinstance(location_obj, list):
        location_obj = [location_obj]
    locations = []
    for location in location_obj:
        address = (location or {}).get("address", {}) if isinstance(location, dict) else {}
        if isinstance(address, dict):
            locations.append(", ".join(
                str(value) for value in (
                    address.get("addressLocality"), address.get("addressRegion"),
                    address.get("addressCountry")
                ) if value
            ))
    restrictions = item.get("applicantLocationRequirements") or item.get("eligibleRegion") or []
    if not isinstance(restrictions, list):
        restrictions = [restrictions]
    for restriction in restrictions:
        if isinstance(restriction, dict):
            locations.append(str(restriction.get("name") or restriction.get("addressCountry") or ""))
        elif restriction:
            locations.append(str(restriction))
    raw_location = plain_text("; ".join(part for part in locations if part), 1_000)
    description = plain_text(item.get("description") or "", settings.max_job_description_chars)
    workplace = "remote" if str(item.get("jobLocationType") or "").upper() == "TELECOMMUTE" else infer_workplace(raw_location, description)
    employment = item.get("employmentType") or ""
    base_salary = item.get("baseSalary") or {}
    if isinstance(base_salary, dict):
        salary_value = base_salary.get("value") or {}
        if not isinstance(salary_value, dict):
            salary_value = {"value": salary_value}
        salary_min = _number(salary_value.get("minValue") or salary_value.get("value"))
        salary_max = _number(salary_value.get("maxValue") or salary_value.get("value"))
        salary_currency = str(base_salary.get("currency") or "")
        salary_period = str(salary_value.get("unitText") or "")
    else:
        salary_min = salary_max = None
        salary_currency = salary_period = ""
    return NormalizedJob(
        source_id=str(source["id"]),
        source_name=str(source["name"]),
        external_id=str(item.get("identifier") or url)[:300],
        title=plain_text(title, 300),
        company=plain_text(company, 250),
        description=description,
        source_url=url,
        canonical_url=url,
        location_raw=raw_location,
        workplace_type=workplace,
        employment_type=_normalize_employment(employment),
        visa_sponsorship=infer_visa_sponsorship(description),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency[:8].upper(),
        salary_period=salary_period[:40],
        posted_at=parse_date(item.get("datePosted")),
        valid_through=parse_date(item.get("validThrough")),
        source_credit=str(source.get("attribution") or source["name"]),
    )


def _extract_html_job_posting(response, source: dict[str, Any], settings: Settings) -> dict[str, Any] | None:
    """Bounded fallback for a linked job detail page without JobPosting JSON-LD."""
    title = response.css("h1::text").get() or response.css("title::text").get()
    title = plain_text(title, 300)
    normalized_title = re.sub(r"\s*[|·–—-]\s*[^|·–—-]+$", "", title).strip()
    if not normalized_title or normalized_title.casefold() in {
        "careers", "jobs", "open positions", "open roles", "join our team", "work with us"
    }:
        return None

    location = ""
    for selector in (
        "[itemprop='jobLocation']::text",
        ".job-location::text",
        ".location::text",
        "[data-testid*='location']::text",
    ):
        values = response.css(selector).getall()
        location = plain_text(" ".join(str(value) for value in values), 1_000)
        if location:
            break

    content = response.css("article").get() or response.css("main").get()
    if not content:
        return None
    description = plain_text(content, settings.max_job_description_chars)
    if len(description) < 80:
        return None
    date_posted = (
        response.css("time[datetime]::attr(datetime)").get()
        or response.css("meta[property='article:published_time']::attr(content)").get()
        or response.css("meta[name='date']::attr(content)").get()
        or ""
    )
    return {
        "title": normalized_title,
        "hiringOrganization": {"name": (source.get("config") or {}).get("company") or source.get("name", "")},
        "description": description,
        "jobLocation": {"address": {"addressLocality": location}} if location else {},
        "datePosted": date_posted,
        "url": getattr(response, "url", ""),
        "_response_url": getattr(response, "url", ""),
    }
