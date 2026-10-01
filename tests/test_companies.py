from __future__ import annotations

from fastapi.testclient import TestClient

from clue_ai.company_catalog import filter_and_rank_companies, profile_role_codes
from clue_ai.domain import CandidateProfile
from clue_ai.repository import (
    list_companies,
    retry_company_board,
    set_company_tracked,
    update_company_board,
)
from clue_ai.web import create_app

ORIGIN = {"Origin": "http://127.0.0.1"}


def test_company_catalog_is_broad_and_uses_https_official_sites(database):
    companies = list_companies(database)

    assert len(companies) >= 75
    assert {company["group_id"] for company in companies} == {
        "italian-ai",
        "italian-tech",
        "europe-ai",
        "data-platform",
        "global-tech",
    }
    assert all(company["homepage_url"].startswith("https://") for company in companies)
    assert all(company["discovery_url"].startswith("https://") for company in companies)
    assert all(company["tracked"] for company in companies)


def test_known_boards_only_use_explicit_official_urls(database):
    companies = {company["id"]: company for company in list_companies(database)}

    assert companies["akamas"]["board_url"] == "https://careers.akamas.io/"
    assert (
        companies["multiverse-computing"]["board_url"]
        == "https://multiversecomputing.teamtailor.com/"
    )
    assert companies["qdrant"]["board_url"] == "https://jobs.ashbyhq.com/qdrant.tech"
    assert companies["mistral-ai"]["board_url"] == ""


def test_profile_match_is_local_and_filters_by_group(database):
    profile = CandidateProfile(
        target_roles="Machine Learning Engineer and AI Product Engineer",
        skills="Python, PyTorch, NLP, RAG, model serving, SQL",
    )
    companies = list_companies(database)

    matched = filter_and_rank_companies(companies, group_id="europe-ai", profile=profile)

    assert matched
    assert all(company["group_id"] == "europe-ai" for company in matched)
    assert matched[0]["profile_match_count"] > 0
    assert {"ai_ml", "llm_nlp", "ml_platform"}.issubset(profile_role_codes(profile))


def test_directory_searches_company_names_and_role_tags(database):
    companies = list_companies(database)

    by_name = filter_and_rank_companies(companies, query="Aindo")
    by_role = filter_and_rank_companies(companies, query="LLM")

    assert [company["id"] for company in by_name] == ["aindo"]
    assert by_role
    assert all("LLM / NLP" in company["role_labels"] for company in by_role)


def test_company_track_state_persists_and_unknown_ids_do_not_mutate(database):
    assert set_company_tracked(database, "aindo", False)
    assert not set_company_tracked(database, "not-a-company", True)
    assert (
        next(company for company in list_companies(database) if company["id"] == "aindo")["tracked"]
        == 0
    )


def test_companies_page_renders_directory_without_claiming_current_vacancies(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")

    response = client.get("/companies?group=italian-ai&q=AI")

    assert response.status_code == 200
    assert 'aria-current="page"' in response.text
    assert "COMPANY BOARD COVERAGE" in response.text
    assert (
        "an employer's role and location terms still determine whether a job fits." in response.text
    )
    assert "https://www.aindo.com/careers/" in response.text


def test_company_tracking_actions_work_through_same_origin_forms(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")

    removed = client.post(
        "/companies/aindo/untrack",
        data={"return_to": "/companies?group=italian-ai"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    restored = client.post("/companies/aindo/track", headers=ORIGIN, follow_redirects=False)
    unknown = client.post("/companies/not-a-company/track", headers=ORIGIN, follow_redirects=False)

    assert removed.status_code == 303
    assert removed.headers["location"] == "/companies?group=italian-ai"
    assert restored.status_code == 303
    assert unknown.status_code == 404
    assert (
        next(
            company
            for company in list_companies(settings.database_path)
            if company["id"] == "aindo"
        )["tracked"]
        == 1
    )


def test_blocked_company_source_can_be_retried_from_directory(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    update_company_board(
        settings.database_path,
        "qdrant",
        board_state="blocked",
        last_state="blocked",
        board_url="https://jobs.ashbyhq.com/qdrant.tech",
        provider="ashby",
        error="HTTP 429.",
    )
    page = client.get("/companies?q=Qdrant")
    retried = client.post(
        "/companies/qdrant/retry",
        data={"return_to": "/companies?q=Qdrant"},
        headers=ORIGIN,
        follow_redirects=False,
    )

    assert page.status_code == 200
    assert "Retry this source" in page.text
    assert retried.status_code == 303
    qdrant = next(
        company for company in list_companies(settings.database_path) if company["id"] == "qdrant"
    )
    assert qdrant["board_state"] == "candidate"
    assert retry_company_board(settings.database_path, "qdrant") is False
