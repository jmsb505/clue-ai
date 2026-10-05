from __future__ import annotations

from collections import Counter
from dataclasses import replace
from pathlib import Path

from clue_ai.company_sources import crawl_tracked_companies
from clue_ai.config import Settings
from clue_ai.database import get_profile
from clue_ai.domain import utc_now
from clue_ai.filters import annotate_jobs, apply_candidate_search_scope, criteria_from_form
from clue_ai.jev import score_run
from clue_ai.job_focus import focus_note, focused_jobs
from clue_ai.repository import (
    all_active_jobs,
    get_run,
    get_run_result_counts,
    get_run_results,
    mark_researched_run_results,
    partition_researched_jobs,
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
    ingestion_excluded: Counter[str] = Counter()

    def save_focused_jobs(jobs):
        eligible, excluded = focused_jobs(jobs)
        ingestion_excluded.update(excluded)
        return save_jobs_with_report(database_path, eligible)

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
                    saved_partial = save_focused_jobs(outcome.jobs)
                    found_count += len(outcome.jobs)
                else:
                    saved_partial = None
                partial_note = (
                    f", {saved_partial.inserted} new and {saved_partial.deduplicated} existing "
                    "listing identities from completed pages"
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
            eligible, excluded = focused_jobs(outcome.jobs)
            save_report = save_focused_jobs(outcome.jobs)
            found_count += len(outcome.jobs)
            record_source_state(
                database_path,
                source["id"],
                "partial" if outcome.parse_failures or outcome.not_found_count else "ok",
                checked_at=utc_now(),
            )
            detail = (
                f"{len(outcome.jobs)} parsed from {outcome.raw_records} record(s); "
                f"{len(eligible)} AI-focused candidates; {sum(excluded.values())} locally excluded "
                f"({focus_note(excluded)}); "
                f"{save_report.inserted} new identities, "
                f"{save_report.deduplicated} existing identities reused; "
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
                f"{source['name']}: checked; {save_report.inserted} new listing identities, "
                f"{save_report.deduplicated} existing identities updated. "
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
        return save_focused_jobs(jobs).inserted

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
            skip_researched_urls=not criteria.include_reviewed,
        )
        found_count += company_report.raw_records
        if company_report.companies_checked:
            coverage_note = (
                f"Company career search: {company_report.companies_checked} tracked companies, "
                f"{company_report.boards_resolved} public ATS boards resolved, "
                f"{company_report.pages_checked} pages/feed requests, "
                f"{company_report.raw_records} listings parsed, "
                f"{company_report.jobs_indexed} new records indexed, "
                f"{company_report.researched_urls_skipped} previously researched detail URLs not refetched, "
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
        message="Screening cached listings for AI engineering and confirmed work location before Jev.",
        checked_sources=checked_notes,
        found_count=found_count,
    )

    prune_expired_data(database_path)
    indexed = all_active_jobs(database_path)
    visible = [job for job in indexed if not job.get("hidden")]
    eligible, cached_excluded = focused_jobs(visible)
    candidates = annotate_jobs(eligible, criteria)
    candidates, scope_excluded = apply_candidate_search_scope(candidates, criteria)
    candidates, research_counts = partition_researched_jobs(
        database_path,
        candidates,
        include_reviewed=criteria.include_reviewed,
    )
    checked_notes.append(
        f"Local AI engineering filter: {len(candidates)} candidates for Jev from "
        f"{len(visible)} active visible indexed listings; "
        f"{sum(cached_excluded.values())} cached listings excluded ({focus_note(cached_excluded)}). "
        f"Fetched listings excluded before indexing: {sum(ingestion_excluded.values())} "
        f"({focus_note(ingestion_excluded)}). These are local relevance decisions, not Jev scores."
    )
    workplace_scope = (
        f"Confirmed remote eligibility from {criteria.work_from} or an explicitly located role in "
        f"{criteria.local_workplace_city} is required; unverified locations are excluded before Jev."
        if criteria.workplace == "remote_preferred"
        else f"Workplace setting: {criteria.workplace}."
    )
    language_scope = (
        " English requirements are allowed; explicit Italian-language requirements are excluded."
        if criteria.exclude_italian_requirement
        else " No Italian-language exclusion is applied."
    )
    exclusion_labels = {
        "explicit_italian_requirement": "explicit Italian-language requirement(s)",
        "remote_outside_work_from_region": "remote role(s) outside the selected work-from region",
        "remote_region_unverified": "remote role(s) without confirmed work-from eligibility",
        "in_person_outside_local_city": "hybrid/on-site role(s) outside the selected local city",
        "workplace_city_unverified": "role(s) without confirmed workplace or local-city eligibility",
    }
    exclusions = ", ".join(
        f"{count} {exclusion_labels[key]}"
        for key, count in sorted(scope_excluded.items())
        if key in exclusion_labels
    )
    checked_notes.append(
        f"Workplace and language scope: {workplace_scope}{language_scope}"
        + (f" Locally excluded: {exclusions}." if exclusions else " No listings excluded by these rules.")
    )
    review_note = (
        f"Listing URL tracking: {research_counts['new']} new, "
        f"{research_counts['changed']} changed since review, "
        f"{research_counts['reviewed']} unchanged previously reviewed, and "
        f"{research_counts['same_run']} repeated URL identity/alias entries."
    )
    if criteria.include_reviewed:
        review_note += " Previously reviewed listings were deliberately included in this search."
    elif research_counts["reviewed"]:
        review_note += " Unchanged reviewed listings were kept in their original search snapshots."
    checked_notes.append(review_note)
    save_run_results(
        database_path,
        run_id,
        candidates,
        score_state="unscored",
        score_reason="Waiting for Jev to assess profile fit and search filters.",
    )
    if not checked_notes:
        checked_notes.append(
            "No source needed a refresh; results use the current local index."
            if due_sources == []
            else "No source returned a listing."
        )
    message = (
        f"Search ready: {len(candidates)} active listings will be assessed against your filters."
    )
    if auto_jev:
        update_run(
            database_path,
            run_id,
            status="scoring",
            stage="jev",
            message=(
                f"Jev is preparing to assess {len(candidates)} listings against your profile "
                "and search filters."
            ),
            checked_sources=checked_notes,
            found_count=found_count,
            matched_count=0,
            scored_count=0,
        )
        run_jev_scoring(database_path, settings, run_id)
        return
    update_run(
        database_path,
        run_id,
        status="complete",
        stage="done",
        message=f"{message} Jev was not run for this search.",
        checked_sources=checked_notes,
        found_count=found_count,
        matched_count=0,
        scored_count=0,
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
    jobs = [
        job
        for job in get_run_results(database_path, run_id)
        if job.get("filter_status") == "unassessed" or job.get("score_state") != "scored"
    ]
    jobs, excluded = focused_jobs(jobs)
    if excluded:
        notes = list(run.get("checked_sources") or [])
        notes.append(
            f"Scoring retry: locally skipped {sum(excluded.values())} out-of-focus listings "
            f"({focus_note(excluded)}); historical results remain unchanged."
        )
        update_run(database_path, run_id, checked_sources=notes)
    if not jobs:
        mark_researched_run_results(database_path, run_id)
        counts = get_run_result_counts(database_path, run_id)
        update_run(
            database_path,
            run_id,
            status="complete",
            stage="done",
            message=(
                "No new unreviewed listing URLs are available; unchanged previously researched "
                "links were skipped. Open Search history or include previously reviewed links "
                "to assess them again."
                if counts["total"] == 0
                else "No unassessed AI-focused candidates remain for Jev. Historical results are retained."
            ),
            matched_count=counts["matches"],
            scored_count=counts["scored"],
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
        mark_researched_run_results(database_path, run_id)
        counts = get_run_result_counts(database_path, run_id)
        update_run(
            database_path,
            run_id,
            status="complete",
            stage="done",
            message=result.message,
            matched_count=counts["matches"],
            scored_count=counts["scored"],
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
