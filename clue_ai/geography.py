"""Explicit work-region constraints, independent of model confidence."""

from __future__ import annotations

import re

EU = frozenset(
    [
        "italy",
        "germany",
        "france",
        "spain",
        "netherlands",
        "poland",
        "portugal",
        "ireland",
        "sweden",
        "denmark",
        "austria",
        "belgium",
        "finland",
        "greece",
        "czechia",
        "romania",
        "bulgaria",
        "croatia",
        "cyprus",
        "estonia",
        "hungary",
        "latvia",
        "lithuania",
        "luxembourg",
        "malta",
        "slovakia",
        "slovenia",
    ]
)
EUROPE = EU | {
    "united kingdom",
    "switzerland",
    "norway",
    "iceland",
    "ukraine",
    "serbia",
    "albania",
    "bosnia",
    "montenegro",
    "north macedonia",
    "moldova",
}
LATAM = frozenset(
    [
        "mexico",
        "brazil",
        "argentina",
        "chile",
        "colombia",
        "peru",
        "uruguay",
        "paraguay",
        "ecuador",
        "bolivia",
        "venezuela",
        "guatemala",
        "honduras",
        "nicaragua",
        "panama",
        "cuba",
    ]
) | {"costa rica", "el salvador", "dominican republic"}
NORTH_AMERICA = {"united states", "canada", "mexico"}
ASIA = frozenset(
    [
        "india",
        "china",
        "japan",
        "singapore",
        "indonesia",
        "malaysia",
        "thailand",
        "vietnam",
        "philippines",
        "taiwan",
        "pakistan",
        "bangladesh",
        "nepal",
    ]
) | {"south korea", "hong kong"}
AFRICA = frozenset(
    ["egypt", "nigeria", "kenya", "morocco", "tunisia", "ghana", "ethiopia", "algeria", "senegal"]
) | {"south africa"}
MIDDLE_EAST = frozenset(
    ["israel", "turkey", "jordan", "lebanon", "qatar", "bahrain", "oman", "kuwait"]
) | {"saudi arabia", "united arab emirates"}
REGIONS = {
    "worldwide": (r"worldwide|anywhere in the world|work from anywhere|global(?:ly)?", None),
    "europe": (r"europe|european countries", EUROPE),
    "eu": (r"european union|eu(?:/eea)?|eu countries", EU),
    "eea": (r"eea|european economic area", EU | {"norway", "iceland", "liechtenstein"}),
    "emea": (r"emea", EUROPE | AFRICA | MIDDLE_EAST),
    "latam": (r"latam|latin america|latin american countries", LATAM),
    "south america": (
        r"south america",
        LATAM
        - {
            "mexico",
            "costa rica",
            "el salvador",
            "dominican republic",
            "guatemala",
            "honduras",
            "nicaragua",
            "panama",
            "cuba",
        },
    ),
    "north america": (r"north america", NORTH_AMERICA),
    "apac": (r"apac|asia[- ]pacific", ASIA | {"australia", "new zealand"}),
    "asia": (r"asia", ASIA),
    "africa": (r"africa", AFRICA),
    "middle east": (r"middle east", MIDDLE_EAST),
}
COUNTRIES = set().union(
    EUROPE,
    LATAM,
    NORTH_AMERICA,
    ASIA,
    AFRICA,
    MIDDLE_EAST,
    {"australia", "new zealand", "liechtenstein"},
)
ALIASES = {
    "uk": "united kingdom",
    "usa": "united states",
    "us": "united states",
    "u.s.": "united states",
    "italia": "italy",
    "milan": "italy",
    "milano": "italy",
}
POLICY_VERSION = "filters-v1.6.0"


def target_country(value: str) -> str:
    normalized = value.strip().casefold()
    if normalized in ALIASES:
        return ALIASES[normalized]
    found = [
        country for country in COUNTRIES if re.search(rf"\b{re.escape(country)}\b", normalized)
    ]
    return found[0] if len(found) == 1 else ""


def region_decision(location: str, work_from: str) -> tuple[str, str]:
    """Resolve explicit region labels, allowing unions. Country lists remain elsewhere."""
    if re.search(
        r"timezone|time zone|time[- ]?zone|headquarters|customers|clients|offices",
        location,
        re.IGNORECASE,
    ):
        return "", ""
    target = target_country(work_from)
    regions = [
        (name, members)
        for name, (pattern, members) in REGIONS.items()
        if re.search(rf"\b(?:{pattern})\b", location, re.IGNORECASE)
    ]
    if not regions:
        return "", ""
    if target and re.search(
        rf"\b(?:except|excluding|not (?:in|from))\s+{re.escape(target)}\b", location, re.IGNORECASE
    ):
        return "not_eligible", location[:500]
    # A separately named eligible country is an alternative to the region.
    target_names = [target] + [alias for alias, country in ALIASES.items() if country == target]
    if target and any(
        re.search(rf"\b{re.escape(name)}\b", location, re.IGNORECASE) for name in target_names
    ):
        return "eligible", location[:500]
    if any(members is None for _, members in regions):
        return "eligible", location[:500]
    if target and any(name == "emea" for name, _ in regions) and not any(
        name != "emea" and members is not None and target in members
        for name, members in regions
    ):
        return "needs_verification", location[:500]
    if not target:
        return "needs_verification", location[:500]
    if target == "turkey" and any(name in {"europe", "asia"} for name, _ in regions):
        return "needs_verification", location[:500]  # Transcontinental hiring scope is ambiguous.
    if any(target in members for _, members in regions):
        return "eligible", location[:500]
    # Unknown countries aren't assumed absent from our bounded membership lists.
    if target in COUNTRIES:
        return "not_eligible", location[:500]
    return "needs_verification", location[:500]


def explicit_work_region(location: str, description: str, work_from: str) -> tuple[str, str]:
    """Restrictions only: structured region or explicit residency/remote-only wording."""
    regions = "|".join(pattern for pattern, _ in REGIONS.values())
    countries = "|".join(
        re.escape(c) for c in sorted(COUNTRIES | set(ALIASES), key=len, reverse=True)
    )
    place = rf"(?:{regions}|{countries})"
    patterns = (
        rf"\b{place}\b[- ]only\b",
        rf"\bonly (?:in|for|available in|open to candidates in) (?:the )?{place}\b",
        rf"\b(?:remote (?:from|in)|must (?:be |reside |live )?(?:based in|located in|in)) (?:the )?{place}\b",
        rf"\b{place}\b[- ]based candidates only\b",
    )
    # Scan the full bounded stored description; collapsing HTML must not lose late restrictions.
    scope = f"{location}. {description}"
    for pattern in patterns:
        for match in re.finditer(pattern, scope, re.IGNORECASE):
            prefix = scope[max(0, match.start() - 30) : match.start()]
            suffix = scope[match.end() : match.end() + 80]
            if re.search(r"\b(?:not|no requirement to be|need not be)\s*$", prefix, re.IGNORECASE):
                continue
            if re.match(r"\s*(?:is |are )?(?:preferred|optional)\b", suffix, re.IGNORECASE):
                continue
            text = match.group(0)
            # "remote in Europe or worldwide" is a union, not an Europe-only rule.
            union = re.match(rf"\s*(?:/|,|or|and)\s*{place}\b", suffix, re.IGNORECASE)
            while union:
                text += union.group(0)
                suffix = suffix[union.end() :]
                union = re.match(rf"\s*(?:/|,|or|and)\s*{place}\b", suffix, re.IGNORECASE)
            decision, _ = region_decision(text, work_from)
            if not decision:
                target = target_country(work_from)
                mentioned = {
                    ALIASES.get(m.group(0).casefold(), m.group(0).casefold())
                    for m in re.finditer(rf"\b(?:{countries})\b", text, re.IGNORECASE)
                }
                if target and mentioned:
                    decision = "eligible" if target in mentioned else "not_eligible"
            if decision:
                return decision, text[:500]
    decision = region_decision(location, work_from)
    if decision[0]:
        return decision
    if re.search(r"\bwork from anywhere(?: in the world)?\b", description, re.IGNORECASE):
        return "eligible", "Work from anywhere"
    return "", ""
