from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from clue_ai.application_followups import (
    cancel_followup_for_request,
    cancel_followups_for_closed_jobs,
    finish_followup,
    list_followups,
    schedule_followup,
)
from clue_ai.application_prep import (
    add_source as add_preparation_source,
)
from clue_ai.application_prep import (
    approved_claims,
    get_preparation,
    get_writing_preferences,
    list_claims,
    list_preparations,
    request_preparation,
    review_claim,
    save_writing_preferences,
    set_source_options,
    suggest_claims,
    suppress_researched_contact,
)
from clue_ai.application_prep import (
    get_source as get_preparation_source,
)
from clue_ai.application_prep import (
    list_sources as list_preparation_sources,
)
from clue_ai.application_workflow import (
    approve_packet,
    create_practice_session,
    get_packet,
    list_practice_sessions,
    queue_practice_answers,
    run_interview_practice_assessment,
    run_interview_practice_questions,
    run_preparation,
    verify_packet_approval,
)
from clue_ai.applications import (
    applied_jobs,
    find_applied_snapshot,
    mark_applied,
    mark_snapshot_applied,
    undo_applied,
)
from clue_ai.company_catalog import GROUP_LABELS, filter_and_rank_companies
from clue_ai.config import Settings
from clue_ai.database import (
    connect,
    delete_personal_data,
    get_profile,
    get_settings,
    initialize,
    recover_interrupted_gmail_drafts,
    save_openai_controls,
    save_profile,
    save_search_run,
    set_gmail_connection,
    set_jev_consent,
)
from clue_ai.domain import CandidateProfile, NormalizedJob, SearchCriteria, utc_now
from clue_ai.external_links import (
    build_x_search_url,
    normalize_public_job_url,
    normalize_x_status_url,
)
from clue_ai.feedback import (
    get_packet_feedback,
    outcome_summary,
    record_interview_feedback,
    record_packet_feedback,
    record_stage,
)
from clue_ai.filters import criteria_from_form
from clue_ai.gmail_drafts import (
    GmailDraftError,
    WindowsDPAPITokenStore,
    create_approved_packet_draft,
    start_local_oauth,
)
from clue_ai.jev import FILTER_CHECK_LABELS
from clue_ai.job_focus import focused_roles
from clue_ai.openai_provider import monthly_usage as monthly_openai_usage
from clue_ai.repository import (
    add_source,
    claim_scoring_run,
    clear_job_user_state,
    get_latest_run,
    get_run,
    get_run_result_counts,
    get_run_results,
    get_source,
    has_active_runs,
    hidden_jobs,
    list_companies,
    list_sources,
    manual_x_leads,
    mark_source_for_review,
    monthly_jev_usage,
    remove_user_source,
    retry_company_board,
    save_jobs,
    saved_jobs,
    set_company_tracked,
    set_job_user_state,
    set_source_enabled,
)
from clue_ai.resume import (
    ResumeError,
    extract_resume_text,
    parse_candidate_profile,
    suggest_profile_sections,
)
from clue_ai.services import run_jev_scoring, run_search_worker
from clue_ai.sources import validate_career_url

LOGGER = logging.getLogger("clue_ai")
PENDING_PATTERN = re.compile(r"^[a-f0-9]{32}$")
SOURCE_KINDS = {
    "greenhouse": "Greenhouse public board",
    "lever": "Lever public board",
    "smartrecruiters": "SmartRecruiters public board",
    "scrapling": "Employer careers page (Scrapling)",
    "jobicy_api": "Jobicy public API",
    "remotejobs_api": "RemoteJobs.org public API",
    "remoteok_json": "Remote OK public JSON feed",
    "weworkremotely_rss": "We Work Remotely public RSS feed",
    "himalayas_api": "Himalayas public JSON API",
    "remotive_api": "Remotive public JSON API",
    "workingnomads_api": "Working Nomads public JSON feed",
    "justremote_scrapling": "JustRemote public pages (Scrapling)",
    "remote_first_rss": "Remote First Jobs role RSS",
    "startup_rss": "Startup Jobs public RSS feed",
    "manual_board": "Manual link-out",
    "manual_x": "Manual X lead source",
}
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1", "testserver"}
LOCAL_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def create_app(
    settings: Settings | None = None,
    database_path: Path | None = None,
) -> FastAPI:
    current_settings = settings or Settings.from_environment()
    db_path = database_path or current_settings.database_path
    initialize(db_path)
    recover_interrupted_gmail_drafts(db_path)
    current_settings.data_dir.mkdir(parents=True, exist_ok=True)
    current_settings.cv_dir.mkdir(parents=True, exist_ok=True)
    _cleanup_pending_uploads(current_settings.cv_dir)

    app = FastAPI(
        title="Clue AI",
        description="Private, local job discovery and TypeSafe Jev fit review.",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.settings = current_settings
    app.state.database_path = db_path
    app.mount(
        "/static",
        StaticFiles(directory=Path(__file__).parent / "static"),
        name="static",
    )
    templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
    app.state.templates = templates
    operation_lock = threading.Lock()

    def run_search_serialized(run_id: str, auto_jev: bool = True) -> None:
        with operation_lock:
            run_search_worker(db_path, current_settings, run_id, auto_jev=auto_jev)

    def run_scoring_serialized(run_id: str) -> None:
        with operation_lock:
            run_jev_scoring(db_path, current_settings, run_id)

    def run_preparation_serialized(request_id: str) -> None:
        with operation_lock:
            run_preparation(db_path, current_settings, request_id)

    def run_practice_questions_serialized(session_id: str) -> None:
        with operation_lock:
            run_interview_practice_questions(db_path, current_settings, session_id)

    def run_practice_assessment_serialized(session_id: str) -> None:
        with operation_lock:
            run_interview_practice_assessment(db_path, current_settings, session_id)

    @app.middleware("http")
    async def local_request_boundary(request: Request, call_next):
        hostname = (request.url.hostname or "").lower()
        if hostname not in LOCAL_HOSTS:
            return Response("This app accepts requests from this device only.", status_code=421)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            request_scheme = request.url.scheme.casefold()
            request_port = request.url.port or (443 if request_scheme == "https" else 80)
            fetch_site = request.headers.get("sec-fetch-site", "").casefold()
            if fetch_site == "same-origin":
                source_url = ""
            elif fetch_site == "cross-site":
                # Embedded local browsers can label a loopback POST cross-site because the
                # containing app has a different origin. Trust only an exact local Origin.
                source_url = request.headers.get("origin", "").strip()
                if not source_url or source_url.casefold() == "null":
                    return Response(
                        "Cross-origin form submissions are not accepted.", status_code=403
                    )
            else:
                origin = request.headers.get("origin", "").strip()
                referer = request.headers.get("referer", "").strip()
                source_url = referer if origin.casefold() == "null" else origin or referer
            if not source_url:
                if fetch_site != "same-origin":
                    return Response("A same-origin browser request is required.", status_code=403)
            else:
                source_parts = urlsplit(source_url)
                source_hostname = (source_parts.hostname or "").lower()
                source_scheme = source_parts.scheme.casefold()
                try:
                    source_port = source_parts.port or (443 if source_scheme == "https" else 80)
                except ValueError:
                    source_port = -1
                same_local_host = source_hostname == hostname or (
                    source_hostname in LOCAL_LOOPBACK_HOSTS and hostname in LOCAL_LOOPBACK_HOSTS
                )
                if (
                    source_scheme not in {"http", "https"}
                    or source_scheme != request_scheme
                    or not same_local_host
                    or source_port != request_port
                ):
                    return Response(
                        "Cross-origin form submissions are not accepted.", status_code=403
                    )
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; "
            "base-uri 'self'; form-action 'self'"
        )
        return response

    def render(
        request: Request,
        name: str,
        context: dict | None = None,
        status_code: int = 200,
    ) -> HTMLResponse:
        values = {
            "request": request,
            "active_page": "",
            "jev_key_configured": bool(current_settings.api_key),
            "jev_consented": bool(get_settings(db_path).get("jev_consent_at")),
        }
        values.update(context or {})
        return templates.TemplateResponse(
            request=request,
            name=name,
            context=values,
            status_code=status_code,
        )

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        profile = get_profile(db_path)
        latest = get_latest_run(db_path)
        sources = list_sources(db_path)
        enabled_sources = [
            source for source in sources if source["enabled"] and source["state"] == "approved"
        ]
        return render(
            request,
            "home.html",
            {
                "active_page": "home",
                "profile": profile,
                "latest_run": latest,
                "approved_source_count": len(enabled_sources),
                "sources": enabled_sources,
                "profile_ready": bool(
                    profile.target_roles or profile.summary or profile.skills or profile.experience
                ),
                "jev_consented": bool(get_settings(db_path).get("jev_consent_at")),
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/profile", response_class=HTMLResponse)
    async def profile_page(request: Request):
        profile = get_profile(db_path)
        pending_id = request.query_params.get("pending", "")
        pending_text = ""
        if pending_id:
            pending_text = _read_pending_text(current_settings.cv_dir, pending_id)
            if not pending_text:
                pending_id = ""
        suggestions = suggest_profile_sections(pending_text) if pending_text else {}
        return render(
            request,
            "profile.html",
            {
                "active_page": "profile",
                "profile": profile,
                "suggestions": suggestions,
                "pending_id": pending_id,
                "pending_name": _read_pending_name(current_settings.cv_dir, pending_id),
                "pending_text": pending_text,
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/evidence", response_class=HTMLResponse)
    async def evidence_page(request: Request):
        preferences = get_writing_preferences(db_path)
        return render(
            request,
            "evidence.html",
            {
                "active_page": "evidence",
                "sources": list_preparation_sources(db_path),
                "claims": list_claims(db_path),
                "writing_preferences": preferences,
                "source_types": {
                    "technical_profile": "Technical profile",
                    "descriptive_profile": "Descriptive profile",
                    "resume": "Resume / CV reference",
                    "writing_sample": "Writing sample",
                },
                "error": request.query_params.get("error", ""),
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/evidence/sources/{source_id}", response_class=HTMLResponse)
    async def evidence_source_detail(request: Request, source_id: str):
        source = get_preparation_source(db_path, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Evidence source not found.")
        return render(
            request,
            "evidence_source.html",
            {
                "active_page": "evidence",
                "source": source,
                "notice": "",
            },
        )

    @app.post("/evidence/upload")
    async def evidence_upload(
        request: Request,
        source_type: str = Form(),
        source_file: UploadFile | None = File(default=None),  # noqa: B008
    ):
        if source_file is None or not source_file.filename:
            return RedirectResponse("/evidence?error=Choose+a+source+file+first.", status_code=303)
        content = await source_file.read(current_settings.max_cv_bytes + 1)
        try:
            add_preparation_source(
                db_path, current_settings, source_file.filename, source_type, content
            )
        except (ResumeError, ValueError) as exc:
            return RedirectResponse(
                f"/evidence?{urlencode({'error': str(exc)})}", status_code=303
            )
        return RedirectResponse(
            "/evidence?notice=Source+stored+on+this+device+as+unapproved+evidence.",
            status_code=303,
        )

    @app.post("/evidence/sources/{source_id}/suggest-claims")
    async def evidence_suggest_claims(source_id: str):
        source = get_preparation_source(db_path, source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Evidence source not found.")
        count = suggest_claims(db_path, source_id)
        return RedirectResponse(
            f"/evidence?notice={count}+unreviewed+claim+suggestions+added.", status_code=303
        )

    @app.post("/evidence/sources/{source_id}/settings")
    async def evidence_source_settings(request: Request, source_id: str):
        form = dict(await request.form())
        try:
            updated = set_source_options(
                db_path,
                source_id,
                permitted=_checked(form.get("permitted")),
                default_cv=_checked(form.get("default_cv")),
                structure_policy=str(form.get("structure_policy") or "preserve"),
            )
        except ValueError as exc:
            return RedirectResponse(
                f"/evidence?{urlencode({'error': str(exc)})}", status_code=303
            )
        if not updated:
            raise HTTPException(status_code=404, detail="Evidence source not found.")
        return RedirectResponse("/evidence?notice=Source+preferences+saved.", status_code=303)

    @app.post("/evidence/writing-preferences")
    async def evidence_writing_preferences(request: Request):
        form = dict(await request.form())
        save_writing_preferences(db_path, str(form.get("content") or ""))
        return RedirectResponse(
            "/evidence?notice=Writing+preferences+saved+locally.", status_code=303
        )

    @app.post("/evidence/claims/{claim_id}/review")
    async def evidence_claim_review(request: Request, claim_id: str):
        form = dict(await request.form())
        try:
            updated = review_claim(
                db_path,
                claim_id,
                status=str(form.get("status") or "unreviewed"),
                evidence_level=str(form.get("evidence_level") or "unknown"),
                category=str(form.get("category") or "unclassified"),
                role_family=str(form.get("role_family") or ""),
                owner_note=str(form.get("owner_note") or ""),
            )
        except ValueError as exc:
            return RedirectResponse(
                f"/evidence?{urlencode({'error': str(exc)})}", status_code=303
            )
        if not updated:
            raise HTTPException(status_code=404, detail="Claim not found.")
        return RedirectResponse("/evidence?notice=Claim+review+saved.", status_code=303)

    @app.post("/profile/extract")
    async def profile_extract(
        request: Request,
        cv_file: UploadFile | None = File(default=None),  # noqa: B008 - FastAPI uses File as parameter metadata.
    ):
        if cv_file is None or not cv_file.filename:
            return RedirectResponse(
                "/profile?notice=Choose+a+PDF+or+DOCX+file+first.", status_code=303
            )
        content = await cv_file.read(current_settings.max_cv_bytes + 1)
        try:
            text = extract_resume_text(cv_file.filename, content, current_settings)
        except ResumeError as exc:
            return render(
                request,
                "profile.html",
                {
                    "active_page": "profile",
                    "profile": get_profile(db_path),
                    "suggestions": {},
                    "pending_id": "",
                    "pending_name": "",
                    "pending_text": "",
                    "error": str(exc),
                },
                status_code=400,
            )
        pending_id = uuid.uuid4().hex
        suffix = Path(cv_file.filename).suffix.lower()
        safe_name = _safe_filename(cv_file.filename, suffix)
        pending_file = current_settings.cv_dir / f"pending-{pending_id}{suffix}"
        pending_text_file = current_settings.cv_dir / f"pending-{pending_id}.txt"
        pending_name_file = current_settings.cv_dir / f"pending-{pending_id}.name"
        pending_file.write_bytes(content)
        pending_text_file.write_text(text, encoding="utf-8")
        pending_name_file.write_text(safe_name, encoding="utf-8")
        return RedirectResponse(f"/profile?pending={pending_id}", status_code=303)

    @app.post("/profile/save")
    async def profile_save(request: Request):
        form = dict(await request.form())
        current = get_profile(db_path)
        pending_id = str(form.get("pending_id") or "")
        extracted_text = current.extracted_text
        cv_filename = current.cv_filename
        cv_path = current.cv_path
        old_cv_to_delete: Path | None = None
        new_cv_to_delete: Path | None = None
        if pending_id and PENDING_PATTERN.fullmatch(pending_id):
            pending_text = _read_pending_text(current_settings.cv_dir, pending_id)
            pending_name = _read_pending_name(current_settings.cv_dir, pending_id)
            pending_files = list(current_settings.cv_dir.glob(f"pending-{pending_id}.*"))
            pending_file = next(
                (path for path in pending_files if path.suffix.lower() in {".pdf", ".docx"}),
                None,
            )
            if not pending_text or pending_file is None:
                return RedirectResponse(
                    "/profile?notice=The+temporary+CV+review+expired.+Please+upload+it+again.",
                    status_code=303,
                )
            stored_name = f"{uuid.uuid4().hex}{pending_file.suffix.lower()}"
            stored_path = current_settings.cv_dir / stored_name
            pending_file.replace(stored_path)
            old_path = Path(current.cv_path) if current.cv_path else None
            if (
                old_path
                and old_path.is_file()
                and old_path.parent.resolve() == current_settings.cv_dir.resolve()
                and old_path.resolve() != stored_path.resolve()
            ):
                old_cv_to_delete = old_path
            new_cv_to_delete = stored_path
            for path in pending_files:
                if path.exists():
                    path.unlink()
            extracted_text = pending_text
            cv_filename = _safe_filename(
                str(form.get("cv_filename") or pending_name or pending_file.name),
                pending_file.suffix,
            )
            cv_path = str(stored_path)
        profile = CandidateProfile(
            summary=_form_text(form, "summary", 2_500),
            target_roles=_form_text(form, "target_roles", 2_000),
            skills=_form_text(form, "skills", 8_000),
            experience=_form_text(form, "experience", 8_000),
            education=_form_text(form, "education", 4_000),
            languages=_form_text(form, "languages", 2_000),
            profile_language=_choice(
                form.get("profile_language"), {"en", "it", "other", "unknown"}
            ),
            work_authorized_countries=_form_text(form, "work_authorized_countries", 500),
            requires_sponsorship=_choice(
                form.get("requires_sponsorship"), {"yes", "no", "unknown"}
            ),
            cv_filename=cv_filename,
            cv_path=cv_path,
            extracted_text=extracted_text,
            updated_at=current.updated_at,
        )
        try:
            save_profile(db_path, profile)
        except Exception:
            if new_cv_to_delete and new_cv_to_delete.is_file():
                new_cv_to_delete.unlink()
            raise
        if old_cv_to_delete and old_cv_to_delete.is_file():
            old_cv_to_delete.unlink()
        return RedirectResponse("/profile?notice=Profile+saved+on+this+device.", status_code=303)

    @app.post("/workflow/start")
    async def start_cv_workflow(
        request: Request,
        background_tasks: BackgroundTasks,
        cv_file: UploadFile | None = File(default=None),  # noqa: B008 - FastAPI uses File as parameter metadata.
        jev_auto_score: str | None = Form(default=None),
    ):
        if not operation_lock.acquire(blocking=False):
            return RedirectResponse(
                "/?notice=Finish+the+current+local+search+before+starting+another.",
                status_code=303,
            )
        current_profile: CandidateProfile | None = None
        profile = CandidateProfile()
        profile_saved = False
        new_cv_path: Path | None = None
        try:
            current_profile = get_profile(db_path)
            profile = current_profile
            if has_active_runs(db_path):
                return RedirectResponse(
                    "/?notice=Finish+the+current+local+search+before+starting+another.",
                    status_code=303,
                )

            if cv_file is not None and cv_file.filename:
                content = await cv_file.read(current_settings.max_cv_bytes + 1)
                extracted_text = extract_resume_text(cv_file.filename, content, current_settings)
                parsed = parse_candidate_profile(extracted_text)
                suffix = Path(cv_file.filename).suffix.lower()
                safe_name = _safe_filename(cv_file.filename, suffix)
                new_cv_path = current_settings.cv_dir / f"{uuid.uuid4().hex}{suffix}"
                new_cv_path.write_bytes(content)
                profile = CandidateProfile(
                    **parsed,
                    work_authorized_countries=current_profile.work_authorized_countries,
                    requires_sponsorship=current_profile.requires_sponsorship,
                    cv_filename=safe_name,
                    cv_path=str(new_cv_path),
                    extracted_text=extracted_text,
                )
                save_profile(db_path, profile)
                profile_saved = True
            elif not (
                current_profile.target_roles
                or current_profile.skills
                or current_profile.experience
                or current_profile.summary
            ):
                return RedirectResponse(
                    "/?notice=Choose+a+PDF+or+DOCX+CV+to+start+your+first+search.",
                    status_code=303,
                )

            settings_row = get_settings(db_path)
            if _checked(jev_auto_score) and not settings_row.get("jev_consent_at"):
                set_jev_consent(db_path, True)

            latest = get_latest_run(db_path)
            if latest and latest.get("criteria"):
                criteria = criteria_from_form(latest["criteria"])
                if criteria.workplace == "remote":
                    criteria = replace(
                        criteria, workplace="remote_preferred", include_unknown_location=False
                    )
            else:
                criteria = SearchCriteria(
                    roles=focused_roles(profile.target_roles),
                    work_from=str(settings_row.get("default_work_from") or "Italy"),
                    requires_sponsorship=profile.requires_sponsorship,
                )
            if not criteria.roles.strip() and profile.target_roles.strip():
                criteria = replace(criteria, roles=profile.target_roles)

            run_id = uuid.uuid4().hex
            save_search_run(db_path, run_id, criteria)
            old_path = Path(current_profile.cv_path) if current_profile.cv_path else None
            if (
                new_cv_path
                and old_path
                and old_path.is_file()
                and old_path.parent.resolve() == current_settings.cv_dir.resolve()
                and old_path.resolve() != new_cv_path.resolve()
            ):
                try:
                    old_path.unlink()
                except OSError:
                    LOGGER.warning("Could not remove the replaced local CV file.")
        except ResumeError as exc:
            if new_cv_path and new_cv_path.is_file():
                new_cv_path.unlink()
            return RedirectResponse(f"/?notice={_url_message(str(exc))}", status_code=303)
        except Exception:
            if new_cv_path and new_cv_path.is_file():
                new_cv_path.unlink()
            if profile_saved and current_profile is not None:
                save_profile(db_path, current_profile)
            raise
        finally:
            operation_lock.release()

        background_tasks.add_task(run_search_serialized, run_id, True)
        return RedirectResponse(f"/searches/{run_id}", status_code=303)

    @app.post("/profile/remove-cv")
    async def remove_cv():
        profile = get_profile(db_path)
        cv_path = Path(profile.cv_path) if profile.cv_path else None
        save_profile(
            db_path,
            CandidateProfile(
                summary=profile.summary,
                target_roles=profile.target_roles,
                skills=profile.skills,
                experience=profile.experience,
                education=profile.education,
                languages=profile.languages,
                profile_language=profile.profile_language,
                work_authorized_countries=profile.work_authorized_countries,
                requires_sponsorship=profile.requires_sponsorship,
            ),
        )
        if (
            cv_path
            and cv_path.is_file()
            and cv_path.parent.resolve() == current_settings.cv_dir.resolve()
        ):
            cv_path.unlink()
        return RedirectResponse(
            "/profile?notice=CV+file+and+extracted+text+removed.", status_code=303
        )

    @app.get("/search", response_class=HTMLResponse)
    async def search_page(request: Request):
        profile = get_profile(db_path)
        source_run_id = request.query_params.get("from", "")
        source_run = get_run(db_path, source_run_id) if source_run_id else None
        latest = get_latest_run(db_path) if source_run is None else source_run
        if latest and latest.get("criteria"):
            criteria = criteria_from_form(latest["criteria"])
            if source_run is None and criteria.workplace == "remote":
                criteria = replace(
                    criteria, workplace="remote_preferred", include_unknown_location=False
                )
        else:
            criteria = SearchCriteria(
                roles=focused_roles(profile.target_roles),
                must_have="",
                work_from="Italy",
                requires_sponsorship=profile.requires_sponsorship,
            )
        return render(
            request,
            "search.html",
            {
                "active_page": "search",
                "criteria": criteria,
                "notice": request.query_params.get("notice", ""),
                "profile": profile,
            },
        )

    @app.post("/search")
    async def start_search(request: Request, background_tasks: BackgroundTasks):
        form = dict(await request.form())
        criteria = criteria_from_form(form)
        run_id = uuid.uuid4().hex
        if not operation_lock.acquire(blocking=False):
            return RedirectResponse(
                "/search?notice=Wait+for+the+current+local+search+operation+to+finish.",
                status_code=303,
            )
        try:
            if has_active_runs(db_path):
                return RedirectResponse(
                    "/search?notice=Finish+the+current+search+before+starting+another.",
                    status_code=303,
                )
            save_search_run(db_path, run_id, criteria)
        finally:
            operation_lock.release()
        background_tasks.add_task(run_search_serialized, run_id, True)
        return RedirectResponse(f"/searches/{run_id}", status_code=303)

    @app.get("/x-leads", response_class=HTMLResponse)
    async def x_leads_page(request: Request):
        profile = get_profile(db_path)
        latest = get_latest_run(db_path)
        saved_criteria = (
            latest.get("criteria")
            if latest and latest.get("criteria")
            else {"roles": profile.target_roles, "work_from": "Italy", "workplace": "remote"}
        )
        if not str(saved_criteria.get("roles") or "").strip():
            saved_criteria["roles"] = profile.target_roles
        roles = str(request.query_params.get("roles", saved_criteria.get("roles", "")))[:500]
        work_from = str(
            request.query_params.get("work_from", saved_criteria.get("work_from", "Italy"))
        )[:100]
        requested_workplace = request.query_params.get(
            "workplace", saved_criteria.get("workplace", "remote")
        )
        if str(requested_workplace).casefold() == "remote_preferred":
            requested_workplace = "remote"
        workplace = _choice(
            requested_workplace,
            {"remote", "hybrid", "onsite", "any"},
        )
        leads = manual_x_leads(db_path)
        for lead in leads:
            normalized = normalize_public_job_url(lead["job_url"])
            lead["job_host"] = normalized[1] if normalized else "Unknown host"
        return render(
            request,
            "x_leads.html",
            {
                "active_page": "x_leads",
                "roles": roles,
                "work_from": work_from,
                "workplace": workplace,
                "x_search_url": build_x_search_url(roles, work_from, workplace),
                "leads": leads,
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.post("/x-leads/add")
    async def add_x_lead_route(request: Request):
        form = dict(await request.form())
        title = _form_text(form, "title", 300)
        company = _form_text(form, "company", 250)
        location = _form_text(form, "location", 1_000)
        description = _form_text(form, "description", 20_000)
        x_post = normalize_x_status_url(_form_text(form, "post_url", 2_000))
        job_page = normalize_public_job_url(_form_text(form, "job_url", 2_000))
        workplace = _choice(form.get("workplace_type"), {"remote", "hybrid", "onsite", "unknown"})
        if not title or not description:
            return RedirectResponse(
                "/x-leads?notice=Add+a+job+title+and+details+copied+from+the+original+listing.",
                status_code=303,
            )
        if not _checked(form.get("reviewed")):
            return RedirectResponse(
                "/x-leads?notice=Confirm+that+you+reviewed+the+X+post+and+the+original+job+listing.",
                status_code=303,
            )
        if x_post is None:
            return RedirectResponse(
                "/x-leads?notice=Use+an+HTTPS+X.com+or+Twitter.com+post+permalink.",
                status_code=303,
            )
        if job_page is None:
            return RedirectResponse(
                "/x-leads?notice=Use+the+final+HTTPS+employer+or+ATS+listing+URL,+not+a+shortened+link.",
                status_code=303,
            )
        post_url, status_id = x_post
        job_url, _ = job_page
        if not operation_lock.acquire(blocking=False):
            return RedirectResponse(
                "/x-leads?notice=Wait+for+the+current+search+or+Jev+operation+to+finish+before+saving+a+lead.",
                status_code=303,
            )
        try:
            if has_active_runs(db_path):
                return RedirectResponse(
                    "/x-leads?notice=Wait+for+the+current+search+or+Jev+operation+to+finish+before+saving+a+lead.",
                    status_code=303,
                )
            saved = save_jobs(
                db_path,
                [
                    NormalizedJob(
                        source_id="x_manual",
                        source_name="X.com · manual lead",
                        external_id=f"{status_id}-{uuid.uuid5(uuid.NAMESPACE_URL, job_url).hex[:12]}",
                        title=title,
                        company=company,
                        description=description,
                        source_url=job_url,
                        canonical_url=job_url,
                        location_raw=location,
                        workplace_type=workplace,
                        context_url=post_url,
                        last_checked_at=utc_now(),
                    )
                ],
            )
        finally:
            operation_lock.release()
        if saved != 1:
            return RedirectResponse(
                "/x-leads?notice=Clue+could+not+save+that+link.+Check+the+URL+and+try+again.",
                status_code=303,
            )
        return RedirectResponse(
            "/x-leads?notice=Lead+saved+locally.+Run+your+search+to+filter+it,+then+choose+Score+with+Jev+if+you+want+fit+signals.",
            status_code=303,
        )

    @app.get("/searches/{run_id}", response_class=HTMLResponse)
    async def search_results(request: Request, run_id: str):
        run = get_run(db_path, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Search not found.")
        result_counts = get_run_result_counts(db_path, run_id)
        status_views = {
            "opportunities": "opportunities",
            "all": None,
            "match": "match",
            "review": "review",
            "conflict": "conflict",
            "unassessed": "unassessed",
        }
        status_count_keys = {
            "opportunities": "opportunities",
            "match": "matches",
            "review": "review",
            "conflict": "conflicts",
            "unassessed": "unassessed",
        }
        default_view = "opportunities" if result_counts["opportunities"] else "all"
        active_view = request.query_params.get("view", default_view)
        if active_view not in status_views:
            active_view = "all"
        try:
            current_page = max(1, int(request.query_params.get("page", "1")))
        except ValueError:
            current_page = 1
        page_size = 50
        view_status = status_views[active_view]
        shown_total = (
            result_counts[status_count_keys[view_status]]
            if view_status
            else result_counts["total"]
        )
        page_count = max(1, (shown_total + page_size - 1) // page_size)
        current_page = min(current_page, page_count)
        jobs = get_run_results(
            db_path,
            run_id,
            filter_status=view_status,
            limit=page_size,
            offset=(current_page - 1) * page_size,
        )
        for job in jobs:
            for source in job.get("sources", []):
                if source.get("id") == "x_manual":
                    normalized = normalize_public_job_url(source.get("source_url", ""))
                    source["display_host"] = normalized[1] if normalized else "Unknown host"
        sources = list_sources(db_path)
        usage = monthly_jev_usage(db_path, current_settings.monthly_jev_budget_usd)
        settings_row = get_settings(db_path)
        evidence_sources = list_preparation_sources(db_path)
        permitted_cvs = [
            source for source in evidence_sources
            if source["source_type"] == "resume" and source["permitted"]
        ]
        approved_claim_count = len(approved_claims(db_path))
        return render(
            request,
            "results.html",
            {
                "active_page": "results",
                "run": run,
                "jobs": jobs,
                "result_counts": result_counts,
                "filter_check_labels": FILTER_CHECK_LABELS,
                "active_view": active_view,
                "shown_total": shown_total,
                "current_page": current_page,
                "page_count": page_count,
                "page_size": page_size,
                "jev_pending": result_counts["unassessed"] + result_counts["pending_scores"],
                "status_url": f"/searches/{run_id}/status",
                "usage": usage,
                "jev_consented": bool(settings_row.get("jev_consent_at")),
                "sources": sources,
                "preparation_cvs": permitted_cvs,
                "preparation_claims_ready": approved_claim_count > 0,
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/searches/{run_id}/status")
    async def search_status(run_id: str):
        run = get_run(db_path, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Search not found.")
        return JSONResponse(
            {
                "status": run["status"],
                "stage": run["stage"],
                "message": run["message"],
                "checked_sources": run["checked_sources"],
                "found_count": run["found_count"],
                "matched_count": run["matched_count"],
                "scored_count": run["scored_count"],
            }
        )

    @app.post("/searches/{run_id}/score")
    async def score_search(
        request: Request,
        background_tasks: BackgroundTasks,
        run_id: str,
    ):
        if not operation_lock.acquire(blocking=False):
            return RedirectResponse(
                f"/searches/{run_id}?notice=Wait+for+the+current+local+search+operation+to+finish.",
                status_code=303,
            )
        try:
            run = get_run(db_path, run_id)
            if run is None:
                raise HTTPException(status_code=404, detail="Search not found.")
            settings_row = get_settings(db_path)
            if not current_settings.api_key:
                return RedirectResponse(
                    "/settings?notice=Add+your+TypeSafe+key+to+.env+and+restart+the+app.",
                    status_code=303,
                )
            if not settings_row.get("jev_consent_at"):
                return RedirectResponse(
                    "/settings?notice=Review+the+data+notice+and+enable+Jev+first.",
                    status_code=303,
                )
            if not get_run_results(db_path, run_id):
                return RedirectResponse(
                    f"/searches/{run_id}?notice=Run+the+search+before+scoring.",
                    status_code=303,
                )
            if not claim_scoring_run(db_path, run_id):
                return RedirectResponse(f"/searches/{run_id}", status_code=303)
            background_tasks.add_task(run_scoring_serialized, run_id)
            return RedirectResponse(f"/searches/{run_id}", status_code=303)
        finally:
            operation_lock.release()

    @app.post("/jobs/{job_id}/prepare")
    async def prepare_job(request: Request, job_id: str, background_tasks: BackgroundTasks):
        if not operation_lock.acquire(blocking=False):
            return RedirectResponse(
                "/preparations?notice=Wait+for+the+current+local+operation+to+finish+before+starting+preparation.",
                status_code=303,
            )
        operation_lock.release()
        form = dict(await request.form())
        run_id = str(form.get("run_id") or "")
        selected_cv_id = str(form.get("selected_cv_id") or "")
        try:
            record, created = request_preparation(db_path, job_id, run_id, selected_cv_id)
        except ValueError as exc:
            return RedirectResponse(
                f"/searches/{run_id}?{urlencode({'notice': str(exc)})}",
                status_code=303,
            )
        if created:
            background_tasks.add_task(run_preparation_serialized, record["id"])
        notice = "Preparation+started+for+this+listing." if created else "This+listing+already+has+a+request+for+the+same+saved+inputs."
        return RedirectResponse(f"/preparations/{record['id']}?notice={notice}", status_code=303)

    @app.post("/jobs/{job_id}/{action}")
    async def job_action(request: Request, job_id: str, action: str):
        if action not in {"save", "hide", "unsave", "unhide", "applied"}:
            raise HTTPException(status_code=404, detail="Action not found.")
        if action == "applied":
            if not mark_applied(db_path, job_id):
                raise HTTPException(status_code=404, detail="Listing not found.")
        elif action == "save":
            set_job_user_state(db_path, job_id, "saved")
        elif action == "hide":
            set_job_user_state(db_path, job_id, "hidden")
        else:
            clear_job_user_state(db_path, job_id)
        form = dict(await request.form())
        target = _safe_return_path(str(form.get("return_to") or "/"))
        return RedirectResponse(target, status_code=303)

    @app.get("/preparations", response_class=HTMLResponse)
    async def preparations_page(request: Request):
        cancel_followups_for_closed_jobs(db_path)
        followups = list_followups(db_path)
        return render(
            request,
            "preparations.html",
            {
                "active_page": "preparations",
                "preparations": list_preparations(db_path),
                "followups": followups,
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/preparations/{request_id}", response_class=HTMLResponse)
    async def preparation_detail(request: Request, request_id: str):
        cancel_followups_for_closed_jobs(db_path)
        record = get_preparation(db_path, request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Preparation request not found.")
        from clue_ai.database import connect

        with connect(db_path) as db:
            latest = db.execute(
                "SELECT id FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
                (request_id,),
            ).fetchone()
        packet = get_packet(db_path, latest["id"]) if latest else None
        with connect(db_path) as db:
            contacts = [
                dict(item)
                for item in db.execute(
                    "SELECT * FROM researched_contacts WHERE request_id = ? ORDER BY confidence, name",
                    (request_id,),
                ).fetchall()
            ]
            gmail_drafts = [
                dict(item)
                for item in db.execute(
                    """SELECT id, packet_id, recipient, subject, approved_sha256,
                              gmail_draft_id, state, error_summary, created_at, updated_at
                       FROM gmail_drafts WHERE request_id = ? ORDER BY created_at DESC""",
                    (request_id,),
                ).fetchall()
            ]
        outreach_options = []
        if packet:
            for index, message in enumerate(packet["output"].get("rewriter", {}).get("outreach_drafts", [])):
                match = next(
                    (
                        item for item in contacts
                        if item["source_url"] == message.get("contact_source_url")
                        and item["name"] == message.get("recipient_name")
                    ),
                    None,
                )
                outreach_options.append({"index": index, "message": message, "contact": match})
        gmail_connected = bool(get_settings(db_path).get("gmail_oauth_connected_at"))
        with connect(db_path) as db:
            applied_record = db.execute(
                "SELECT 1 FROM applications WHERE job_id = ? OR canonical_url = ? LIMIT 1",
                (record["job_id"], record["snapshot"].get("canonical_url", "")),
            ).fetchone()
        return render(
            request,
            "preparation_detail.html",
            {
                "active_page": "preparations",
                "preparation": record,
                "practice_sessions": list_practice_sessions(db_path, request_id),
                "packet": packet,
                "contacts": contacts,
                "gmail_drafts": gmail_drafts,
                "outreach_options": outreach_options,
                "followup": next(iter(list_followups(db_path, request_id=request_id)), None),
                "packet_feedback": get_packet_feedback(db_path, packet["id"]) if packet else None,
                "gmail_connected": gmail_connected,
                "applied_recorded": bool(applied_record),
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/outcomes", response_class=HTMLResponse)
    async def outcomes_page(request: Request):
        with connect(db_path) as db:
            events = [
                dict(item)
                for item in db.execute(
                    """SELECT event.*, app.title, app.company FROM application_events event
                       LEFT JOIN applications app ON app.job_id = event.job_id
                       ORDER BY event.occurred_at DESC, event.id"""
                ).fetchall()
            ]
            feedback_rows = [
                dict(item)
                for item in db.execute(
                    """SELECT feedback.*, app.title, app.company FROM interview_feedback feedback
                       LEFT JOIN applications app ON app.job_id = feedback.job_id
                       ORDER BY feedback.occurred_at DESC, feedback.id"""
                ).fetchall()
            ]
        for item in events:
            try:
                item["details"] = json.loads(item["details_json"])
            except (json.JSONDecodeError, TypeError):
                item["details"] = {}
        for item in feedback_rows:
            try:
                item["gap_tags"] = json.loads(item["gap_tags_json"])
            except (json.JSONDecodeError, TypeError):
                item["gap_tags"] = []
        return render(
            request,
            "outcomes.html",
            {
                "active_page": "outcomes",
                "summary": outcome_summary(db_path),
                "events": events,
                "feedback_rows": feedback_rows,
                "tracked_applications": len(applied_jobs(db_path)),
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.post("/preparations/{request_id}/follow-up")
    async def schedule_followup_route(request: Request, request_id: str):
        form = dict(await request.form())
        try:
            schedule_followup(
                db_path,
                request_id,
                kind=str(form.get("kind") or ""),
                due_on=str(form.get("due_on") or ""),
                note=str(form.get("note") or ""),
            )
        except ValueError as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}", status_code=303
            )
        return RedirectResponse(
            f"/preparations/{request_id}?notice=In-app+follow-up+reminder+saved.", status_code=303
        )

    @app.post("/preparations/{request_id}/follow-up/finish")
    async def finish_followup_route(request: Request, request_id: str):
        form = dict(await request.form())
        outcome = str(form.get("outcome") or "")
        if outcome == "completed":
            state, reason = "completed", "Owner completed the follow-up manually."
        elif outcome == "reply":
            state, reason = "cancelled", "Owner marked a relevant reply received."
        elif outcome == "closed":
            state, reason = "cancelled", "Owner marked the opportunity closed."
        else:
            return RedirectResponse(
                f"/preparations/{request_id}?notice=Choose+a+valid+reminder+action.", status_code=303
            )
        if not finish_followup(db_path, request_id, state=state, resolution=reason):
            return RedirectResponse(
                f"/preparations/{request_id}?notice=No+active+reminder+was+found.", status_code=303
            )
        label = "completed" if state == "completed" else "closed"
        return RedirectResponse(
            f"/preparations/{request_id}?notice=Follow-up+reminder+{label}.", status_code=303
        )


    @app.post("/preparations/{request_id}/retry")
    async def retry_preparation_route(request_id: str, background_tasks: BackgroundTasks):
        from clue_ai.application_prep import retry_preparation

        try:
            record, created = retry_preparation(db_path, request_id)
        except ValueError as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}",
                status_code=303,
            )
        if created:
            background_tasks.add_task(run_preparation_serialized, record["id"])
        return RedirectResponse(f"/preparations/{record['id']}", status_code=303)

    @app.post("/preparations/{request_id}/practice/start")
    async def start_interview_practice(request_id: str, background_tasks: BackgroundTasks):
        try:
            session = create_practice_session(db_path, request_id)
        except ValueError as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}", status_code=303
            )
        background_tasks.add_task(run_practice_questions_serialized, session["id"])
        return RedirectResponse(f"/preparations/{request_id}?notice=Interview+practice+started.", status_code=303)

    @app.post("/preparations/{request_id}/contacts/{contact_id}/suppress")
    async def suppress_contact_route(request_id: str, contact_id: str):
        if not suppress_researched_contact(db_path, request_id, contact_id):
            return RedirectResponse(
                f"/preparations/{request_id}?notice=That+contact+cannot+be+changed+in+this+packet+state.",
                status_code=303,
            )
        return RedirectResponse(
            f"/preparations/{request_id}?notice=Contact+excluded.+The+packet+was+invalidated;+retry+manually+to+prepare+without+them.+Remove+any+prior+unsent+Gmail+draft+yourself.",
            status_code=303,
        )

    @app.post("/preparations/{request_id}/practice/{session_id}/answers")
    async def submit_practice_answers(request: Request, request_id: str, session_id: str, background_tasks: BackgroundTasks):
        form = await request.form()
        questions = form.getlist("question")
        answers = form.getlist("answer")
        if len(questions) != len(answers):
            return RedirectResponse(
                f"/preparations/{request_id}?notice=Answer+all+practice+questions+before+assessment.",
                status_code=303,
            )
        try:
            queue_practice_answers(
                db_path,
                session_id,
                json.dumps(
                    [{"question": str(question), "answer": str(answer)} for question, answer in zip(questions, answers, strict=True)],
                    ensure_ascii=False,
                ),
            )
        except ValueError as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}", status_code=303
            )
        background_tasks.add_task(run_practice_assessment_serialized, session_id)
        return RedirectResponse(f"/preparations/{request_id}?notice=Your+answers+were+submitted+for+practice+feedback.", status_code=303)

    @app.post("/preparations/{request_id}/packets/{packet_id}/approve")
    async def approve_packet_route(request: Request, request_id: str, packet_id: str):
        form = dict(await request.form())
        if not _checked(form.get("confirm_review")):
            return RedirectResponse(
                f"/preparations/{request_id}?notice=Confirm+that+you+reviewed+this+exact+packet+version+first.",
                status_code=303,
            )
        packet = get_packet(db_path, packet_id)
        if packet is None or packet["request_id"] != request_id:
            raise HTTPException(status_code=404, detail="Packet not found.")
        try:
            approve_packet(db_path, current_settings, packet_id)
        except ValueError as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}",
                status_code=303,
            )
        return RedirectResponse(
            f"/preparations/{request_id}?notice=Packet+approved.+You+must+still+apply+or+send+manually.",
            status_code=303,
        )

    @app.post("/preparations/{request_id}/packets/{packet_id}/feedback")
    async def packet_feedback_route(request: Request, request_id: str, packet_id: str):
        form = dict(await request.form())
        packet = get_packet(db_path, packet_id)
        if packet is None or packet["request_id"] != request_id:
            raise HTTPException(status_code=404, detail="Packet not found.")
        try:
            verify_packet_approval(
                db_path, current_settings, packet_id, require_current_inputs=False
            )
            record_packet_feedback(
                db_path,
                packet_id=packet_id,
                owner_minutes=int(str(form.get("owner_minutes") or "")),
                quality_rating=int(str(form.get("quality_rating") or "")),
                factual_corrections=int(str(form.get("factual_corrections") or "0")),
                owner_note=str(form.get("owner_note") or ""),
            )
        except (ValueError, TypeError) as exc:
            message = str(exc) or "Enter valid packet-review values."
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': message})}",
                status_code=303,
            )
        return RedirectResponse(
            f"/preparations/{request_id}?notice=Packet+review+feedback+saved+locally.",
            status_code=303,
        )

    @app.get("/packets/{packet_id}/artifacts/{artifact_id}")
    async def packet_artifact_download(packet_id: str, artifact_id: str):
        packet = get_packet(db_path, packet_id)
        if packet is None:
            raise HTTPException(status_code=404, detail="Packet not found.")
        artifact = next((item for item in packet["artifacts"] if item["id"] == artifact_id), None)
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found.")
        path = Path(artifact["file_path"]).resolve()
        packet_root = (current_settings.data_dir / "application-packets").resolve()
        if not path.is_relative_to(packet_root) or not path.is_file():
            raise HTTPException(status_code=404, detail="Artifact is unavailable.")
        if sha256(path.read_bytes()).hexdigest() != artifact["content_sha256"]:
            raise HTTPException(status_code=409, detail="Artifact changed after generation.")
        return FileResponse(path, filename=artifact["filename"])

    @app.post("/preparations/{request_id}/packets/{packet_id}/gmail-draft")
    async def create_gmail_draft_route(request: Request, request_id: str, packet_id: str):
        form = dict(await request.form())
        if not _checked(form.get("confirm_exact")):
            return RedirectResponse(
                f"/preparations/{request_id}?notice=Review+and+confirm+the+exact+To,+Subject,+and+body+first.",
                status_code=303,
            )
        settings_row = get_settings(db_path)
        if not settings_row.get("gmail_consent_at") or not settings_row.get("gmail_oauth_connected_at"):
            return RedirectResponse(
                "/settings?notice=Connect+and+authorize+Gmail+Drafts+first.", status_code=303
            )
        try:
            draft_index = int(form.get("draft_index") or -1)
            _, gmail_id = create_approved_packet_draft(
                db_path,
                current_settings,
                request_id,
                packet_id,
                draft_index,
                confirmed=True,
            )
        except (ValueError, GmailDraftError) as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}",
                status_code=303,
            )
        return RedirectResponse(
            f"/preparations/{request_id}?notice=Unsent+Gmail+draft+created+({gmail_id}).+The+owner+must+send+it+manually.",
            status_code=303,
        )

    @app.post("/preparations/{request_id}/gmail-drafts/{draft_record_id}/reconcile")
    async def reconcile_gmail_draft_route(request: Request, request_id: str, draft_record_id: str):
        form = dict(await request.form())
        outcome = str(form.get("outcome") or "")
        gmail_id = _form_text(form, "gmail_draft_id", 200)
        with connect(db_path) as db:
            row = db.execute(
                "SELECT state FROM gmail_drafts WHERE id = ? AND request_id = ?",
                (draft_record_id, request_id),
            ).fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Gmail draft record not found.")
            if row["state"] != "unknown":
                raise HTTPException(status_code=409, detail="Only an unresolved Gmail draft can be reconciled.")
            if outcome == "found" and gmail_id:
                db.execute(
                    """UPDATE gmail_drafts SET state = 'created', gmail_draft_id = ?,
                       error_summary = '', updated_at = ? WHERE id = ?""",
                    (gmail_id, utc_now(), draft_record_id),
                )
            elif outcome == "not_found" and _checked(form.get("checked_gmail")):
                db.execute(
                    """UPDATE gmail_drafts SET state = 'failed', error_summary = ?,
                       updated_at = ? WHERE id = ?""",
                    ("Owner confirmed the draft is absent from Gmail Drafts; manual retry is allowed.", utc_now(), draft_record_id),
                )
            else:
                return RedirectResponse(
                    f"/preparations/{request_id}?notice=Choose+the+reconciled+result+after+checking+Gmail+Drafts.",
                    status_code=303,
                )
        return RedirectResponse(f"/preparations/{request_id}?notice=Gmail+draft+status+reconciled.", status_code=303)

    @app.post("/preparations/{request_id}/record-stage")
    async def record_application_stage_route(request: Request, request_id: str):
        form = dict(await request.form())
        record = get_preparation(db_path, request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Preparation request not found.")
        with connect(db_path) as db:
            packet_row = db.execute(
                "SELECT id, status FROM preparation_packets WHERE request_id = ? ORDER BY revision DESC LIMIT 1",
                (request_id,),
            ).fetchone()
        if not packet_row or packet_row["status"] != "approved":
            return RedirectResponse(
                f"/preparations/{request_id}?notice=Approve+the+final+packet+before+recording+an+application+outcome.",
                status_code=303,
            )
        stage = str(form.get("stage") or "")
        try:
            if stage == "submitted":
                if not _checked(form.get("owner_attestation")):
                    raise ValueError("Confirm that you submitted the application outside Clue.")
                application_id = mark_snapshot_applied(db_path, record["snapshot"])
            else:
                application_id = find_applied_snapshot(db_path, record["snapshot"])
                if application_id is None:
                    raise ValueError("Record your manual submission first, then add later stage updates.")
            record_stage(
                db_path,
                job_id=application_id,
                request_id=request_id,
                stage=stage,
                details=str(form.get("details") or ""),
            )
            if stage in {"screen", "technical", "final", "offer", "rejected", "withdrawn", "no_response"}:
                cancel_followup_for_request(
                    db_path, request_id, f"Relevant application update recorded: {stage}."
                )
        except ValueError as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}",
                status_code=303,
            )
        return RedirectResponse("/outcomes?notice=Owner-reported+stage+saved.", status_code=303)

    @app.post("/preparations/{request_id}/interview-feedback")
    async def record_interview_feedback_route(request: Request, request_id: str):
        form = dict(await request.form())
        record = get_preparation(db_path, request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Preparation request not found.")
        application_id = find_applied_snapshot(db_path, record["snapshot"])
        if application_id is None:
            return RedirectResponse(
                f"/preparations/{request_id}?notice=Record+the+manual+submission+before+adding+interview+feedback.",
                status_code=303,
            )
        try:
            tags = [part.strip() for part in str(form.get("gap_tags") or "").split(",") if part.strip()]
            record_interview_feedback(
                db_path,
                job_id=application_id,
                request_id=request_id,
                stage=str(form.get("stage") or ""),
                self_assessment=str(form.get("self_assessment") or ""),
                employer_feedback=str(form.get("employer_feedback") or ""),
                gap_tags=tags,
            )
            cancel_followup_for_request(
                db_path, request_id, "Interview feedback was recorded for this opportunity."
            )
        except ValueError as exc:
            return RedirectResponse(
                f"/preparations/{request_id}?{urlencode({'notice': str(exc)})}",
                status_code=303,
            )
        return RedirectResponse("/outcomes?notice=Interview+feedback+saved.", status_code=303)

    @app.post("/preparations/{request_id}/receipt")
    async def upload_application_receipt(
        request_id: str,
        receipt_file: UploadFile | None = File(default=None),  # noqa: B008 - FastAPI parameter metadata.
    ):
        record = get_preparation(db_path, request_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Preparation request not found.")
        with connect(db_path) as db:
            owner_submission = db.execute(
                """SELECT job_id FROM application_events WHERE request_id = ? AND stage = 'submitted'
                   AND event_type = 'owner_submission_attestation' LIMIT 1""",
                (request_id,),
            ).fetchone()
        if not owner_submission:
            return RedirectResponse(
                f"/preparations/{request_id}?notice=Record+your+manual+submission+before+adding+a+receipt.",
                status_code=303,
            )
        if receipt_file is None or not receipt_file.filename:
            return RedirectResponse(f"/preparations/{request_id}?notice=Choose+a+receipt+file+first.", status_code=303)
        suffix = Path(receipt_file.filename).suffix.casefold()
        if suffix not in {".pdf", ".png", ".jpg", ".jpeg", ".eml", ".txt"}:
            return RedirectResponse(f"/preparations/{request_id}?notice=Use+a+PDF,+image,+EML,+or+TXT+receipt.", status_code=303)
        content = await receipt_file.read(10 * 1024 * 1024 + 1)
        if len(content) > 10 * 1024 * 1024:
            return RedirectResponse(f"/preparations/{request_id}?notice=Receipt+files+must+be+10+MB+or+smaller.", status_code=303)
        relative = Path("application-packets") / request_id / "receipts" / f"{uuid.uuid4().hex}{suffix}"
        destination = (current_settings.data_dir / relative).resolve()
        if not destination.is_relative_to(current_settings.data_dir.resolve()):
            raise HTTPException(status_code=400, detail="Receipt path is outside local storage.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        details = {
            "receipt_filename": Path(receipt_file.filename).name[:200],
            "receipt_path": str(destination),
            "receipt_sha256": sha256(content).hexdigest(),
        }
        record_stage(
            db_path,
            job_id=find_applied_snapshot(db_path, record["snapshot"]) or owner_submission["job_id"],
            request_id=request_id,
            stage="submitted",
            details_data=details,
            evidence_level="receipt_imported",
            event_type="receipt_imported",
        )
        return RedirectResponse(f"/preparations/{request_id}?notice=Receipt+stored+locally.", status_code=303)

    @app.get("/outcomes/receipts/{event_id}")
    async def download_application_receipt(event_id: str):
        with connect(db_path) as db:
            row = db.execute(
                "SELECT details_json FROM application_events WHERE id = ? AND event_type = 'receipt_imported'",
                (event_id,),
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Receipt not found.")
        try:
            details = json.loads(row["details_json"])
            path = Path(details["receipt_path"]).resolve()
        except (KeyError, json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=404, detail="Receipt is unavailable.") from None
        root = (current_settings.data_dir / "application-packets").resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(status_code=404, detail="Receipt is unavailable.")
        if sha256(path.read_bytes()).hexdigest() != details.get("receipt_sha256"):
            raise HTTPException(status_code=409, detail="Receipt changed after it was recorded.")
        return FileResponse(path, filename=details.get("receipt_filename", path.name))

    @app.get("/applied", response_class=HTMLResponse)
    async def applied_page(request: Request):
        return render(request, "applied.html", {
            "active_page": "applied", "jobs": applied_jobs(db_path),
            "notice": request.query_params.get("notice", ""),
        })

    @app.post("/applications/{application_id}/undo")
    async def undo_application(request: Request, application_id: str):
        if not undo_applied(db_path, application_id):
            raise HTTPException(status_code=404, detail="Application record not found.")
        return RedirectResponse("/applied?notice=Applied+status+removed.+The+job+is+eligible+for+search+again.", status_code=303)

    @app.get("/saved", response_class=HTMLResponse)
    async def saved_page(request: Request):
        return render(
            request,
            "saved.html",
            {
                "active_page": "saved",
                "jobs": saved_jobs(db_path),
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/hidden", response_class=HTMLResponse)
    async def hidden_page(request: Request):
        return render(
            request,
            "hidden.html",
            {
                "active_page": "hidden",
                "jobs": hidden_jobs(db_path),
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/sources", response_class=HTMLResponse)
    async def sources_page(request: Request):
        sources = list_sources(db_path)
        return render(
            request,
            "sources.html",
            {
                "active_page": "sources",
                "sources": sources,
                "connector_types": SOURCE_KINDS,
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.get("/companies", response_class=HTMLResponse)
    async def companies_page(request: Request):
        profile = get_profile(db_path)
        query = str(request.query_params.get("q") or "")[:100]
        group_id = str(request.query_params.get("group") or "")
        if group_id not in GROUP_LABELS:
            group_id = ""
        all_companies = list_companies(db_path)
        companies = filter_and_rank_companies(
            all_companies, query=query, group_id=group_id, profile=profile
        )
        tracked_count = sum(bool(company["tracked"]) for company in all_companies)
        return render(
            request,
            "companies.html",
            {
                "active_page": "companies",
                "companies": companies,
                "groups": GROUP_LABELS,
                "selected_group": group_id,
                "query": query,
                "return_to": "/companies?" + urlencode({"q": query, "group": group_id}),
                "tracked_count": tracked_count,
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.post("/companies/{company_id}/track")
    async def track_company(company_id: str, request: Request):
        if not set_company_tracked(db_path, company_id, True):
            raise HTTPException(status_code=404, detail="Company not found.")
        form = dict(await request.form())
        return RedirectResponse(
            _safe_return_path(str(form.get("return_to") or "/companies")), status_code=303
        )

    @app.post("/companies/{company_id}/untrack")
    async def untrack_company(company_id: str, request: Request):
        if not set_company_tracked(db_path, company_id, False):
            raise HTTPException(status_code=404, detail="Company not found.")
        form = dict(await request.form())
        return RedirectResponse(
            _safe_return_path(str(form.get("return_to") or "/companies")), status_code=303
        )

    @app.post("/companies/{company_id}/retry")
    async def retry_company_source(company_id: str, request: Request):
        if not retry_company_board(db_path, company_id):
            raise HTTPException(
                status_code=409, detail="This company is not a tracked blocked source."
            )
        form = dict(await request.form())
        return RedirectResponse(
            _safe_return_path(str(form.get("return_to") or "/companies")), status_code=303
        )

    @app.post("/sources/add")
    async def add_source_route(request: Request):
        form = dict(await request.form())
        kind = str(form.get("kind") or "")
        if kind not in SOURCE_KINDS:
            return RedirectResponse(
                "/sources?notice=Choose+a+supported+public+source+type.", status_code=303
            )
        company = _form_text(form, "company", 120).strip()
        if not company:
            return RedirectResponse(
                "/sources?notice=Enter+the+company+or+source+name.", status_code=303
            )
        attribution = _form_text(form, "attribution", 120) or company
        config: dict[str, str] = {"company": company}
        if kind == "greenhouse":
            token = _form_text(form, "identifier", 100).strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
                return RedirectResponse(
                    "/sources?notice=Enter+a+valid+Greenhouse+board+token.", status_code=303
                )
            config["board_token"] = token
            endpoint = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
        elif kind == "lever":
            token = _form_text(form, "identifier", 100).strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
                return RedirectResponse(
                    "/sources?notice=Enter+a+valid+Lever+site+identifier.", status_code=303
                )
            region = _form_text(form, "lever_region", 16).strip().casefold() or "eu"
            if region not in {"global", "eu"}:
                return RedirectResponse(
                    "/sources?notice=Choose+a+valid+Lever+site+region.", status_code=303
                )
            host = "api.eu.lever.co" if region == "eu" else "api.lever.co"
            config["site"] = token
            config["region"] = region
            endpoint = f"https://{host}/v0/postings/{token}?mode=json"
        elif kind == "smartrecruiters":
            token = _form_text(form, "identifier", 100).strip()
            if not re.fullmatch(r"[A-Za-z0-9_-]+", token):
                return RedirectResponse(
                    "/sources?notice=Enter+a+valid+SmartRecruiters+company+identifier.",
                    status_code=303,
                )
            config["company_id"] = token
            endpoint = (
                f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100&offset=0"
            )
        else:
            career_url = _form_text(form, "career_url", 2_000).strip()
            valid, message = validate_career_url(career_url)
            if not valid:
                return RedirectResponse(
                    f"/sources?notice={_url_message(message)}",
                    status_code=303,
                )
            endpoint = career_url
            config["career_url"] = career_url
        source_id = add_source(
            db_path,
            name=company,
            kind=kind,
            endpoint=endpoint,
            config=config,
            attribution=attribution,
        )
        return RedirectResponse(
            f"/sources?notice=Added+{source_id}+and+enabled+for+the+next+search.",
            status_code=303,
        )

    @app.post("/sources/{source_id}/approve")
    async def approve_source(source_id: str):
        source = get_source(db_path, source_id)
        if source is None or source.get("is_builtin"):
            raise HTTPException(status_code=404, detail="Reviewable source not found.")
        set_source_enabled(db_path, source_id, True)
        return RedirectResponse(
            f"/sources?notice={source_id}+enabled.+A+future+search+will+check+it.",
            status_code=303,
        )

    @app.post("/sources/{source_id}/pause")
    async def pause_source(source_id: str):
        mark_source_for_review(db_path, source_id)
        return RedirectResponse(
            "/sources?notice=Source+paused+and+returned+to+Review.", status_code=303
        )

    @app.post("/sources/{source_id}/enable")
    async def enable_builtin_source(source_id: str):
        source = get_source(db_path, source_id)
        if (
            source is None
            or not source.get("is_builtin")
            or source.get("state") != "approved"
            or source.get("kind") == "manual_x"
        ):
            raise HTTPException(status_code=404, detail="This source cannot be directly enabled.")
        set_source_enabled(db_path, source_id, True)
        return RedirectResponse("/sources?notice=Source+enabled.", status_code=303)

    @app.post("/sources/{source_id}/remove")
    async def remove_source_route(source_id: str):
        source = get_source(db_path, source_id)
        if source is None or source.get("is_builtin"):
            raise HTTPException(status_code=404, detail="Removable source not found.")
        remove_user_source(db_path, source_id)
        return RedirectResponse("/sources?notice=Owner-added+source+removed.", status_code=303)

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request):
        settings_row = get_settings(db_path)
        usage = monthly_jev_usage(db_path, current_settings.monthly_jev_budget_usd)
        openai_usage = monthly_openai_usage(db_path)
        return render(
            request,
            "settings.html",
            {
                "active_page": "settings",
                "jev_consented": bool(settings_row.get("jev_consent_at")),
                "usage": usage,
                "openai_settings": settings_row,
                "openai_usage": openai_usage,
                "openai_key_configured": bool(current_settings.openai_api_key),
                "openai_enabled": bool(settings_row.get("openai_consent_at")),
                "gmail_client_configured": bool(current_settings.gmail_oauth_client_id),
                "gmail_connected": bool(settings_row.get("gmail_oauth_connected_at")),
                "notice": request.query_params.get("notice", ""),
            },
        )

    @app.post("/settings/jev-consent")
    async def set_jev_consent_route(request: Request):
        form = dict(await request.form())
        accepted = _checked(form.get("agree"))
        set_jev_consent(db_path, accepted)
        message = "Jev+is+enabled." if accepted else "Jev+is+disabled."
        return RedirectResponse(f"/settings?notice={message}", status_code=303)

    @app.post("/settings/openai-controls")
    async def save_openai_controls_route(request: Request):
        form = dict(await request.form())
        try:
            values = {
                "consent": _checked(form.get("openai_consent")),
                "monthly_cap_usd": float(form.get("monthly_cap_usd") or 0),
                "opportunity_cap_usd": float(form.get("opportunity_cap_usd") or 0),
                "input_usd_per_million": float(form.get("input_usd_per_million") or 0),
                "output_usd_per_million": float(form.get("output_usd_per_million") or 0),
                "rate_card_revision": _form_text(form, "rate_card_revision", 80),
                "search_usd_per_thousand": 0.0,
            }
            save_openai_controls(db_path, **values)
        except (ValueError, TypeError) as exc:
            return RedirectResponse(
                f"/settings?{urlencode({'notice': str(exc) or 'Enter valid non-negative budget and rate values.'})}",
                status_code=303,
            )
        state = "enabled" if values["consent"] else "disabled"
        return RedirectResponse(f"/settings?notice=OpenAI+data-sharing+consent+{state}.", status_code=303)

    @app.post("/settings/gmail/connect")
    async def connect_gmail_route():
        try:
            authorization_url = start_local_oauth(db_path, current_settings)
        except GmailDraftError as exc:
            return RedirectResponse(
                f"/settings?{urlencode({'notice': str(exc)})}", status_code=303
            )
        return RedirectResponse(authorization_url, status_code=303)

    @app.post("/settings/gmail/disconnect")
    async def disconnect_gmail_route():
        WindowsDPAPITokenStore(current_settings.data_dir).delete()
        set_gmail_connection(db_path, False)
        return RedirectResponse(
            "/settings?notice=Local+Gmail+authorization+removed.+Revoke+the+Google+grant+in+your+Google+Account+if+you+also+want+to+withdraw+it.",
            status_code=303,
        )

    @app.post("/data/delete")
    async def delete_all_data(request: Request):
        form = dict(await request.form())
        if str(form.get("confirmation") or "").strip() != "DELETE":
            return RedirectResponse(
                "/settings?notice=Type+DELETE+to+confirm+local+data+removal.", status_code=303
            )
        if not operation_lock.acquire(blocking=False):
            return RedirectResponse(
                "/settings?notice=Wait+for+the+current+search+or+Jev+scoring+run+to+finish+before+deleting+local+data.",
                status_code=303,
            )
        try:
            if has_active_runs(db_path):
                return RedirectResponse(
                    "/settings?notice=Wait+for+the+current+search+or+Jev+scoring+run+to+finish+before+deleting+local+data.",
                    status_code=303,
                )
            profile = get_profile(db_path)
            cv_path = Path(profile.cv_path) if profile.cv_path else None
            delete_personal_data(db_path, cv_path, current_settings.data_dir)
            return RedirectResponse(
                "/?notice=Local+profile,+CV,+search+history,+and+job+data+were+removed.",
                status_code=303,
            )
        finally:
            operation_lock.release()

    @app.get("/privacy", response_class=HTMLResponse)
    async def privacy_page(request: Request):
        return render(request, "privacy.html", {"active_page": ""})

    @app.get("/health")
    async def health():
        return JSONResponse({"status": "ok", "storage": "local"})

    return app


def _form_text(form: dict, field: str, limit: int) -> str:
    value = str(form.get(field) or "")
    value = value.replace("\x00", "").strip()
    return value[:limit]


def _choice(value: object, choices: set[str]) -> str:
    selected = str(value or "unknown").casefold()
    return selected if selected in choices else "unknown"


def _checked(value: object) -> bool:
    return str(value or "").casefold() in {"1", "true", "yes", "on"}


def _safe_filename(value: str, suffix: str) -> str:
    name = Path(value).name
    name = re.sub(r"[\x00-\x1f<>:\"/\\|?*]+", "_", name).strip(" .")
    if not name:
        name = "cv"
    return (Path(name).stem[:100] or "cv") + suffix.lower()


def _read_pending_text(cv_dir: Path, pending_id: str) -> str:
    if not PENDING_PATTERN.fullmatch(pending_id):
        return ""
    path = cv_dir / f"pending-{pending_id}.txt"
    try:
        return path.read_text(encoding="utf-8")[:120_000]
    except OSError:
        return ""


def _read_pending_name(cv_dir: Path, pending_id: str) -> str:
    if not PENDING_PATTERN.fullmatch(pending_id):
        return ""
    path = cv_dir / f"pending-{pending_id}.name"
    try:
        return path.read_text(encoding="utf-8")[:120]
    except OSError:
        return ""


def _cleanup_pending_uploads(cv_dir: Path) -> None:
    cutoff = time.time() - 24 * 60 * 60
    for path in cv_dir.glob("pending-*"):
        try:
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            continue


def _safe_return_path(value: str) -> str:
    if not value.startswith("/") or value.startswith("//") or "\\" in value:
        return "/"
    parts = urlsplit(value)
    if parts.scheme or parts.netloc:
        return "/"
    return value[:2_000]


def _url_message(value: str) -> str:
    from urllib.parse import quote

    return quote(value[:220], safe="")


app = create_app()
