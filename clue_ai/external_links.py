from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlencode, urlsplit

from clue_ai.jobs import canonical_url

X_HOSTS = {"x.com", "www.x.com", "twitter.com", "www.twitter.com"}
SHORTENER_HOSTS = {
    "bit.do", "bit.ly", "bl.ink", "buff.ly", "cutt.ly", "goo.gl", "is.gd",
    "lnkd.in", "ow.ly", "rb.gy", "rebrand.ly", "s.id", "short.io", "shorturl.at",
    "t.co", "t.ly", "tiny.cc", "tinyurl.com", "trib.al",
}
_X_POST_PATH = re.compile(
    r"^/(?:[A-Za-z0-9_]{1,15}/status/(?P<account_id>\d+)|i/web/status/(?P<web_id>\d+))/?$",
    re.IGNORECASE,
)
_SEARCH_PUNCTUATION = re.compile(r"[^\w\s.+/#-]", re.UNICODE)


def is_x_host(host: str) -> bool:
    normalized = str(host or "").casefold().rstrip(".")
    return any(
        normalized == domain or normalized.endswith(f".{domain}")
        for domain in ("x.com", "twitter.com", "t.co")
    )


def normalize_x_status_url(value: str) -> tuple[str, str] | None:
    """Return the canonical X status URL and status ID for a user-supplied permalink."""
    raw = _valid_raw_url(value)
    if raw is None:
        return None
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError:
        return None
    host = (parts.hostname or "").casefold()
    match = _X_POST_PATH.fullmatch(parts.path)
    if (
        parts.scheme.casefold() != "https"
        or host not in X_HOSTS
        or parts.username
        or parts.password
        or port not in (None, 443)
        or match is None
    ):
        return None
    status_id = match.group("account_id") or match.group("web_id")
    return f"https://x.com{parts.path.rstrip('/')}", status_id


def normalize_public_job_url(value: str) -> tuple[str, str] | None:
    """Validate a direct HTTPS destination without resolving or fetching it."""
    raw = _valid_raw_url(value)
    if raw is None:
        return None
    try:
        parts = urlsplit(raw)
        port = parts.port
    except ValueError:
        return None
    host = (parts.hostname or "").casefold()
    if (
        parts.scheme.casefold() != "https"
        or not host
        or is_x_host(host)
        or parts.username
        or parts.password
        or port not in (None, 443)
        or host.endswith((".", ".localhost", ".local", ".internal", ".test", ".lan", ".home", ".onion"))
        or "." not in host
    ):
        return None
    try:
        ipaddress.ip_address(host)
        return None
    except ValueError:
        pass
    try:
        display_host = host.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    if is_x_host(display_host) or any(
        display_host == suffix or display_host.endswith(f".{suffix}")
        for suffix in SHORTENER_HOSTS
    ):
        return None
    normalized = canonical_url(raw)
    if not normalized:
        return None
    return normalized, display_host


def build_x_search_url(roles: str, work_from: str, workplace: str = "remote") -> str:
    role_terms = _search_terms(roles, limit=5)
    location = _search_terms(re.sub(r"[,;/\n]+", "\n", str(work_from or "")), limit=4)
    if not role_terms:
        return ""
    role_query = " OR ".join(f'"{term}"' for term in role_terms)
    location_terms = list(location)
    if any(term.casefold() in {"italy", "italia"} for term in location_terms):
        location_terms.extend(["Europe", "EU", "worldwide"])
    if not location_terms:
        location_terms = ["Europe"]
    location_query = "(" + " OR ".join(f'"{term}"' for term in location_terms) + ")"
    query_parts = [
        f"({role_query})",
        '("hiring" OR "job opening" OR "apply")',
        location_query,
    ]
    workplace_term = {"remote": "remote", "hybrid": "hybrid", "onsite": "onsite"}.get(
        str(workplace).casefold()
    )
    if workplace_term:
        query_parts.append(workplace_term)
    return "https://x.com/search?" + urlencode({"q": " ".join(query_parts)})


def _valid_raw_url(value: str) -> str | None:
    raw = str(value or "").strip()
    if not raw or len(raw) > 2_000 or "\\" in raw:
        return None
    if any(character.isspace() or ord(character) < 32 for character in raw):
        return None
    try:
        parts = urlsplit(raw)
        _ = parts.port
    except ValueError:
        return None
    if not parts.netloc:
        return None
    return raw


def _search_terms(value: str, limit: int) -> list[str]:
    raw_terms = re.split(r"[,;\n]+", str(value or ""))
    results = []
    for raw_term in raw_terms:
        cleaned = _SEARCH_PUNCTUATION.sub(" ", raw_term)
        term = " ".join(cleaned.split())[:70]
        if term and term.casefold() not in {item.casefold() for item in results}:
            results.append(term)
        if len(results) >= limit:
            break
    return results
