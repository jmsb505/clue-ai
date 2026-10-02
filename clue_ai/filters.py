from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from clue_ai.domain import SearchCriteria
from clue_ai.jobs import classify_location

DEFAULT_FIT_WEIGHTS = {
    "role": 25,
    "skills": 25,
    "experience": 10,
    "ai_relevance": 35,
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

    for job in annotate_jobs(jobs, criteria):
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
        if criteria.workplace == "hybrid" and job.get("workplace_type") not in {"hybrid", "unknown"}:
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
    elif legacy_weights == LEGACY_DEFAULT_FIT_WEIGHTS:
        weights = DEFAULT_FIT_WEIGHTS.copy()
    elif not any(legacy_weights.values()):
        weights = {**legacy_weights, "ai_relevance": 0}
    else:
        weights = {
            **legacy_weights,
            "ai_relevance": min(100, max(legacy_weights.values()) + 5),
        }
    return SearchCriteria(
        roles=str(form.get("roles", ""))[:500],
        target_seniority="junior_or_intern",
        paid_only=True,
        work_from=str(form.get("work_from", "Italy"))[:100],
        workplace=str(form.get("workplace", "remote"))[:20],
        employment_types=str(form.get("employment_types", ""))[:200],
        minimum_salary=str(form.get("minimum_salary", ""))[:30],
        salary_currency=str(form.get("salary_currency", "EUR"))[:3].upper(),
        requires_sponsorship=_enum(form.get("requires_sponsorship", "unknown"), {"yes", "no", "unknown"}),
        posted_within_days=max(1, min(days, 365)),
        must_have=str(form.get("must_have", ""))[:1_000],
        nice_to_have=str(form.get("nice_to_have", ""))[:1_000],
        include_unknown_location=_checked(form.get("include_unknown_location", "on")),
        include_unknown_salary=_checked(form.get("include_unknown_salary", "on")),
        include_unknown_sponsorship=_checked(form.get("include_unknown_sponsorship", "on")),
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
