from __future__ import annotations

import ipaddress
import json
import logging
import re
import socket
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, ClassVar
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urljoin, urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from clue_ai.config import Settings
from clue_ai.crawl_policy import (
    ROBOTS_TXT_OBEY,
    SCRAPLING_CONCURRENT_REQUESTS,
    SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN,
    SCRAPLING_DOWNLOAD_DELAY_SECONDS,
    STANDALONE_CAREER_PAGE_LIMIT,
)
from clue_ai.domain import NormalizedJob, SearchCriteria
from clue_ai.external_links import is_x_host
from clue_ai.jobs import canonical_url, infer_workplace, parse_date, plain_text
from clue_ai.repository import (
    record_role_feed_check,
    researched_listing_urls,
    role_feed_due,
)


class SourceFetchError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None, blocked: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.blocked = blocked


_CAREER_OR_JOB_PATH = re.compile(
    r"(?i)(?:career|jobs?|positions?|vacanc|opening|roles?|opportunit|"
    r"work[-_]?with[-_]?us|join[-_]?us|our[-_]?team)"
)
_JOB_DETAIL_PATH = re.compile(
    r"(?i)/(?:jobs?|job[-_]?openings?|positions?|vacancies|openings?|roles?|opportunities)/[^/]+"
)


@dataclass
class FetchOutcome:
    jobs: list[NormalizedJob] = field(default_factory=list)
    checked: int = 0
    message: str = ""
    blocked: bool = False
    skipped: bool = False
    response_bytes: int = 0
    raw_records: int = 0
    parse_failures: int = 0
    not_found_count: int = 0
    status_counts: dict[str, int] = field(default_factory=dict)


SOURCE_HOSTS = {
    "jobicy_api": {"jobicy.com"},
    "remotejobs_api": {"remotejobs.org"},
    "remoteok_json": {"remoteok.com"},
    "weworkremotely_rss": {"weworkremotely.com"},
    "himalayas_api": {"himalayas.app"},
    "remotive_api": {"remotive.com"},
    "workingnomads_api": {"workingnomads.com", "www.workingnomads.com"},
    "remote_first_rss": {"remotefirstjobs.com"},
    "startup_rss": {"startup.jobs"},
    "greenhouse": {"boards-api.greenhouse.io"},
    "lever": {"api.lever.co", "api.eu.lever.co"},
    "smartrecruiters": {"api.smartrecruiters.com"},
    "ashby": {"api.ashbyhq.com"},
}


def fetch_source(
    source: dict[str, Any],
    criteria: SearchCriteria,
    settings: Settings,
    database_path=None,
) -> FetchOutcome:
    """Fetch only an enabled, already-approved source supplied by the registry."""
    if source.get("kind") == "manual_x":
        return FetchOutcome(
            message="X is a manual-only lead source and is never fetched.", skipped=True
        )
    if source.get("kind") == "manual_board":
        return FetchOutcome(
            message="This board is available as a manual link-out and is never fetched by Clue.",
            skipped=True,
        )
    if source.get("state") != "approved" or not source.get("enabled"):
        return FetchOutcome(message="This source is not approved and enabled.", skipped=True)
    kind = str(source.get("kind") or "")
    if kind == "justremote_scrapling":
        from clue_ai.scrapling_boards import crawl_justremote

        reviewed_urls = (
            set()
            if criteria.include_reviewed or database_path is None
            else researched_listing_urls(database_path)
        )
        return crawl_justremote(source, settings, reviewed_urls)
    if kind == "techeurope_scrapling":
        from clue_ai.techeurope_scrapling import crawl_techeurope

        return crawl_techeurope(source, settings)
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
    if kind == "himalayas_api":
        return _fetch_himalayas(source, criteria, settings)
    if kind == "smartrecruiters":
        return _fetch_smartrecruiters(source, settings)

    url = _connector_url(source)
    allowed_hosts = _allowed_hosts(source, kind, url)
    if not _url_is_allowed(url, allowed_hosts):
        raise SourceFetchError("The source endpoint is outside its registered host.", blocked=True)
    payload = _fetch_bytes(url, allowed_hosts, settings)
    try:
        if kind in {
            "jobicy_api",
            "remotejobs_api",
            "remoteok_json",
            "remotive_api",
            "workingnomads_api",
            "greenhouse",
            "lever",
            "ashby",
        }:
            raw = json.loads(payload.decode("utf-8-sig"))
            raw_records = _raw_json_record_count(kind, raw)
            jobs = _parse_json_feed(kind, source, raw, settings)
        else:
            raw_records = _raw_rss_record_count(payload)
            jobs = _parse_rss_feed(source, payload, settings)
    except (UnicodeDecodeError, json.JSONDecodeError, ET.ParseError) as exc:
        raise SourceFetchError("The listing feed could not be parsed.") from exc
    return FetchOutcome(
        jobs=jobs,
        checked=1,
        message=f"Retrieved {len(jobs)} listing records.",
        response_bytes=len(payload),
        raw_records=raw_records,
        parse_failures=max(0, raw_records - len(jobs)),
        status_counts={"status_200": 1},
    )


def _fetch_himalayas(
    source: dict[str, Any],
    criteria: SearchCriteria,
    settings: Settings,
    *,
    max_pages: int = 25,
) -> FetchOutcome:
    """Search alternatives independently within the existing total daily page cap."""
    page_budget = max(1, min(25, max_pages))
    queries = (_role_queries(criteria.roles) or [""])[:min(4, page_budget)]
    combined = FetchOutcome()
    for index, query in enumerate(queries):
        if index:
            time.sleep(1.0)
        budget = page_budget // len(queries) + (index < page_budget % len(queries))
        outcome = _fetch_himalayas_query(source, replace(criteria, roles=query), settings, max_pages=budget)
        combined.jobs.extend(outcome.jobs)
        combined.checked += outcome.checked
        combined.response_bytes += outcome.response_bytes
        combined.raw_records += outcome.raw_records
        combined.parse_failures += outcome.parse_failures
        for status, count in outcome.status_counts.items():
            combined.status_counts[status] = combined.status_counts.get(status, 0) + count
        if outcome.blocked:
            combined.blocked = True
            combined.message = outcome.message
            return combined
    combined.message = (
        f"Retrieved {len(combined.jobs)} Himalayas listings from {combined.checked} pages "
        f"across {len(queries)} alternative AI role queries; total cap {page_budget} pages."
    )
    return combined


def _fetch_himalayas_query(
    source: dict[str, Any],
    criteria: SearchCriteria,
    settings: Settings,
    *,
    max_pages: int = 25,
) -> FetchOutcome:
    """Search Himalayas for the requested role/location and walk a bounded number of pages."""
    endpoint = str(source.get("endpoint") or "https://himalayas.app/jobs/api")
    allowed_hosts = SOURCE_HOSTS["himalayas_api"]
    page_budget = max(1, min(25, max_pages))
    endpoint_parts = urlsplit(endpoint)
    path = endpoint_parts.path.rstrip("/")
    if path.endswith("/jobs/api"):
        path = f"{path}/search"
    query = criteria.roles.strip()[:500]
    country = _himalayas_country(criteria.work_from)
    jobs: list[NormalizedJob] = []
    response_bytes = 0
    raw_records = 0
    checked = 0
    truncated = False
    status_counts: dict[str, int] = {}

    for page in range(1, page_budget + 1):
        if page > 1:
            # The API refreshes daily and warns that excess requests can be rate-limited.
            time.sleep(1.0)
        params = {
            key: value
            for key, value in parse_qsl(endpoint_parts.query, keep_blank_values=True)
            if key not in {"cursor", "offset", "limit", "page", "q", "country"}
        }
        if query:
            params["q"] = query
        if country:
            params["country"] = country
        params["page"] = str(page)
        page_url = urlunsplit(
            (endpoint_parts.scheme, endpoint_parts.netloc, path, urlencode(params), "")
        )
        try:
            payload = _fetch_bytes(page_url, allowed_hosts, settings)
        except SourceFetchError as exc:
            if exc.status_code == 429:
                status_counts["status_429"] = status_counts.get("status_429", 0) + 1
                return FetchOutcome(
                    jobs=jobs,
                    checked=checked + 1,
                    message="Himalayas rate-limited the role/location search; saved listings from completed pages and paused this source.",
                    blocked=True,
                    response_bytes=response_bytes,
                    raw_records=raw_records,
                    status_counts=status_counts,
                )
            raise
        checked += 1
        status_counts["status_200"] = status_counts.get("status_200", 0) + 1
        response_bytes += len(payload)
        try:
            raw = json.loads(payload.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceFetchError("The Himalayas API response could not be parsed.") from exc
        if not isinstance(raw, dict) or not isinstance(raw.get("jobs"), list):
            raise SourceFetchError("The Himalayas API returned an unexpected response shape.")
        page_records = _raw_json_record_count("himalayas_api", raw)
        raw_records += page_records
        jobs.extend(_parse_json_feed("himalayas_api", source, raw, settings))
        try:
            total_count = max(0, int(raw.get("totalCount") or 0))
        except (TypeError, ValueError):
            total_count = 0
        if total_count:
            if page * 20 >= total_count:
                break
        elif page_records < 20:
            break
        if page == page_budget:
            truncated = True

    message = (
        f"Retrieved {len(jobs)} Himalayas listings from {checked} role/location search page(s)."
        if not truncated
        else f"Retrieved {len(jobs)} Himalayas listings; stopped at the {page_budget}-page daily cap."
    )
    return FetchOutcome(
        jobs=jobs,
        checked=checked,
        message=message,
        response_bytes=response_bytes,
        raw_records=raw_records,
        parse_failures=max(0, raw_records - len(jobs)),
        status_counts=status_counts,
    )


def _himalayas_country(work_from: str) -> str:
    """Return a country query when the user's work location names a country."""
    value = str(work_from or "").strip()
    if "," in value:
        value = value.rsplit(",", 1)[-1].strip()
    if value.casefold() in {
        "",
        "anywhere",
        "worldwide",
        "global",
        "europe",
        "european union",
        "eu",
        "emea",
        "remote",
    }:
        return ""
    return value[:100]


def _fetch_smartrecruiters(
    source: dict[str, Any], settings: Settings, *, max_pages: int = 5
) -> FetchOutcome:
    """Read up to five pages from SmartRecruiters' documented public postings route."""
    company_id = quote(str((source.get("config") or {}).get("company_id") or ""), safe="")
    if not company_id:
        raise SourceFetchError("The linked SmartRecruiters board has no company identifier.")
    allowed_hosts = SOURCE_HOSTS["smartrecruiters"]
    jobs: list[NormalizedJob] = []
    total_bytes = 0
    raw_records = 0
    checked = 0
    for page in range(max(1, min(max_pages, 5))):
        if page:
            time.sleep(2.0)
        offset = page * 100
        url = (
            f"https://api.smartrecruiters.com/v1/companies/{company_id}"
            f"/postings?limit=100&offset={offset}"
        )
        payload = _fetch_bytes(url, allowed_hosts, settings)
        checked += 1
        total_bytes += len(payload)
        try:
            raw = json.loads(payload.decode("utf-8-sig"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SourceFetchError(
                "The SmartRecruiters public listing response could not be parsed."
            ) from exc
        page_count = _raw_json_record_count("smartrecruiters", raw)
        raw_records += page_count
        jobs.extend(_parse_json_feed("smartrecruiters", source, raw, settings))
        total = int(raw.get("totalFound") or raw.get("total") or 0) if isinstance(raw, dict) else 0
        if page_count < 100 or (total and offset + page_count >= total):
            break
    return FetchOutcome(
        jobs=jobs,
        checked=checked,
        message=f"Retrieved {len(jobs)} SmartRecruiters listing records.",
        response_bytes=total_bytes,
        raw_records=raw_records,
        parse_failures=max(0, raw_records - len(jobs)),
        status_counts={"status_200": checked},
    )


def _connector_url(source: dict[str, Any]) -> str:
    kind = source["kind"]
    config = source.get("config") or {}
    if kind == "greenhouse":
        token = quote(str(config.get("board_token") or ""), safe="")
        return f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    if kind == "lever":
        site = quote(str(config.get("site") or ""), safe="")
        region = str(config.get("region") or "global").strip().casefold()
        if region not in {"global", "eu"}:
            raise SourceFetchError("Choose a supported Lever site region.")
        host = "api.eu.lever.co" if region == "eu" else "api.lever.co"
        return f"https://{host}/v0/postings/{site}?mode=json"
    if kind == "smartrecruiters":
        company_id = quote(str(config.get("company_id") or ""), safe="")
        return (
            f"https://api.smartrecruiters.com/v1/companies/{company_id}/postings?limit=100&offset=0"
        )
    if kind == "ashby":
        board_name = quote(str(config.get("board_name") or ""), safe="")
        return f"https://api.ashbyhq.com/posting-api/job-board/{board_name}"
    return str(source.get("endpoint") or "")


def _allowed_hosts(source: dict[str, Any], kind: str, url: str) -> set[str]:
    if kind == "lever":
        region = str((source.get("config") or {}).get("region") or "global").strip().casefold()
        if region not in {"global", "eu"}:
            return set()
        return {"api.eu.lever.co" if region == "eu" else "api.lever.co"}
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
                raise SourceFetchError(
                    "The source returned a bot or access challenge.", blocked=True
                )
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
        "verify you are human",
        "access denied",
        "unusual traffic",
        "automated requests are not allowed",
        "automated request detected",
        "bot detection",
        "complete the captcha to continue",
        "captcha verification required",
        "please complete the security check",
        "cf-chl-",
        "cloudflare ray id",
    )
    return any(marker in sample for marker in markers)


def _raw_json_record_count(kind: str, raw: Any) -> int:
    if kind in {
        "jobicy_api",
        "greenhouse",
        "ashby",
        "remotive_api",
        "himalayas_api",
    }:
        items = raw.get("jobs", []) if isinstance(raw, dict) else []
        if kind == "ashby":
            items = [
                item
                for item in items
                if isinstance(item, dict) and item.get("isListed") is not False
            ]
    elif kind == "remotejobs_api":
        items = raw.get("data", []) if isinstance(raw, dict) else []
    elif kind == "remoteok_json":
        items = raw if isinstance(raw, list) else []
        items = [item for item in items if isinstance(item, dict) and item.get("position")]
    elif kind == "workingnomads_api":
        items = raw if isinstance(raw, list) else raw.get("jobs", []) if isinstance(raw, dict) else []
    elif kind == "lever":
        items = raw if isinstance(raw, list) else []
    elif kind == "smartrecruiters":
        items = raw.get("content", []) if isinstance(raw, dict) else []
    else:
        items = []
    return sum(isinstance(item, dict) for item in items)


def _raw_rss_record_count(payload: bytes) -> int:
    root = ET.fromstring(payload)
    return len(root.findall(".//item")) + len(root.findall(".//{*}entry"))


def _parse_json_feed(
    kind: str,
    source: dict[str, Any],
    raw: Any,
    settings: Settings,
) -> list[NormalizedJob]:
    items: list[dict[str, Any]] = []
    if kind in {"jobicy_api", "remotive_api", "himalayas_api"}:
        items = raw.get("jobs", []) if isinstance(raw, dict) else []
    elif kind == "ashby":
        items = raw.get("jobs", []) if isinstance(raw, dict) else []
        items = [
            item for item in items if isinstance(item, dict) and item.get("isListed") is not False
        ]
    elif kind == "remotejobs_api":
        items = raw.get("data", []) if isinstance(raw, dict) else []
    elif kind == "remoteok_json":
        items = raw if isinstance(raw, list) else []
        items = [item for item in items if isinstance(item, dict) and item.get("position")]
    elif kind == "workingnomads_api":
        items = raw if isinstance(raw, list) else raw.get("jobs", []) if isinstance(raw, dict) else []
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
    valid_through = ""
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
    elif kind == "remotive_api":
        title = item.get("title")
        company = item.get("company_name") or ""
        description = item.get("description") or ""
        tags = item.get("tags") or []
        if isinstance(tags, list) and tags:
            description = f"{description}\n\nTags: {', '.join(str(tag) for tag in tags if tag)}"
        if item.get("category"):
            description = f"{description}\n\nCategory: {item['category']}"
        location = item.get("candidate_required_location") or "Remote"
        url = item.get("url")
        ext = item.get("id") or url
        posted = item.get("publication_date")
        employment = item.get("job_type") or ""
        salary_text = str(item.get("salary") or "")
        salary_min = _number(item.get("salary_min"))
        salary_max = _number(item.get("salary_max"))
        if salary_min is None and salary_max is None:
            salary_min, salary_max = _salary_range_from_text(salary_text)
        currency = item.get("salary_currency") or _salary_currency_from_text(salary_text)
        period = item.get("salary_period") or _salary_period_from_text(salary_text)
    elif kind == "himalayas_api":
        title = item.get("title")
        company = item.get("companyName") or ""
        description = item.get("description") or item.get("excerpt") or ""
        category_values = item.get("categories") or item.get("parentCategories") or []
        seniority_values = item.get("seniority") or []
        if not isinstance(category_values, list):
            category_values = [category_values]
        if not isinstance(seniority_values, list):
            seniority_values = [seniority_values]
        metadata = [
            f"Categories: {', '.join(str(value) for value in category_values if value)}"
            if category_values
            else "",
            f"Seniority: {', '.join(str(value) for value in seniority_values if value)}"
            if seniority_values
            else "",
        ]
        if any(metadata):
            metadata_text = "\n".join(value for value in metadata if value)
            description = f"{description}\n\n{metadata_text}"
        restrictions = item.get("locationRestrictions") or []
        if not isinstance(restrictions, list):
            restrictions = [restrictions]
        location_names = [
            str(value.get("name") or value.get("alpha2") or "")
            if isinstance(value, dict)
            else str(value)
            for value in restrictions
        ]
        location = ", ".join(value for value in location_names if value) or "Worldwide"
        url = item.get("applicationLink")
        ext = item.get("guid") or url
        posted = _source_epoch_date(item.get("pubDate"))
        valid_through = _source_epoch_date(item.get("expiryDate"))
        employment = item.get("employmentType") or ""
        salary_min = _number(item.get("minSalary"))
        salary_max = _number(item.get("maxSalary"))
        currency = item.get("currency") or ""
        period = item.get("salaryPeriod") or "annual"
    elif kind == "workingnomads_api":
        title = item.get("title")
        company = item.get("company_name") or ""
        description = item.get("description") or ""
        tags = item.get("tags") or ""
        if isinstance(tags, list):
            tags = ", ".join(str(tag) for tag in tags if tag)
        if tags:
            description = f"{description}\n\nTags: {tags}"
        location = item.get("location") or "Remote"
        url = item.get("url")
        ext = item.get("id") or url
        posted = item.get("pub_date")
        employment = item.get("type") or ""
        salary_min = _number(item.get("salary_min"))
        salary_max = _number(item.get("salary_max"))
        currency = item.get("salary_currency") or ""
        period = item.get("salary_period") or ""
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
    elif kind == "ashby":
        title = item.get("title")
        company = (source.get("config") or {}).get("company") or source.get("name")
        description = item.get("descriptionPlain") or item.get("descriptionHtml") or ""
        locations = [str(item.get("location") or "")]
        for secondary in item.get("secondaryLocations") or []:
            if not isinstance(secondary, dict):
                continue
            locations.append(str(secondary.get("location") or ""))
            address = secondary.get("address") or {}
            if isinstance(address, dict):
                locations.extend(
                    str(address.get(key) or "")
                    for key in ("addressLocality", "addressRegion", "addressCountry")
                )
        address_value = item.get("address") or {}
        postal = address_value.get("postalAddress") or {} if isinstance(address_value, dict) else {}
        if isinstance(postal, dict):
            locations.extend(
                str(postal.get(key) or "")
                for key in ("addressLocality", "addressRegion", "addressCountry")
            )
        location = ", ".join(value for value in locations if value)
        url = item.get("jobUrl")
        ext = item.get("jobUrl") or url
        posted = item.get("publishedAt")
        employment = item.get("employmentType") or ""
        salary_min = salary_max = None
        currency = period = ""
    else:
        company = (source.get("config") or {}).get("company") or source.get("name")
        title = item.get("name")
        description = (
            item.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text", "")
        )
        location_obj = item.get("location") or {}
        location = ", ".join(
            str(value)
            for value in (
                location_obj.get("city"),
                location_obj.get("region"),
                location_obj.get("country"),
            )
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
    workplace = infer_workplace(raw_location, description_text)
    if kind in {
        "jobicy_api",
        "remoteok_json",
        "weworkremotely_rss",
        "himalayas_api",
        "remotive_api",
        "workingnomads_api",
    } and workplace == "unknown":
        workplace = "remote"
    if kind == "ashby":
        workplace_value = str(item.get("workplaceType") or "").casefold()
        if workplace_value in {"remote", "hybrid", "onsite"}:
            workplace = "on-site" if workplace_value == "onsite" else workplace_value
        elif item.get("isRemote") is True:
            workplace = "remote"
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
        workplace_type=workplace,
        employment_type=_normalize_employment(employment),
        visa_sponsorship=infer_visa_sponsorship(description_text),
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=str(currency or "").upper()[:8],
        salary_period=str(period or "")[:40],
        posted_at=parse_date(posted),
        valid_through=parse_date(valid_through),
        eligibility_status="unknown",
        source_credit=str(source.get("attribution") or source["name"]),
    )


def _fetch_remote_first(
    source: dict[str, Any],
    criteria: SearchCriteria,
    settings: Settings,
    database_path,
) -> FetchOutcome:
    roles = _role_slugs(
        criteria.roles or str((source.get("config") or {}).get("profile_roles", ""))
    )
    if not roles:
        return FetchOutcome(
            message="Add one or more target roles to search this role-specific RSS source.",
            skipped=True,
        )
    jobs: list[NormalizedJob] = []
    checked = 0
    response_bytes = 0
    raw_records = 0
    parse_failures = 0
    hosts = {"remotefirstjobs.com"}
    due_roles = [
        role_slug
        for role_slug in roles[:4]
        if role_feed_due(
            database_path,
            str(source["id"]),
            role_slug,
            int(source.get("interval_seconds") or 21_600),
        )
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
            raw_count = _raw_rss_record_count(payload)
            parsed = _parse_rss_feed(source, payload, settings)
        except Exception:
            record_role_feed_check(
                database_path, str(source["id"]), role_slug, state="error"
            )
            raise
        record_role_feed_check(database_path, str(source["id"]), role_slug)
        jobs.extend(parsed)
        response_bytes += len(payload)
        raw_records += raw_count
        parse_failures += max(0, raw_count - len(parsed))
        checked += 1
    return FetchOutcome(
        jobs=jobs,
        checked=checked,
        message=f"Retrieved {len(jobs)} role-feed records.",
        response_bytes=response_bytes,
        raw_records=raw_records,
        parse_failures=parse_failures,
        status_counts={"status_200": checked},
    )


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
    response_bytes = 0
    raw_records = 0
    parse_failures = 0
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
            raw_count = _raw_json_record_count("remotejobs_api", raw)
            parsed = _parse_json_feed("remotejobs_api", source, raw, settings)
            jobs.extend(parsed)
        except Exception:
            record_role_feed_check(database_path, source_id, query_key, state="error")
            raise
        record_role_feed_check(database_path, source_id, query_key)
        response_bytes += len(payload)
        raw_records += raw_count
        parse_failures += max(0, raw_count - len(parsed))
        checked += 1
    return FetchOutcome(
        jobs=jobs,
        checked=checked,
        message=f"Retrieved {len(jobs)} RemoteJobs.org records across {checked} query pages.",
        response_bytes=response_bytes,
        raw_records=raw_records,
        parse_failures=parse_failures,
        status_counts={"status_200": checked},
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
                elif name in {
                    "title",
                    "description",
                    "summary",
                    "content",
                    "pubdate",
                    "published",
                    "updated",
                    "guid",
                    "id",
                    "category",
                    "company",
                    "location",
                }:
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
        if not company and source.get("kind") == "weworkremotely_rss":
            title, company = _split_board_title(title)
        location = plain_text(
            item.get("location") or ("Remote" if "remote" in title.casefold() else ""), 1_000
        )
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


def _source_epoch_date(value: Any) -> str:
    if value in (None, ""):
        return ""
    try:
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds /= 1000
        return datetime.fromtimestamp(seconds, tz=timezone.utc).isoformat(timespec="seconds")
    except (OverflowError, OSError, TypeError, ValueError):
        return parse_date(value)


def _salary_range_from_text(value: str) -> tuple[float | None, float | None]:
    matches = re.findall(r"(?<![A-Za-z])([0-9][0-9,]*(?:\.[0-9]+)?)\s*([kKmM]?)", value)
    amounts: list[float] = []
    for number, suffix in matches[:2]:
        amount = _number(number)
        if amount is None:
            continue
        if suffix.casefold() == "k":
            amount *= 1_000
        elif suffix.casefold() == "m":
            amount *= 1_000_000
        amounts.append(amount)
    if not amounts:
        return None, None
    if len(amounts) == 1:
        return amounts[0], amounts[0]
    return min(amounts), max(amounts)


def _salary_period_from_text(value: str) -> str:
    text = value.casefold()
    if re.search(r"/\s*(?:hr|hour)|per\s+hour|hourly", text):
        return "hourly"
    if re.search(r"/\s*(?:mo|month)|per\s+month|monthly", text):
        return "monthly"
    if re.search(r"/\s*(?:wk|week)|per\s+week|weekly", text):
        return "weekly"
    if re.search(r"/\s*(?:yr|year)|per\s+year|annual|yearly", text):
        return "annual"
    return ""


def _split_board_title(value: str) -> tuple[str, str]:
    """Recover common `Company: Role` and `Role at Company` RSS title formats."""
    if ":" in value:
        company, title = value.split(":", 1)
        if company.strip() and title.strip() and len(company) <= 100:
            return title.strip(), company.strip()
    match = re.match(r"^(.*?)\s+at\s+(.+)$", value, re.IGNORECASE)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return value, ""


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
        if is_x_host(host):
            return False, "X and its short-link domains are manual-only; use the X leads page."
        if parts.scheme != "https" or not host or parts.username or parts.password:
            return False, "Use an HTTPS careers or public job URL without embedded credentials."
        if parts.port not in (None, 443):
            return False, "Only standard HTTPS port 443 is supported."
        addresses = {
            ipaddress.ip_address(info[4][0])
            for info in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        }
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
        raise SourceFetchError(
            "Scrapling is unavailable. Install the project dependencies."
        ) from exc

    class BoundedCareerSpider(Spider):
        name = "clue_ai_public_careers"
        robots_txt_obey = ROBOTS_TXT_OBEY
        allowed_domains: ClassVar[set[str]] = {host}
        concurrent_requests = SCRAPLING_CONCURRENT_REQUESTS
        concurrent_requests_per_domain = SCRAPLING_CONCURRENT_REQUESTS_PER_DOMAIN
        download_delay = SCRAPLING_DOWNLOAD_DELAY_SECONDS
        max_blocked_retries = 0
        logging_level = logging.INFO
        start_urls: ClassVar[list[str]] = []
        user_agent: ClassVar[str] = settings.crawler_user_agent

        def __init__(self) -> None:
            super().__init__()
            self.start_urls = [start_url]
            self.allowed_domains = {host}
            self.hit_block = False
            self.page_limit = STANDALONE_CAREER_PAGE_LIMIT
            self.scheduled_urls = {canonical_url(start_url)}
            self.raw_records = 0
            self.parse_failures = 0
            self.not_found_count = 0

        def configure_sessions(self, manager) -> None:
            manager.add(
                "ordinary",
                FetcherSession(
                    impersonate=None,
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
            yield ScraplingRequest(
                self.start_urls[0],
                sid=self._session_manager.default_session_id,
                callback=self.parse,
                headers={
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml",
                },
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
            if status == 404:
                self.not_found_count += 1
                return
            if status < 200 or status >= 300:
                return
            if len(body) > settings.max_page_bytes:
                self.parse_failures += 1
                return
            entries = _extract_jsonld_job_postings(response, source, settings)
            self.raw_records += len(entries)
            for entry in entries:
                yield entry
            if entries:
                return
            is_job_detail = bool(_JOB_DETAIL_PATH.search(urlsplit(response.url).path))
            if is_job_detail:
                entry = _extract_html_job_posting(response, source, settings)
                if entry:
                    self.raw_records += 1
                    yield entry
                    return
                self.parse_failures += 1
                return
            for href in response.css("a::attr(href)").getall():
                absolute = urljoin(response.url, str(href))
                parts = urlsplit(absolute)
                if parts.scheme != "https" or (parts.hostname or "").lower() != host:
                    continue
                path = parts.path.casefold()
                if not _CAREER_OR_JOB_PATH.search(path):
                    continue
                normalized = canonical_url(absolute)
                if not normalized or normalized in self.scheduled_urls:
                    continue
                if len(self.scheduled_urls) >= self.page_limit:
                    break
                self.scheduled_urls.add(normalized)
                yield response.follow(
                    normalized,
                    callback=self.parse_job_page,
                    headers={
                        "User-Agent": self.user_agent,
                        "Accept": "text/html,application/xhtml+xml",
                    },
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
            if status == 404:
                self.not_found_count += 1
                return
            if status < 200 or status >= 300:
                return
            if len(body) > settings.max_page_bytes:
                self.parse_failures += 1
                return
            structured = _extract_jsonld_job_postings(response, source, settings)
            self.raw_records += len(structured)
            for entry in structured:
                yield entry
            if not structured:
                entry = _extract_html_job_posting(response, source, settings)
                if entry:
                    self.raw_records += 1
                    yield entry
                else:
                    self.parse_failures += 1

    try:
        spider = BoundedCareerSpider()
        result = spider.start()
    except Exception as exc:
        raise SourceFetchError(f"Scrapling crawl failed: {type(exc).__name__}.") from exc
    stats = getattr(result, "stats", None)
    status_counts = getattr(stats, "response_status_count", {}) if stats else {}
    not_found_count = max(
        spider.not_found_count,
        int((status_counts or {}).get("status_404", 0) or 0),
    )
    blocked_status = any(key in status_counts for key in ("status_401", "status_403", "status_429"))
    if blocked_status or getattr(spider, "hit_block", False):
        return FetchOutcome(
            message="The source returned an access or bot challenge.",
            blocked=True,
            checked=int(getattr(stats, "requests_count", 1) or 1) if stats else 1,
            response_bytes=int(getattr(stats, "response_bytes", 0) or 0) if stats else 0,
            raw_records=spider.raw_records,
            parse_failures=spider.parse_failures,
            not_found_count=not_found_count,
            status_counts=dict(status_counts or {}),
        )
    jobs = []
    for item in getattr(result, "items", []):
        if isinstance(item, dict):
            job = _normalize_crawled_job(source, item, settings)
            if job:
                jobs.append(job)
    parse_failures = spider.parse_failures + max(0, spider.raw_records - len(jobs))
    return FetchOutcome(
        jobs=jobs,
        checked=int(getattr(stats, "requests_count", 1) or 1) if stats else 1,
        message=f"Retrieved {len(jobs)} career-page listings.",
        response_bytes=int(getattr(stats, "response_bytes", 0) or 0) if stats else 0,
        raw_records=spider.raw_records,
        parse_failures=parse_failures,
        not_found_count=not_found_count,
        status_counts=dict(status_counts or {}),
    )


def _extract_jsonld_job_postings(
    response, source: dict[str, Any], settings: Settings
) -> list[dict[str, Any]]:
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
            if not any(
                str(value).rstrip("/").rsplit("/", 1)[-1] == "JobPosting" for value in types
            ):
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
            locations.append(
                ", ".join(
                    str(value)
                    for value in (
                        address.get("addressLocality"),
                        address.get("addressRegion"),
                        address.get("addressCountry"),
                    )
                    if value
                )
            )
    restrictions = item.get("applicantLocationRequirements") or item.get("eligibleRegion") or []
    if not isinstance(restrictions, list):
        restrictions = [restrictions]
    for restriction in restrictions:
        if isinstance(restriction, dict):
            locations.append(
                str(restriction.get("name") or restriction.get("addressCountry") or "")
            )
        elif restriction:
            locations.append(str(restriction))
    raw_location = plain_text("; ".join(part for part in locations if part), 1_000)
    description = plain_text(item.get("description") or "", settings.max_job_description_chars)
    workplace = (
        "remote"
        if str(item.get("jobLocationType") or "").upper() == "TELECOMMUTE"
        else infer_workplace(raw_location, description)
    )
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


def _extract_html_job_posting(
    response, source: dict[str, Any], settings: Settings
) -> dict[str, Any] | None:
    """Bounded fallback for a linked job detail page without JobPosting JSON-LD."""
    title = response.css("h1::text").get() or response.css("title::text").get()
    title = plain_text(title, 300)
    normalized_title = re.sub(r"\s*[|·–—-]\s*[^|·–—-]+$", "", title).strip()
    if not normalized_title or normalized_title.casefold() in {
        "careers",
        "jobs",
        "open positions",
        "open roles",
        "join our team",
        "work with us",
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
        "hiringOrganization": {
            "name": (source.get("config") or {}).get("company") or source.get("name", "")
        },
        "description": description,
        "jobLocation": {"address": {"addressLocality": location}} if location else {},
        "datePosted": date_posted,
        "url": getattr(response, "url", ""),
        "_response_url": getattr(response, "url", ""),
    }
