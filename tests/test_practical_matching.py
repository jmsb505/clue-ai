from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest
from conftest import make_job
from fastapi.testclient import TestClient

from clue_ai.database import save_search_run, set_jev_consent
from clue_ai.domain import CandidateProfile, SearchCriteria
from clue_ai.jev import FILTER_CHECK_INSTRUCTIONS, _build_request_state, score_run
from clue_ai.repository import (
    all_active_jobs,
    get_run_result_counts,
    get_run_results,
    save_jobs,
    save_run_results,
    set_job_user_state,
    update_run,
    update_score,
)
from clue_ai.resume import parse_candidate_profile
from clue_ai.web import create_app


@pytest.mark.parametrize(
    ("changed_check", "choice", "confidence", "omit", "expected"),
    [
        ("pay", "match", 0.95, False, "match"),
        ("pay", "review", 0.95, False, "review"),
        ("pay", "conflict", 0.95, False, "conflict"),
        ("seniority", "conflict", 0.95, False, "conflict"),
        ("location", "conflict", 0.95, False, "conflict"),
        ("location", "conflict", 0.55, False, "conflict"),
        ("pay", "match", 0.55, False, "match"),
        ("pay", "conflict", float("nan"), False, "review"),
        ("pay", "conflict", float("inf"), False, "review"),
        ("pay", "match", 0.95, True, "unassessed"),
        ("pay", "unsupported", 0.95, False, "unassessed"),
    ],
)
def test_independent_jev_checks_preserve_uncertainty_and_explicit_exclusions(
    settings, database, changed_check, choice, confidence, omit, expected
):
    settings = replace(settings, api_key="synthetic-key")
    save_search_run(database, "checks", SearchCriteria(roles="AI Engineer, Data Analyst"))
    save_jobs(database, [make_job(title="Graduate Python Developer")])
    save_run_results(database, "checks", all_active_jobs(database))
    set_jev_consent(database, True)
    calls = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def system_one(self, *, state, questions):
            calls.append(state)
            answers = {}
            for name in questions:
                label = "match" if "_filter_" in name else "4"
                certainty = 0.95
                if name.endswith(f"filter_{changed_check}"):
                    if omit:
                        continue
                    label, certainty = choice, confidence
                answers[name] = SimpleNamespace(choice=label, confidence=certainty, probabilities={})
            return SimpleNamespace(usage=SimpleNamespace(input_tokens=1000), choices=answers)

    result = score_run(
        database, settings, "checks", get_run_results(database, "checks"),
        CandidateProfile(target_roles="AI Engineer", skills="Python"), SearchCriteria(),
        client_factory=lambda **_kwargs: FakeClient(),
    )
    job = get_run_results(database, "checks")[0]
    assert len(calls) == 1
    assert job["combined_score"] == 1.0  # Requirement checks never alter weighted fit.
    assert job["filter_status"] == expected
    assert result.filter_match_count == int(expected == "match")
    if expected != "unassessed":
        check = job["dimensions"][f"filter_{changed_check}"]
        assert check["model_status"] == choice
        assert check["status"] == ("review" if expected == "review" else choice)
        assert all(f"filter_{name}" in job["dimensions"] for name in FILTER_CHECK_INSTRUCTIONS)
    if expected == "review":
        assert any("Verify these requirements" in line for line in job["evidence"])


@pytest.mark.parametrize("omit_pay", [False, True])
def test_filter_only_retry_preserves_existing_fit_scores_and_records_checks(settings, database, omit_pay):
    settings = replace(settings, api_key="synthetic-key")
    save_search_run(database, "retry", SearchCriteria())
    save_jobs(database, [make_job()])
    save_run_results(database, "retry", all_active_jobs(database))
    job_id = get_run_results(database, "retry")[0]["id"]
    update_score(
        database, "retry", job_id, score_state="scored", combined_score=0.6,
        dimensions={"role": {"score": 0.6, "confidence": 0.9},
                    "filter_pay": {"status": "conflict", "score": None}},
        filter_status="unassessed",
    )
    set_jev_consent(database, True)

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def system_one(self, *, state, questions):
            return SimpleNamespace(
                usage=SimpleNamespace(input_tokens=1000),
                choices={
                    key: SimpleNamespace(choice="review", confidence=0.95)
                    for key in questions if "_filter_" in key
                    and not (omit_pay and key.endswith("_filter_pay"))
                },
            )

    score_run(
        database, settings, "retry", get_run_results(database, "retry"),
        CandidateProfile(skills="Python"), SearchCriteria(),
        client_factory=lambda **_kwargs: FakeClient(),
    )
    job = get_run_results(database, "retry")[0]
    assert job["combined_score"] == 0.6
    assert job["score_state"] == "scored"
    assert job["dimensions"]["role"]["score"] == 0.6
    assert job["filter_checks"]["seniority"]["status"] == "review"
    if omit_pay:
        assert "pay" not in job["filter_checks"]
        assert job["filter_status"] == "unassessed"
    else:
        assert job["filter_checks"]["pay"]["status"] == "review"
        assert job["filter_status"] == "review"


def test_listing_pay_details_and_sponsorship_survive_the_jev_input_path(settings, database):
    job = replace(make_job(), description="Role details. " * 430 + "Paid graduate role.",
                  visa_sponsorship="yes")
    save_search_run(database, "details", SearchCriteria())
    save_jobs(database, [job])
    save_run_results(database, "details", all_active_jobs(database))
    stored = get_run_results(database, "details")
    state, _, _ = _build_request_state(stored, CandidateProfile(skills="Python"),
                                      SearchCriteria(), settings)
    assert state["jobs"][0]["visa_sponsorship"] == "yes"
    assert state["jobs"][0]["description"].endswith("Paid graduate role.")
    assert len(state["jobs"][0]["description"]) <= settings.max_job_description_chars


def seed_ranked_results(database):
    save_search_run(database, "ranked", SearchCriteria())
    specs = [
        ("Confirmed junior", "match", 0.5),
        ("Related AI graduate", "review", 0.9),
        ("Senior conflict", "conflict", 0.95),
        ("Pending role", "unassessed", 0.95),
        ("Hidden lead", "review", 1.0),
    ]
    save_jobs(database, [
        replace(make_job(title=title, url=f"https://jobs.example.org/{i}"), external_id=f"rank-{i}")
        for i, (title, _, _) in enumerate(specs)
    ])
    save_run_results(database, "ranked", all_active_jobs(database))
    by_title = {j["title"]: j for j in get_run_results(database, "ranked")}
    for title, status, score in specs:
        dimensions = {"role": {"score": score, "confidence": 0.95}}
        for key in FILTER_CHECK_INSTRUCTIONS:
            dimensions[f"filter_{key}"] = {
                "score": None, "status": "review", "model_status": "review", "confidence": 0.95,
            }
        update_score(database, "ranked", by_title[title]["id"], score_state="scored",
                     combined_score=score, filter_status=status, rubric_version="fit-v1.4.0",
                     dimensions=dimensions)
    set_job_user_state(database, by_title["Hidden lead"]["id"], "hidden")
    update_run(database, "ranked", status="complete", completed=True)


def test_opportunities_rank_review_by_fit_with_exact_counts_and_pagination(database):
    seed_ranked_results(database)
    counts = get_run_result_counts(database, "ranked")
    assert counts["opportunities"] == 2
    assert counts["matches"] == counts["review"] == counts["conflicts"] == counts["unassessed"] == 1
    assert counts["total"] == 4
    first = get_run_results(database, "ranked", filter_status="opportunities", limit=1)
    second = get_run_results(database, "ranked", filter_status="opportunities", limit=1, offset=1)
    assert first[0]["title"] == "Related AI graduate"
    assert second[0]["title"] == "Confirmed junior"


def test_results_default_to_opportunities_with_filter_details_and_all_view(settings, database):
    seed_ranked_results(database)
    client = TestClient(create_app(settings))
    response = client.get("/searches/ranked")
    assert response.status_code == 200
    assert "2 potential opportunities" in response.text
    assert response.text.index("Related AI graduate") < response.text.index("Confirmed junior")
    assert "Senior conflict" not in response.text
    assert "Pending role" not in response.text
    assert "Hidden lead" not in response.text
    assert "Requirement checks" in response.text
    assert "Paid compensation" in response.text
    assert "Needs verification" in response.text
    assert 'https://jobs.example.org/1' in response.text
    all_results = client.get("/searches/ranked?view=all")
    assert all_results.status_code == 200
    assert "Senior conflict" in all_results.text
    assert "Pending role" in all_results.text
    assert "Hidden lead" not in all_results.text
    assert client.get("/searches/ranked?view=match").status_code == 200


@pytest.mark.parametrize("heading", ["", "Target roles\n"])
def test_cv_action_sentence_does_not_become_a_required_job_title(heading):
    text = (
        f"{heading}AI/ML Engineer\n"
        "Connects technical decisions with product design and business needs\n"
        "Freelance Data Analyst\nSkills\nPython, SQL, Machine Learning\n"
    )
    profile = parse_candidate_profile(text)
    assert "Connects" not in profile["target_roles"]
    assert "AI/ML Engineer" in profile["target_roles"]
    assert "Data Analyst" in profile["target_roles"]


def test_opportunities_second_page_uses_its_filtered_count_and_preserves_view(settings, database):
    save_search_run(database, "pages", SearchCriteria())
    save_jobs(database, [
        replace(make_job(title=f"Lead {i:02}", url=f"https://jobs.example.org/pages/{i}"),
                external_id=f"page-{i}")
        for i in range(53)
    ])
    save_run_results(database, "pages", all_active_jobs(database))
    for job in get_run_results(database, "pages"):
        index = int(job["title"].split()[-1])
        update_score(database, "pages", job["id"], score_state="scored", combined_score=index / 100,
                     filter_status="review" if index < 51 else "conflict")
    update_run(database, "pages", status="complete", completed=True)
    response = TestClient(create_app(settings)).get("/searches/pages?view=opportunities&page=2")
    assert response.status_code == 200
    assert "51 potential opportunities" in response.text
    assert "Page 2 of 2" in response.text
    assert "Lead 00" in response.text
    assert "Lead 50" not in response.text
    assert "Lead 51" not in response.text
    assert "view=opportunities&amp;page=1" in response.text
