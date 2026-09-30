from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class CandidateProfile:
    summary: str = ""
    target_roles: str = ""
    skills: str = ""
    experience: str = ""
    education: str = ""
    languages: str = ""
    profile_language: str = "unknown"
    work_authorized_countries: str = ""
    requires_sponsorship: str = "unknown"
    cv_filename: str = ""
    cv_path: str = ""
    extracted_text: str = ""
    updated_at: str = ""

    def fit_fields(self) -> dict[str, str]:
        """Only reviewed, job-relevant fields intended for Jev; never include CV/file metadata."""
        return {
            "summary": self.summary.strip(),
            "target_roles": self.target_roles.strip(),
            "skills": self.skills.strip(),
            "experience": self.experience.strip(),
            "education": self.education.strip(),
            "languages": self.languages.strip(),
        }


@dataclass
class SearchCriteria:
    roles: str = ""
    work_from: str = "Italy"
    workplace: str = "remote"
    employment_types: str = ""
    minimum_salary: str = ""
    salary_currency: str = "EUR"
    requires_sponsorship: str = "unknown"
    posted_within_days: int = 30
    must_have: str = ""
    nice_to_have: str = ""
    include_unknown_location: bool = True
    include_unknown_salary: bool = True
    include_unknown_sponsorship: bool = True
    role_weight: int = 35
    skills_weight: int = 35
    experience_weight: int = 20
    preference_weight: int = 10

    def to_jsonable(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class NormalizedJob:
    source_id: str
    source_name: str
    external_id: str
    title: str
    company: str
    description: str
    source_url: str
    canonical_url: str = ""
    location_raw: str = ""
    workplace_type: str = "unknown"
    employment_type: str = "unknown"
    visa_sponsorship: str = "unknown"
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = ""
    salary_period: str = ""
    posted_at: str = ""
    valid_through: str = ""
    eligibility_status: str = "unknown"
    eligibility_evidence: str = ""
    source_credit: str = ""
    last_checked_at: str = field(default_factory=utc_now)


@dataclass
class FitDimension:
    score: float
    confidence: float
    probabilities: dict[str, float] = field(default_factory=dict)


@dataclass
class FitResult:
    dimensions: dict[str, FitDimension]
    combined_score: float
    confidence: float
    evidence: list[str]
    model: str
    input_tokens: int


def profile_from_row(row: Any | None) -> CandidateProfile:
    if row is None:
        return CandidateProfile()
    return CandidateProfile(**{field: row[field] for field in CandidateProfile.__dataclass_fields__})


def criteria_from_json(values: dict[str, Any] | None) -> SearchCriteria:
    if not values:
        return SearchCriteria()
    allowed = SearchCriteria.__dataclass_fields__
    return SearchCriteria(**{key: value for key, value in values.items() if key in allowed})
