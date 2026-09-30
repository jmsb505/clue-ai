from __future__ import annotations

import hashlib
import html
import ipaddress
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
        elif tag in {"p", "div", "li", "br", "h1", "h2", "h3", "tr"} and not self._skip_depth:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        elif tag in {"p", "div", "li", "br", "h1", "h2", "h3", "tr"} and not self._skip_depth:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)


def plain_text(value: object, limit: int = 20_000) -> str:
    raw = str(value or "")
    parser = _PlainText()
    parser.feed(raw)
    raw = " ".join(parser.parts)
    raw = html.unescape(raw)
    raw = re.sub(r"[\r\t\u00a0]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:limit]


def canonical_url(value: str) -> str:
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return ""
    if (
        parts.scheme.lower() not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        return ""
    hostname = parts.hostname.lower()
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(
        (".localhost", ".local", ".internal", ".test")
    ):
        return ""
    try:
        if not ipaddress.ip_address(hostname).is_global:
            return ""
        if ":" in hostname:
            return ""
    except ValueError:
        pass
    try:
        port = parts.port
    except ValueError:
        return ""
    if port not in (None, 80, 443):
        return ""
    netloc = hostname
    stripped_query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                      if not key.lower().startswith("utm_") and key.lower() not in {"ref", "source"}]
    query = urlencode(stripped_query, doseq=True)
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", query, ""))


def parse_date(value: object) -> str:
    if not value:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
        except (TypeError, ValueError, OverflowError):
            return ""
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")


def infer_workplace(value: object, description: str = "") -> str:
    text = f"{value or ''} {description[:3000]}".casefold()
    if re.search(r"\bhybrid\b|\bremote and on[- ]site\b", text):
        return "hybrid"
    if re.search(r"\bremote(?:ly)?\b|\bwork from anywhere\b|\bdistributed\b", text):
        return "remote"
    if re.search(r"\bon[- ]site\b|\bin[- ]office\b|\bin person\b", text):
        return "onsite"
    return "unknown"


def classify_location(location: str, description: str, work_from: str = "Italy") -> tuple[str, str]:
    """Classify explicit work-from eligibility; a generic remote label remains uncertain."""
    target = work_from.strip() or "Italy"
    location_text = plain_text(location, 1_000)
    description_lines = [plain_text(line, 600) for line in description.splitlines()]
    cue_lines = [
        line for line in description_lines
        if re.search(r"remote|location|based|eligible|work from|located|timezone|time zone|country|region", line, re.IGNORECASE)
    ]
    evidence_pool = " | ".join(([location_text] if location_text else []) + cue_lines[:80])
    haystack = evidence_pool.casefold()
    target_norm = target.casefold()
    incompatible = _has_exclusive_other_region(haystack)
    if incompatible:
        evidence = _find_pattern_evidence(evidence_pool, incompatible)
        return "not_eligible", evidence or location_text
    if target_norm and _explicit_location_match(haystack, target_norm):
        evidence = _find_evidence(evidence_pool, target)
        return "eligible", evidence or location_text or target
    target_countries = _country_patterns(target_norm)
    if target_countries and any(re.search(pattern, haystack) for pattern in target_countries):
        evidence = _find_pattern_evidence(evidence_pool, target_countries)
        return "eligible", evidence or location_text

    regions = {
        "worldwide": (
            r"\bworldwide\b", r"\banywhere in the world\b", r"\bglobally\b",
            r"\bwork from anywhere\b",
        ),
        "europe": (
            r"\beurope\b", r"\beuropean union\b", r"\beu/eea\b", r"\beea\b",
            r"\beu countries\b",
        ),
    }
    for region, patterns in regions.items():
        if any(re.search(pattern, haystack) for pattern in patterns):
            evidence = _find_pattern_evidence(evidence_pool, patterns)
            return "eligible", evidence or region

    conflicting_country = _location_country_conflict(location_text, target_norm)
    if conflicting_country:
        return "not_eligible", conflicting_country

    remote_evidence = bool(re.search(r"\bremote\b|\bwork from anywhere\b", haystack))
    if remote_evidence or location_text:
        evidence = _find_pattern_evidence(evidence_pool, (r"\bremote\b",)) or location_text
        return "needs_verification", evidence or "Location eligibility is not explicit."
    return "unknown", "No reliable work-from location evidence was found."


def _explicit_location_match(haystack: str, target: str) -> bool:
    aliases = {
        "italy": (r"\bitaly\b", r"\bitalian\b"),
        "germany": (r"\bgermany\b", r"\bgerman\b"),
        "france": (r"\bfrance\b", r"\bfrench\b"),
        "spain": (r"\bspain\b", r"\bspanish\b"),
        "netherlands": (r"\bnetherlands\b", r"\bdutch\b"),
        "united kingdom": (r"\bunited kingdom\b", r"\buk\b", r"\bbritain\b"),
        "uk": (r"\bunited kingdom\b", r"\buk\b", r"\bbritain\b"),
        "united states": (r"\bunited states\b", r"\busa\b", r"\bus\b"),
        "usa": (r"\bunited states\b", r"\busa\b", r"\bus\b"),
        "canada": (r"\bcanada\b", r"\bcanadian\b"),
        "poland": (r"\bpoland\b", r"\bpolish\b"),
        "portugal": (r"\bportugal\b", r"\bportuguese\b"),
    }
    patterns = aliases.get(target, (rf"\b{re.escape(target)}\b",))
    return any(re.search(pattern, haystack) for pattern in patterns)


def _country_patterns(text: str) -> tuple[str, ...]:
    aliases = {
        "italy": (r"\bitaly\b", r"\bitalian\b"),
        "germany": (r"\bgermany\b", r"\bgerman\b"),
        "france": (r"\bfrance\b", r"\bfrench\b"),
        "spain": (r"\bspain\b", r"\bspanish\b"),
        "netherlands": (r"\bnetherlands\b", r"\bdutch\b"),
        "united kingdom": (r"\bunited kingdom\b", r"\buk\b", r"\bbritain\b"),
        "uk": (r"\bunited kingdom\b", r"\buk\b", r"\bbritain\b"),
        "united states": (r"\bunited states\b", r"\busa\b", r"\bu\.s\.\b", r"\bus\b"),
        "usa": (r"\bunited states\b", r"\busa\b", r"\bu\.s\.\b", r"\bus\b"),
        "canada": (r"\bcanada\b", r"\bcanadian\b"),
        "poland": (r"\bpoland\b", r"\bpolish\b"),
        "portugal": (r"\bportugal\b", r"\bportuguese\b"),
        "switzerland": (r"\bswitzerland\b", r"\bswiss\b"),
        "ireland": (r"\bireland\b", r"\birish\b"),
        "sweden": (r"\bsweden\b", r"\bswedish\b"),
        "norway": (r"\bnorway\b", r"\bnorwegian\b"),
        "denmark": (r"\bdenmark\b", r"\bdanish\b"),
        "austria": (r"\baustria\b", r"\baustrian\b"),
        "belgium": (r"\bbelgium\b", r"\bbelgian\b"),
        "finland": (r"\bfinland\b", r"\bfinnish\b"),
        "greece": (r"\bgreece\b", r"\bgreek\b"),
        "czechia": (r"\bczechia\b", r"\bczech republic\b"),
        "romania": (r"\bromania\b", r"\bromanian\b"),
    }
    selected = []
    for country, patterns in aliases.items():
        if re.search(rf"\b{re.escape(country)}\b", text) or any(
            re.search(pattern, text) for pattern in patterns
        ):
            selected.extend(patterns)
    return tuple(dict.fromkeys(selected))


def _location_country_conflict(location_text: str, target: str) -> str:
    location = location_text.casefold()
    if not location or not target:
        return ""
    location_patterns = _country_patterns(location)
    target_patterns = _country_patterns(target)
    if not location_patterns or not target_patterns:
        return ""
    target_countries = {
        country for country, patterns in _known_countries().items()
        if any(re.search(pattern, target) for pattern in patterns)
    }
    location_countries = {
        country for country, patterns in _known_countries().items()
        if any(re.search(pattern, location) for pattern in patterns)
    }
    if target_countries and location_countries and target_countries.isdisjoint(location_countries):
        return _find_pattern_evidence(location_text, location_patterns) or location_text
    return ""


def _known_countries() -> dict[str, tuple[str, ...]]:
    return {
        "italy": (r"\bitaly\b", r"\bitalian\b"),
        "germany": (r"\bgermany\b", r"\bgerman\b"),
        "france": (r"\bfrance\b", r"\bfrench\b"),
        "spain": (r"\bspain\b", r"\bspanish\b"),
        "netherlands": (r"\bnetherlands\b", r"\bdutch\b"),
        "united kingdom": (r"\bunited kingdom\b", r"\buk\b", r"\bbritain\b"),
        "united states": (r"\bunited states\b", r"\busa\b", r"\bu\.s\.\b", r"\bus\b"),
        "canada": (r"\bcanada\b", r"\bcanadian\b"),
        "poland": (r"\bpoland\b", r"\bpolish\b"),
        "portugal": (r"\bportugal\b", r"\bportuguese\b"),
        "switzerland": (r"\bswitzerland\b", r"\bswiss\b"),
        "ireland": (r"\bireland\b", r"\birish\b"),
        "sweden": (r"\bsweden\b", r"\bswedish\b"),
        "norway": (r"\bnorway\b", r"\bnorwegian\b"),
        "denmark": (r"\bdenmark\b", r"\bdanish\b"),
        "austria": (r"\baustria\b", r"\baustrian\b"),
        "belgium": (r"\bbelgium\b", r"\bbelgian\b"),
        "finland": (r"\bfinland\b", r"\bfinnish\b"),
        "greece": (r"\bgreece\b", r"\bgreek\b"),
        "czechia": (r"\bczechia\b", r"\bczech republic\b"),
        "romania": (r"\bromania\b", r"\bromanian\b"),
    }


def _has_exclusive_other_region(haystack: str) -> tuple[str, ...]:
    patterns = (
        r"\b(?:us|u\.s\.|usa|united states|canada|north america)[- ]only\b",
        r"\bonly (?:in|for|available in) (?:the )?(?:us|u\.s\.|usa|united states|canada)\b",
        r"\b(?:us|u\.s\.|usa|united states|canada)[- ]based candidates only\b",
    )
    for pattern in patterns:
        if re.search(pattern, haystack):
            return (pattern,)
    return ()


def _find_evidence(text: str, term: str) -> str:
    at = text.casefold().find(term.casefold())
    if at < 0:
        aliases = {"italy": "Italian", "united states": "US", "usa": "US", "uk": "United Kingdom"}
        alias = aliases.get(term.casefold())
        at = text.casefold().find(alias.casefold()) if alias else -1
    return text[max(0, at - 70): min(len(text), at + len(term) + 90)].strip(" |") if at >= 0 else ""


def _find_pattern_evidence(text: str, patterns: tuple[str, ...]) -> str:
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return text[max(0, match.start() - 70): min(len(text), match.end() + 90)].strip(" |")
    return ""


def stable_job_id(canonical: str) -> str:
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]


def job_fingerprint(title: str, company: str, location: str, posted_at: str) -> str:
    date_bucket = posted_at[:10]
    normalized = "|".join(value.casefold().strip() for value in (title, company, location, date_bucket))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
