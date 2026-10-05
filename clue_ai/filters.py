from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any

from clue_ai.domain import SearchCriteria
from clue_ai.job_focus import focused_roles
from clue_ai.jobs import classify_location
from clue_ai.work_scope import explicit_italian_language_requirement, local_workplace_decision

DEFAULT_FIT_WEIGHTS = {
    "role": 25,
    "skills": 15,
    "experience": 5,
    "ai_relevance": 50,
    "preference": 5,
}
LEGACY_DEFAULT_FIT_WEIGHTS = {
    "role": 35,
    "skills": 35,
    "experience": 20,
    "preference": 10,
}


def terms(value: str) -> list[str]:
    return [part.strip().casefold() for part in re.split(r"[,;\n]+", value or "") if part.strip()]


def _job_text(job: dict[str, Any]) -> str:
    return " ".join(
        str(job.get(key) or "")
        for key in ("title", "company", "description", "location_raw", "employment_type")
    ).casefold()


def annotate_jobs(jobs: list[dict[str, Any]], criteria: SearchCriteria) -> list[dict[str, Any]]:
    """Attach per-run location and freshness evidence without excluding candidates."""
    annotated: list[dict[str, Any]] = []
    for source_job in jobs:
        job = dict(source_job)
        eligibility, evidence = classify_location(
            str(job.get("location_raw") or ""),
            str(job.get("description") or ""),
            criteria.work_from,
        )
        job["eligibility_status"] = eligibility
        job["eligibility_evidence"] = evidence
        job["workplace_label"] = _workplace_label(str(job.get("workplace_type") or "unknown"))
        source_ids = {str(source.get("id") or "") for source in job.get("sources", [])}
        if job.get("source_id") == "x_manual" or "x_manual" in source_ids:
            job["freshness_status"] = "manual"
            job["freshness_age_days"] = None
        else:
            checked_at = _parse_datetime(job.get("last_checked_at"))
            fresh_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
            job["freshness_status"] = (
                "recent" if checked_at and checked_at >= fresh_cutoff else "stale"
            )
            job["freshness_age_days"] = (
                max(0, (datetime.now(timezone.utc) - checked_at).days) if checked_at else None
            )
        annotated.append(job)
    return annotated


def apply_candidate_search_scope(
    jobs: list[dict[str, Any]], criteria: SearchCriteria
) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Keep only jobs within the selected language and default workplace scope."""
    selected: list[dict[str, Any]] = []
    excluded: Counter[str] = Counter()
    for job in jobs:
        if criteria.exclude_italian_requirement:
            language_evidence = explicit_italian_language_requirement(
                str(job.get("description") or "")
            )
            if language_evidence:
                excluded["explicit_italian_requirement"] += 1
                continue

        if criteria.workplace == "remote_preferred":
            workplace_type = str(job.get("workplace_type") or "unknown").casefold().replace("-", "")
            if workplace_type == "remote":
                location_status = str(job.get("eligibility_status") or "unknown")
                if location_status == "eligible":
                    selected.append(job)
                elif location_status == "not_eligible":
                    excluded["remote_outside_work_from_region"] += 1
                else:
                    excluded["remote_region_unverified"] += 1
                continue

            city_status, city_evidence = local_workplace_decision(
                str(job.get("location_raw") or ""),
                str(job.get("description") or ""),
                workplace_type,
                criteria.local_workplace_city,
            )
            if city_status == "not_eligible" and workplace_type in {"hybrid", "onsite"}:
                excluded["in_person_outside_local_city"] += 1
                continue
            if city_status != "eligible":
                excluded["workplace_city_unverified"] += 1
                continue
            job["eligibility_status"] = "eligible"
            job["eligibility_evidence"] = city_evidence
        selected.append(job)
    return selected, excluded


def filter_jobs(jobs: list[dict[str, Any]], criteria: SearchCriteria) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    role_terms = terms(criteria.roles)
    must_have = terms(criteria.must_have)
    employment = set(terms(criteria.employment_types))
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, min(criteria.posted_within_days, 365)))
    try:
        minimum_salary = float(criteria.minimum_salary) if criteria.minimum_salary.strip() else None
    except ValueError:
        minimum_salary = None

    scoped_jobs, _ = apply_candidate_search_scope(annotate_jobs(jobs, criteria), criteria)
    for job in scoped_jobs:
        text = _job_text(job)
        if role_terms and not any(term in text for term in role_terms):
            continue
        if must_have and not all(term in text for term in must_have):
            continue
        if employment and str(job.get("employment_type") or "unknown").casefold() not in employment:
            continue
        if criteria.requires_sponsorship == "yes":
            sponsorship = str(job.get("visa_sponsorship") or "unknown").casefold()
            if sponsorship == "no":
                continue
            if sponsorship == "unknown" and not criteria.include_unknown_sponsorship:
                continue
        if criteria.workplace == "remote" and job.get("workplace_type") not in {"remote", "unknown"}:
            continue
        if criteria.workplace == "hybrid" and job.get("workplace_type") not in {"remote", "hybrid", "unknown"}:
            continue
        eligibility = str(job.get("eligibility_status") or "unknown")
        if eligibility == "not_eligible":
            continue
        if eligibility in {"unknown", "needs_verification"} and not criteria.include_unknown_location:
            continue
        if minimum_salary is not None:
            salary_max = job.get("salary_max")
            salary_min = job.get("salary_min")
            if salary_max is None and salary_min is None:
                if not criteria.include_unknown_salary:
                    continue
            else:
                same_currency = (
                    str(job.get("salary_currency") or "").upper()
                    == criteria.salary_currency.upper()
                )
                annual = str(job.get("salary_period") or "").casefold() in {
                    "year", "yearly", "annual", "annually", "per year", "yearly salary"
                }
                if not same_currency or not annual:
                    if not criteria.include_unknown_salary:
                        continue
                elif float(salary_max if salary_max is not None else salary_min) < minimum_salary:
                    continue
        posted = _parse_datetime(job.get("posted_at"))
        if posted and posted < cutoff:
            continue
        selected.append(job)
    return selected


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)


def _workplace_label(value: str) -> str:
    return {"remote": "Remote", "hybrid": "Hybrid", "onsite": "On-site"}.get(value, "Not specified")


def criteria_from_form(form: dict[str, Any]) -> SearchCriteria:
    try:
        days = int(form.get("posted_within_days", 30))
    except (TypeError, ValueError):
        days = 30
    legacy_weights = {
        name: _integer(form.get(f"{name}_weight"), default)
        for name, default in LEGACY_DEFAULT_FIT_WEIGHTS.items()
    }
    if "ai_relevance_weight" in form:
        weights = {
            name: _integer(form.get(f"{name}_weight"), default)
            for name, default in DEFAULT_FIT_WEIGHTS.items()
        }
        if weights == {"role": 25, "skills": 25, "experience": 10, "ai_relevance": 35, "preference": 5}:
            weights = DEFAULT_FIT_WEIGHTS.copy()
    elif legacy_weights == LEGACY_DEFAULT_FIT_WEIGHTS:
        weights = DEFAULT_FIT_WEIGHTS.copy()
    elif not any(legacy_weights.values()):
        weights = {**legacy_weights, "ai_relevance": 0}
    else:
        weights = {
            **legacy_weights,
            "ai_relevance": min(100, max(legacy_weights.values()) + 5),
        }
    workplace = _enum(
        form.get("workplace", "remote_preferred"),
        {"remote_preferred", "remote", "hybrid", "any"},
    )
    include_unknown_location = (
        _checked(form.get("include_unknown_location")) if workplace != "remote_preferred" else False
    )
    return SearchCriteria(
        roles=focused_roles(str(form.get("roles", ""))),
        target_seniority="junior_or_intern",
        paid_only=True,
        work_from=str(form.get("work_from", "Italy"))[:100],
        workplace=workplace,
        local_workplace_city=str(form.get("local_workplace_city", "Milan"))[:100],
        employment_types=str(form.get("employment_types", ""))[:200],
        minimum_salary=str(form.get("minimum_salary", ""))[:30],
        salary_currency=str(form.get("salary_currency", "EUR"))[:3].upper(),
        requires_sponsorship=_enum(form.get("requires_sponsorship", "unknown"), {"yes", "no", "unknown"}),
        posted_within_days=max(1, min(days, 365)),
        must_have=str(form.get("must_have", ""))[:1_000],
        nice_to_have=str(form.get("nice_to_have", ""))[:1_000],
        include_unknown_location=include_unknown_location,
        include_unknown_salary=_checked(form.get("include_unknown_salary", "on")),
        include_unknown_sponsorship=_checked(form.get("include_unknown_sponsorship", "on")),
        include_reviewed=_checked(form.get("include_reviewed")),
        role_weight=weights["role"],
        skills_weight=weights["skills"],
        experience_weight=weights["experience"],
        ai_relevance_weight=weights["ai_relevance"],
        preference_weight=weights["preference"],
    )


def criteria_from_json(raw: str) -> SearchCriteria:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    return criteria_from_form(data)


def _checked(value: Any) -> bool:
    return str(value or "").casefold() in {"1", "true", "yes", "on"}


def _integer(value: Any, default: int) -> int:
    try:
        return max(0, min(int(value), 100))
    except (TypeError, ValueError):
        return default


def _enum(value: Any, allowed: set[str]) -> str:
    normalized = str(value or "unknown").casefold()
    return normalized if normalized in allowed else "unknown"
