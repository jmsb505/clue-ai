from __future__ import annotations

import re

from clue_ai.jobs import plain_text

_ITALIAN_LANGUAGE = re.compile(
    r"\b(?:italian|italiano|italiana|italiani|italiane|lingua italiana|dell['’]italiano)\b",
    re.IGNORECASE,
)
_ITALIAN_MANDATORY = re.compile(
    r"\b(?:required|requirement|must(?: be| have)?|need(?:ed)?|mandatory|essential|"
    r"necessary|richiest[oaie]?|obbligator[ioaie]?|necessar[ioaie]?|indispensabile)\b",
    re.IGNORECASE,
)
_ITALIAN_LANGUAGE_CUE = re.compile(
    r"\b(?:language|lingua|speak|speaking|spoken|written|conversational|verbal|"
    r"command of|knowledge of|language skills|language ability|conoscenza|padronanza)\b",
    re.IGNORECASE,
)
_ITALIAN_STRONG_PROFICIENCY = re.compile(
    r"\b(?:proficien(?:t|cy)|fluen(?:t|cy)|native|mother tongue|first language|"
    r"bilingual|C1|C2|B2|fluente|madrelingua)\b",
    re.IGNORECASE,
)
_ITALIAN_PREFERRED = re.compile(
    r"\b(?:preferred|preferable|nice to have|bonus|a plus|plus|desirable|ideally|"
    r"optional|preferibile|preferito|preferita|gradito|gradita|facoltativo|"
    r"costituisce un plus)\b",
    re.IGNORECASE,
)
_ITALIAN_NEGATED = re.compile(
    r"\b(?:not required|not a requirement|not necessary|not mandatory|no requirement|"
    r"no need (?:to|for)|need not|must not require|do not require|does not require|"
    r"non richiesto|non richiesta|"
    r"non necessario|non necessaria|non obbligatorio|non obbligatoria)\b",
    re.IGNORECASE,
)
_LANGUAGE_ALTERNATIVE = re.compile(
    r"\b(?:english|inglese)\b.{0,35}\b(?:or|either|oppure)\b.{0,35}\b"
    r"(?:italian|italiano|italiana)\b|"
    r"\b(?:italian|italiano|italiana)\b.{0,35}\b(?:or|either|oppure)\b"
    r".{0,35}\b(?:english|inglese)\b",
    re.IGNORECASE,
)
_GENERIC_LOCALITIES = re.compile(
    r"\b(?:italy|italia|lombardy|lombardia|europe|european union|eu|eea|emea|"
    r"worldwide|global|anywhere|multiple locations|various locations|remote|hybrid|"
    r"on[- ]site|timezone|time zone|CET|UTC|north|northern|central|south|southern)\b",
    re.IGNORECASE,
)
_OTHER_KNOWN_CITIES = (
    "Rome", "Roma", "Turin", "Torino", "Florence", "Firenze", "Bologna", "Naples",
    "Napoli", "Genoa", "Genova", "Venice", "Venezia", "Padua", "Padova", "Verona",
    "Parma", "Modena", "Bergamo", "Brescia", "Pisa", "Trento", "Trieste", "Palermo",
    "Catania", "Bari", "Lecce", "Cagliari",
)


def explicit_italian_language_requirement(description: str) -> str:
    """Return clear mandatory-Italian evidence; ignore optional and alternative-language mentions."""
    text = plain_text(description, 40_000)
    segments = re.split(r"(?<=[.!?;])\s+|[•▪●]\s*", text)
    for segment in segments:
        language = _ITALIAN_LANGUAGE.search(segment)
        if language is None or _LANGUAGE_ALTERNATIVE.search(segment):
            continue
        nearby = segment[max(0, language.start() - 60) : language.end() + 60]
        after = segment[language.end() : language.end() + 60]
        if _ITALIAN_NEGATED.search(nearby):
            continue
        if _ITALIAN_PREFERRED.search(after):
            continue
        language_cue = _ITALIAN_LANGUAGE_CUE.search(nearby)
        mandatory = _ITALIAN_MANDATORY.search(nearby)
        strong_proficiency = _ITALIAN_STRONG_PROFICIENCY.search(nearby)
        if strong_proficiency or (language_cue and mandatory):
            return segment.strip()[:500]
    return ""


def local_workplace_decision(
    location: str, description: str, workplace_type: str, local_city: str
) -> tuple[str, str]:
    """Check physical or unspecified workplace locations against the chosen city."""
    normalized_type = str(workplace_type or "unknown").casefold().replace("-", "")
    if normalized_type == "remote":
        return "not_applicable", ""
    if normalized_type not in {"hybrid", "onsite", "unknown"}:
        return "not_applicable", ""
    city = (str(local_city or "Milan").split(",", maxsplit=1)[0].strip() or "Milan")
    variants = ("Milan", "Milano") if city.casefold() in {"milan", "milano"} else (city,)
    location_text = plain_text(location, 1_000)
    description_text = plain_text(description, 40_000)
    for variant in variants:
        if re.search(rf"\b{re.escape(variant)}\b", location_text, re.IGNORECASE):
            return "eligible", location_text[:500]

    # A structured posting location takes precedence over incidental mentions in the body.
    for other_city in _OTHER_KNOWN_CITIES:
        if re.search(rf"\b{re.escape(other_city)}\b", location_text, re.IGNORECASE):
            return "not_eligible", location_text[:500]

    for variant in variants:
        escaped = re.escape(variant)
        role_site = re.compile(
            rf"\b(?:hybrid|on[- ]site|in[- ]office|office[- ]based|based|located|"
            rf"work(?:ing)? from|work location)\b.{{0,70}}\b(?:in|at|near|from)?\s*"
            rf"(?:the\s+)?{escaped}\b|"
            rf"\b{escaped}\b.{{0,70}}\b(?:hybrid|on[- ]site|in[- ]office|"
            rf"office[- ]based|office|work location)\b",
            re.IGNORECASE,
        )
        if role_site.search(description_text):
            return "eligible", f"The posting locates the hybrid/on-site role in {city}."

    for other_city in _OTHER_KNOWN_CITIES:
        escaped = re.escape(other_city)
        role_site = re.compile(
            rf"\b(?:hybrid|on[- ]site|in[- ]office|office[- ]based|based|located|"
            rf"work(?:ing)? from|work location)\b.{{0,70}}\b(?:in|at|near|from)?\s*"
            rf"(?:the\s+)?{escaped}\b|"
            rf"\b{escaped}\b.{{0,70}}\b(?:hybrid|on[- ]site|in[- ]office|"
            rf"office[- ]based|office|work location)\b",
            re.IGNORECASE,
        )
        if role_site.search(description_text):
            return "not_eligible", f"The posting locates the hybrid/on-site role in {other_city}."

    if location_text:
        remainder = _GENERIC_LOCALITIES.sub(" ", location_text)
        remainder = re.sub(r"[^a-zA-ZÀ-ÿ]+", " ", remainder).strip()
        if remainder:
            return "not_eligible", location_text[:500]
    return "needs_verification", location_text or "The physical work city is not stated."
