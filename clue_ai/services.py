from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from clue_ai.company_sources import crawl_tracked_companies
from clue_ai.config import Settings
from clue_ai.database import get_profile
from clue_ai.domain import utc_now
from clue_ai.filters import criteria_from_form, filter_jobs
from clue_ai.jev import score_run
from clue_ai.repository import (
    all_active_jobs,
    get_run,
    get_run_results,
    prune_expired_data,
    record_source_state,
    save_jobs_with_report,
    save_run_results,
    sources_due,
    update_run,
)
from clue_ai.sources import FetchOutcome, SourceFetchError, fetch_source


def run_search(
    database_path: Path,
    settings: Settings,
    run_id: str,
    *,
    auto_jev: bool = True,
) -> None:
    run = get_run(database_path, run_id)
    if run is None:
        return
    profile = get_profile(database_path)
    criteria = criteria_from_form(run.get("criteria") or {})
    if not criteria.roles.strip() and profile.target_roles.strip():
        criteria = replace(criteria, roles=profile.target_roles)

    update_run(
        database_path,
        run_id,
        status="running",
        stage="sources",
        message="Checking approved sources that are due for refresh.",
    )
    due_sources = sources_due(database_path)
    checked_notes: list[str] = []
    found_count = 0
    for index, source in enumerate(due_sources, start=1):
        update_run(
            database_path,
            run_id,
            stage="sources",
            message=f"Checking {source['name']} ({index} of {len(due_sources)}).",
            checked_sources=checked_notes,
        )
        try:
            outcome: FetchOutcome = fetch_source(source, criteria, settings, database_path)
            if outcome.skipped:
                checked_notes.append(f"{source['name']}: skipped — {outcome.message}")
                continue
            if outcome.blocked:
                if outcome.jobs:
                    saved_partial = save_jobs_with_report(database_path, outcome.jobs)
                    found_count += len(outcome.jobs)
                else:
                    saved_partial = None
                partial_note = (
                    f", {saved_partial.saved} listing record(s) saved from completed pages"
                    if saved_partial
                    else ""
                )
                record_source_state(database_path, source["id"], "blocked", outcome.message)
                statuses = _status_summary(outcome)
                checked_notes.append(
                    f"{source['name']}: paused after a block response; "
                    f"{outcome.checked} request(s), {outcome.response_bytes} response bytes"
                    f"{partial_note}"
                    f"{statuses}."
                )
                continue
            save_report = save_jobs_with_report(database_path, outcome.jobs)
            found_count += len(outcome.jobs)
            record_source_state(
                database_path,
                source["id"],
                "partial" if outcome.parse_failures or outcome.not_found_count else "ok",
                checked_at=utc_now(),
            )
            detail = (
                f"{len(outcome.jobs)} parsed from {outcome.raw_records} record(s); "
                f"{save_report.deduplicated} deduplicated; "
                f"{outcome.parse_failures} parse failure(s); "
                f"{outcome.response_bytes} response bytes across {outcome.checked} request(s)"
                f"{_status_summary(outcome)}."
            )
            if outcome.not_found_count:
                detail += (
                    f" {outcome.not_found_count} page(s) returned 404; cached listings remain "
                    "stale until their normal expiry or retention rule applies."
                )
            message_prefix = f"{outcome.message} " if outcome.message else ""
            checked_notes.append(
                f"{source['name']}: checked; {save_report.saved} listing record(s) indexed. "
                f"{message_prefix}{detail}"
            )
        except SourceFetchError as exc:
            state = "blocked" if exc.blocked else "error"
            record_source_state(database_path, source["id"], state, str(exc))
            if exc.blocked:
                checked_notes.append(f"{source['name']}: paused after a block response.")
            else:
                checked_notes.append(
                    f"{source['name']}: unavailable ({type(exc).__name__}); existing listings kept."
                )
        except Exception as exc:  # noqa: BLE001 - connector and parser implementations raise varied errors.
            record_source_state(
                database_path,
                source["id"],
                "error",
                f"Connector error: {type(exc).__name__}.",
            )
            checked_notes.append(
                f"{source['name']}: connector error ({type(exc).__name__}); existing listings kept."
            )

    company_raw_records = 0

    def save_company_jobs(jobs) -> int:
        nonlocal company_raw_records
        company_raw_records += len(jobs)
        return save_jobs_with_report(database_path, jobs).saved

    def company_progress(message: str) -> None:
        update_run(
            database_path,
            run_id,
            stage="sources",
            message=message,
            checked_sources=checked_notes,
            found_count=found_count + company_raw_records,
        )

    try:
        company_report = crawl_tracked_companies(
            database_path,
            settings,
            on_progress=company_progress,
            save_jobs=save_company_jobs,
        )
        found_count += company_report.raw_records
        if company_report.companies_checked:
            coverage_note = (
                f"Company career search: {company_report.companies_checked} tracked companies, "
                f"{company_report.boards_resolved} public ATS boards resolved, "
                f"{company_report.pages_checked} pages/feed requests, "
                f"{company_report.raw_records} listings parsed, "
                f"{company_report.jobs_indexed} new records indexed, "
                f"{company_report.blocked} blocked, {company_report.unavailable} unavailable, "
                f"{company_report.errors} errors; "
                f"{company_report.response_bytes} response bytes in "
                f"{company_report.elapsed_seconds:.1f}s."
            )
            checked_notes.append(coverage_note)
    except Exception as exc:  # noqa: BLE001 - existing aggregator results remain usable on crawler failure.
        found_count += company_raw_records
        checked_notes.append(
            f"Company career search could not finish ({type(exc).__name__}); existing listings kept."
        )

    update_run(
        database_path,
        run_id,
        stage="filtering",
        message="Filtering the local listing index against your search rules.",
        checked_sources=checked_notes,
        found_count=found_count,
    )

    prune_expired_data(database_path)
    indexed = all_active_jobs(database_path)
    indexed = [job for job in indexed if not job.get("hidden")]
    matched = filter_jobs(indexed, criteria)
    save_run_results(
        database_path,
        run_id,
        matched,
        score_state="unscored",
        score_reason="Waiting for the automatic Jev fit check.",
    )
    if not checked_notes:
        checked_notes.append(
            "No source needed a refresh; results use the current local index."
            if due_sources == []
            else "No source returned a listing."
        )
    message = f"Search ready: {len(matched)} listings match your hard filters."
    if auto_jev:
        update_run(
            database_path,
            run_id,
            status="scoring",
            stage="jev",
            message="Search complete. Checking Jev settings and fit evidence.",
            checked_sources=checked_notes,
            found_count=found_count,
            matched_count=len(matched),
        )
        run_jev_scoring(database_path, settings, run_id)
        return
    update_run(
        database_path,
        run_id,
        status="complete",
        stage="done",
        message=message,
        checked_sources=checked_notes,
        found_count=found_count,
        matched_count=len(matched),
        completed=True,
    )


def _status_summary(outcome: FetchOutcome) -> str:
    if not outcome.status_counts:
        return ""
    codes = ", ".join(
        f"HTTP {key.removeprefix('status_')} ×{count}"
        for key, count in sorted(outcome.status_counts.items())
        if count
    )
    return f"; {codes}" if codes else ""


def run_search_worker(
    database_path: Path,
    settings: Settings,
    run_id: str,
    *,
    auto_jev: bool = True,
) -> None:
    try:
        run_search(database_path, settings, run_id, auto_jev=auto_jev)
    except Exception as exc:  # noqa: BLE001 - persist a failed state for any worker failure.
        update_run(
            database_path,
            run_id,
            status="failed",
            stage="error",
            message="The local search could not finish. Existing listings are still available.",
            error=f"Local search error: {type(exc).__name__}.",
            completed=True,
        )


def run_jev_scoring(database_path: Path, settings: Settings, run_id: str) -> None:
    run = get_run(database_path, run_id)
    if run is None:
        return
    profile = get_profile(database_path)
    criteria = criteria_from_form(run.get("criteria") or {})
    jobs = [job for job in get_run_results(database_path, run_id) if not job.get("hidden")]
    if not jobs:
        matched_count = int(run.get("matched_count") or 0)
        message = (
            f"Search ready: {matched_count} listings match your hard filters. "
            "There are no listings to score with Jev."
        )
        update_run(
            database_path,
            run_id,
            status="complete",
            stage="done",
            message=message,
            scored_count=0,
            completed=True,
        )
        return
    try:
        result = score_run(
            database_path,
            settings,
            run_id,
            jobs,
            profile,
            criteria,
        )
        update_run(
            database_path,
            run_id,
            status="complete",
            stage="done",
            message=result.message,
            scored_count=result.scored_count,
            completed=True,
        )
    except Exception as exc:  # noqa: BLE001 - keep listings usable if Jev processing fails locally.
        update_run(
            database_path,
            run_id,
            status="complete",
            stage="done",
            message=f"Jev scoring failed locally ({type(exc).__name__}); listings remain available.",
            completed=True,
        )
