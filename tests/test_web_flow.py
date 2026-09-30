from __future__ import annotations

import io
from urllib.parse import urlparse

import pytest
from conftest import make_job
from docx import Document
from fastapi.testclient import TestClient

from clue_ai.database import get_profile, save_search_run
from clue_ai.domain import CandidateProfile, SearchCriteria
from clue_ai.repository import add_source, get_run_results, get_source, list_sources, update_run
from clue_ai.sources import FetchOutcome
from clue_ai.web import create_app

ORIGIN = {"Origin": "http://127.0.0.1"}


def test_local_views_render_without_a_jev_key(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")

    for route in ("/", "/profile", "/search", "/saved", "/hidden", "/sources", "/settings", "/privacy", "/health"):
        response = client.get(route)
        assert response.status_code == 200, route
    assert client.get("/health").json() == {"status": "ok", "storage": "local"}


@pytest.mark.parametrize(
    ("route", "current_href"),
    (
        ("/", "/"),
        ("/profile", "/profile"),
        ("/search", "/search"),
        ("/saved", "/saved"),
        ("/hidden", "/hidden"),
        ("/sources", "/sources"),
        ("/settings", "/settings"),
    ),
)
def test_primary_navigation_names_groups_and_marks_current_page(settings, route, current_href):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")

    response = client.get(route)

    assert response.status_code == 200
    assert 'aria-label="Your search"' in response.text
    assert 'aria-label="Workspace"' in response.text
    assert f'<a href="{current_href}" class="is-active" aria-current="page">' in response.text


def test_result_status_poller_only_runs_for_active_searches(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")

    save_search_run(settings.database_path, "run-polling", SearchCriteria())
    active = client.get("/searches/run-polling")
    assert active.status_code == 200
    assert '/static/poll.js' in active.text

    update_run(
        settings.database_path,
        "run-polling",
        status="complete",
        stage="complete",
        message="Search complete.",
        completed=True,
    )
    complete = client.get("/searches/run-polling")
    assert complete.status_code == 200
    assert '/static/poll.js' not in complete.text


def test_jev_settings_state_external_data_and_local_budget_limits(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")

    response = client.get("/settings")

    assert response.status_code == 200
    assert "Work history and skills can still identify you." in response.text
    assert "Clue does not inspect your TypeSafe account terms" in response.text
    assert "it cannot guarantee account-wide charges" in response.text
    assert "Clue does not read or control account refill settings" in response.text
    assert "I understand which profile facts and listing details leave this device" in response.text
    assert "I have reviewed the data disclosure and TypeSafe terms above" not in response.text
    assert "The five built-in public source definitions remain." in response.text


def test_localhost_and_same_origin_boundaries_reject_cross_origin_requests(settings):
    app = create_app(settings)
    local = TestClient(app, base_url="http://127.0.0.1")
    remote = TestClient(app, base_url="http://attacker.example")

    assert remote.get("/").status_code == 421
    response = local.post(
        "/settings/jev-consent", data={"agree": "on"}, headers={"Origin": "https://attacker.example"}
    )
    assert response.status_code == 403


def test_source_management_requires_review_before_enabling(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    response = client.post(
        "/sources/add",
        data={"kind": "greenhouse", "company": "Example", "identifier": "example"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    source_id = next(
        item["id"] for item in list_sources(settings.database_path) if item["id"].startswith("user-")
    )
    source = get_source(settings.database_path, source_id)
    assert response.status_code == 303
    assert source["state"] == "review"
    assert source["enabled"] == 0

    incomplete = client.post(
        f"/sources/{source_id}/approve",
        data={"terms_reviewed": "on"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert incomplete.status_code == 303
    assert get_source(settings.database_path, source_id)["enabled"] == 0

    reviewed = client.post(
        f"/sources/{source_id}/approve",
        data={
            key: "on"
            for key in (
                "terms_reviewed",
                "zero_cost",
                "attribution_confirmed",
                "robots_confirmed",
                "public_access_confirmed",
            )
        },
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert reviewed.status_code == 303
    assert get_source(settings.database_path, source_id)["state"] == "approved"
    assert get_source(settings.database_path, source_id)["enabled"] == 1


def test_lever_source_form_records_the_selected_region(settings):
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    response = client.post(
        "/sources/add",
        data={
            "kind": "lever",
            "company": "Prima",
            "identifier": "prima",
            "lever_region": "eu",
        },
        headers=ORIGIN,
        follow_redirects=False,
    )
    source = next(item for item in list_sources(settings.database_path) if item["name"] == "Prima")

    assert response.status_code == 303
    assert source["state"] == "review"
    assert source["enabled"] == 0
    assert source["endpoint"] == "https://api.eu.lever.co/v0/postings/prima?mode=json"
    assert source["config"]["region"] == "eu"


def test_search_to_results_save_hide_and_delete_uses_mocked_sources_only(
    settings, monkeypatch
):
    from clue_ai import services

    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    add_source(
        settings.database_path,
        name="Under review",
        kind="greenhouse",
        endpoint="https://boards-api.greenhouse.io/v1/boards/review/jobs",
        config={"board_token": "review"},
        attribution="Under review",
    )
    calls = []

    base_job = make_job()

    def fake_fetch(source, *_args):
        calls.append(source["id"])
        job = make_job(
            source_id=source["id"],
            url=base_job.canonical_url,
            title=base_job.title,
            company=base_job.company,
            location=base_job.location_raw,
            description=base_job.description,
        )
        job.posted_at = base_job.posted_at
        return FetchOutcome(
            jobs=[job],
            checked=1,
            response_bytes=1_024,
            raw_records=1,
            status_counts={"status_200": 1},
        )

    monkeypatch.setattr(services, "fetch_source", fake_fetch)
    response = client.post(
        "/search",
        data={"roles": "Software Engineer", "work_from": "Italy", "workplace": "remote"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert response.status_code == 303
    results_url = response.headers["location"]
    run_id = results_url.rsplit("/", 1)[-1]
    results = client.get(results_url)

    assert results.status_code == 200
    assert "Software Engineer" in results.text
    assert 'href="https://jobs.example.org/openings/software-engineer"' in results.text
    assert "Fit not evaluated" in results.text or "not evaluated" in results.text.casefold()
    assert "HTTP 200" in results.text
    assert set(calls) == {"jobicy", "remotejobs", "remoteok", "remotefirstjobs", "startupjobs"}
    assert "Powered by RemoteJobs.org" in results.text
    assert not any(call.startswith("user-") for call in calls)
    row = get_run_results(settings.database_path, run_id)[0]
    assert row["eligibility_status"] == "eligible"
    assert row["eligibility_evidence"]
    assert row["score_state"] == "unscored"

    saved = client.post(
        f"/jobs/{row['id']}/save",
        data={"return_to": results_url},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert saved.status_code == 303
    saved_page = client.get("/saved")
    assert "Software Engineer" in saved_page.text
    assert "Powered by RemoteJobs.org" in saved_page.text
    hidden = client.post(
        f"/jobs/{row['id']}/hide",
        data={"return_to": results_url},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert hidden.status_code == 303
    hidden_page = client.get("/hidden")
    assert "Software Engineer" in hidden_page.text
    assert "Powered by RemoteJobs.org" in hidden_page.text

    deleted = client.post(
        "/data/delete",
        data={"confirmation": "DELETE"},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert "Local+profile" in deleted.headers["location"]
    assert get_profile(settings.database_path) == CandidateProfile()


def test_cv_upload_is_held_for_review_then_saved_locally_and_removable(settings):
    document = Document()
    document.add_heading("Summary", level=1)
    document.add_paragraph(
        "Synthetic candidate profile with enough selectable text to test local document extraction."
    )
    output = io.BytesIO()
    document.save(output)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1")
    extracted = client.post(
        "/profile/extract",
        files={"cv_file": ("synthetic.docx", output.getvalue(), "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert extracted.status_code == 303
    pending_id = urlparse(extracted.headers["location"]).query.split("=")[-1]
    review_page = client.get(extracted.headers["location"])
    assert "Synthetic candidate profile" in review_page.text

    saved = client.post(
        "/profile/save",
        data={
            "pending_id": pending_id,
            "target_roles": "Software Engineer",
            "skills": "Python, SQL",
            "profile_language": "en",
        },
        headers=ORIGIN,
        follow_redirects=False,
    )
    assert saved.status_code == 303
    profile = get_profile(settings.database_path)
    assert profile.target_roles == "Software Engineer"
    assert profile.cv_path
    assert profile.extracted_text.startswith("Summary")

    removed = client.post("/profile/remove-cv", headers=ORIGIN, follow_redirects=False)
    assert removed.status_code == 303
    profile = get_profile(settings.database_path)
    assert profile.target_roles == "Software Engineer"
    assert profile.cv_path == ""
    assert profile.extracted_text == ""
