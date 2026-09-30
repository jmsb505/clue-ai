from __future__ import annotations

from datetime import datetime, timezone

import pytest

from clue_ai.config import Settings
from clue_ai.database import initialize
from clue_ai.domain import NormalizedJob


@pytest.fixture
def settings(tmp_path):
    return Settings(
        data_dir=tmp_path / "data",
        api_key="",
        model="jev-1.13.0",
        monthly_jev_budget_usd=4.0,
    )


@pytest.fixture
def database(settings):
    initialize(settings.database_path)
    return settings.database_path


def make_job(
    *,
    source_id="jobicy",
    url="https://jobs.example.org/openings/software-engineer",
    title="Software Engineer",
    company="Example Labs",
    location="Europe",
    description=(
        "Remote software engineer role open to candidates in Italy and across Europe. "
        "Build Python services, review production systems, work with product teams, "
        "and improve reliability, observability, testing, deployment, and documentation. "
        "The team collaborates across several European time zones."
    ),
):
    return NormalizedJob(
        source_id=source_id,
        source_name=source_id.title(),
        external_id=f"{source_id}-listing-1",
        title=title,
        company=company,
        description=description,
        source_url=url,
        canonical_url=url,
        location_raw=location,
        workplace_type="remote",
        employment_type="full-time",
        posted_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        source_credit=source_id.title(),
    )
