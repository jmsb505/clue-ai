from __future__ import annotations

import argparse
import json
import math
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from clue_ai.config import Settings
from clue_ai.database import initialize, save_profile, save_search_run, set_jev_consent
from clue_ai.domain import CandidateProfile, NormalizedJob, SearchCriteria
from clue_ai.filters import filter_jobs
from clue_ai.jev import score_run
from clue_ai.jobs import canonical_url
from clue_ai.repository import (
    all_active_jobs,
    get_run_results,
    monthly_jev_usage,
    save_jobs_with_report,
    save_run_results,
)


@dataclass(frozen=True)
class BenchmarkCase:
    job: NormalizedJob
    relevance: int
    should_pass_hard_filters: bool


class BenchmarkRunError(RuntimeError):
    def __init__(self, phase: str, error_type: str) -> None:
        super().__init__(f"{phase}: {error_type}")
        self.phase = phase
        self.error_type = error_type


def synthetic_benchmark() -> tuple[CandidateProfile, SearchCriteria, list[BenchmarkCase]]:
    """Return a small, fully synthetic profile and fixed relevance benchmark."""
    profile = CandidateProfile(
        summary=(
            "Synthetic mid-career data analyst with five years building reliable analytics "
            "datasets, reporting, and decision tools for product and operations teams."
        ),
        target_roles="Analytics Engineer, Data Analyst",
        skills="SQL, Python, dbt, Power BI, data modeling, dashboard design",
        experience=(
            "Five years creating dbt models and Python data workflows, validating datasets, "
            "and explaining findings to product and business partners."
        ),
        education="Bachelor's degree in statistics",
        languages="English",
        profile_language="en",
    )
    criteria = SearchCriteria(
        work_from="Italy",
        workplace="remote",
        must_have="SQL, Python",
        nice_to_have="SaaS analytics",
        include_unknown_location=False,
        posted_within_days=365,
    )
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stale = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat(timespec="seconds")
    examples = [
        (
            "SYN-01",
            "Analytics Engineer",
            "Synthetic Northstar Analytics",
            "Italy · Remote",
            """This fully remote Analytics Engineer role is open to candidates living in Italy.
            The team builds dbt models and trusted product datasets with SQL and Python, then
            works with product partners to improve decisions. It asks for experience with data
            modeling, testing, documentation, and communicating findings. Five years of relevant
            analytics experience is welcome, and the company works across European time zones.""",
            "remote",
            4,
            True,
            now,
        ),
        (
            "SYN-02",
            "Data Analyst",
            "Synthetic Alder Product",
            "Europe · Remote",
            """This Data Analyst role is fully remote for applicants based in Europe, including
            Italy. The analyst uses SQL and Python to answer product questions, maintains Power BI
            dashboards, checks experiment data, and presents findings to product managers. The
            team values clear writing and sound statistical judgment. Prior SaaS experience is
            useful, but the role is suitable for a mid-career analyst who can work independently.""",
            "remote",
            4,
            True,
            now,
        ),
        (
            "SYN-03",
            "Business Intelligence Analyst",
            "Synthetic Meridian Research",
            "Europe · Remote",
            """This Business Intelligence Analyst works remotely from Italy or elsewhere in
            Europe. The role uses SQL and Python for reporting, quality checks, and recurring
            analysis. Power BI is used for dashboards; dbt is not part of the current stack.
            The analyst partners with finance and operations and presents results to nontechnical
            teams. The job asks for three years of experience and careful attention to detail.""",
            "remote",
            3,
            True,
            now,
        ),
        (
            "SYN-04",
            "Customer Insights Analyst",
            "Synthetic Lumen Support",
            "Italy · Remote",
            """This customer insights position is remote for people located in Italy. It uses SQL
            and Python to investigate support trends, prepare weekly reports, and recommend
            process improvements. The work is closer to customer operations than product
            analytics, but includes data validation, dashboard updates, and collaboration with
            business teams. The company welcomes applicants with analytics experience.""",
            "remote",
            2,
            True,
            now,
        ),
        (
            "SYN-05",
            "Sales Operations Analyst",
            "Synthetic Cedar Systems",
            "Europe · Remote",
            """This remote Sales Operations Analyst role is open across Europe, including Italy.
            It uses SQL and Python to reconcile pipeline reports, maintain forecasting dashboards,
            and investigate data quality. Most work supports sales planning rather than product
            analytics. The role asks for experience working with CRM exports, sales leaders, and
            monthly targets; dbt and experimentation are not required.""",
            "remote",
            2,
            True,
            stale,
        ),
        (
            "SYN-06",
            "Data Analyst — On-site",
            "Synthetic Milan Office",
            "Milan, Italy",
            """This on-site Data Analyst role in Milan uses SQL and Python to build reports and
            dashboards. Applicants need to attend the office five days each week. The description
            otherwise matches the synthetic candidate's background and experience.""",
            "onsite",
            4,
            False,
            now,
        ),
        (
            "SYN-07",
            "Analytics Engineer — United States only",
            "Synthetic Redwood Data",
            "Remote · United States only",
            """This fully remote Analytics Engineer role is limited to people who live and are
            authorized to work in the United States. It uses SQL, Python, and dbt to maintain
            analytics models and support product teams. The company cannot hire in Italy or other
            European countries for this position.""",
            "remote",
            4,
            False,
            now,
        ),
        (
            "SYN-08",
            "Remote Reporting Analyst",
            "Synthetic Kestrel Metrics",
            "Italy · Remote",
            """This remote Reporting Analyst role is open to candidates in Italy. The work uses SQL
            and Power BI to prepare operational reports, validate metrics, and support business
            reviews. The team collaborates with analysts and operations managers and builds
            recurring reports from carefully validated business data.""",
            "remote",
            3,
            False,
            now,
        ),
    ]
    cases = []
    for external_id, title, company, location, description, workplace, relevance, passes, checked in examples:
        url = f"https://benchmark.example/jobs/{external_id.casefold()}"
        cases.append(
            BenchmarkCase(
                job=NormalizedJob(
                    source_id="jobicy",
                    source_name="Synthetic benchmark",
                    external_id=external_id,
                    title=title,
                    company=company,
                    description=" ".join(description.split()),
                    source_url=url,
                    canonical_url=url,
                    location_raw=location,
                    workplace_type=workplace,
                    employment_type="full-time",
                    posted_at=now,
                    source_credit="Synthetic benchmark (no external source)",
                    last_checked_at=checked,
                ),
                relevance=relevance,
                should_pass_hard_filters=passes,
            )
        )
    return profile, criteria, cases


def keyword_hits(job: dict[str, Any], profile: CandidateProfile) -> int:
    text = " ".join(str(job.get(field) or "") for field in ("title", "description")).casefold()
    terms = [
        "analytics engineer",
        "data analyst",
        "sql",
        "python",
        "dbt",
        "power bi",
        "data modeling",
    ]
    candidate_text = " ".join(profile.fit_fields().values()).casefold()
    return sum(1 for term in terms if term in candidate_text and term in text)


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, int], k: int) -> float:
    def dcg(grades: list[int]) -> float:
        return sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(grades))

    actual = dcg([relevance.get(job_id, 0) for job_id in ranked_ids[:k]])
    ideal = dcg(sorted(relevance.values(), reverse=True)[:k])
    return actual / ideal if ideal else 0.0


def _benchmark_job_id(job: dict[str, Any]) -> str:
    return str(job.get("title") or "")


def _link_is_structurally_valid(url: str) -> bool:
    parts = urlsplit(url)
    return (
        parts.scheme == "https"
        and bool(parts.hostname)
        and not parts.username
        and not parts.password
        and canonical_url(url) == url
    )


def run_live_benchmark(client_factory: Callable[..., Any] | None = None) -> dict[str, Any]:
    phase = "load local settings"
    try:
        base_settings = Settings.from_environment()
        if not base_settings.api_key:
            raise RuntimeError("No TypeSafe API key is configured; no request was made.")
        profile, criteria, cases = synthetic_benchmark()
        run_id = "synthetic-jev-benchmark"
        phase = "create disposable local database"
        with tempfile.TemporaryDirectory(prefix="clue-jev-benchmark-") as temp_dir:
            settings = replace(
                base_settings,
                data_dir=Path(temp_dir),
                monthly_jev_budget_usd=min(base_settings.monthly_jev_budget_usd, 4.0),
            )
            initialize(settings.database_path)
            set_jev_consent(settings.database_path, True)
            save_profile(settings.database_path, profile)
            save_search_run(settings.database_path, run_id, criteria)
            duplicate_report = save_jobs_with_report(
                settings.database_path,
                [case.job for case in cases] + [cases[0].job],
            )
            indexed_jobs = all_active_jobs(settings.database_path)
            filtered_jobs = filter_jobs(indexed_jobs, criteria)
            save_run_results(settings.database_path, run_id, filtered_jobs)
            stored_results = get_run_results(settings.database_path, run_id)
            phase = "score synthetic listings with Jev"
            fit_result = score_run(
                settings.database_path,
                settings,
                run_id,
                stored_results,
                profile,
                criteria,
                client_factory=client_factory,
            )
            phase = "read temporary evaluation results"
            results = get_run_results(settings.database_path, run_id)
            by_title = {_benchmark_job_id(job): job for job in results}
            case_by_title = {case.job.title: case for case in cases}
            relevance = {
                key: case.relevance for key, case in case_by_title.items() if key in by_title
            }
            case_order = [case.job.title for case in cases if case.job.title in by_title]
            jev_order = sorted(
                case_order,
                key=lambda key: (
                    by_title[key].get("combined_score") is not None,
                    float(by_title[key].get("combined_score") or -1.0),
                ),
                reverse=True,
            )
            keyword_order = sorted(
                case_order,
                key=lambda key: keyword_hits(by_title[key], profile),
                reverse=True,
            )
            expected = {case.job.title for case in cases if case.should_pass_hard_filters}
            actual = set(case_order)
            false_positives = sorted(actual - expected)
            false_negatives = sorted(expected - actual)
            stale_ids = sorted(
                key for key in case_order if by_title[key].get("freshness_status") == "stale"
            )
            usage = monthly_jev_usage(settings.database_path, settings.monthly_jev_budget_usd)
            rows = []
            for rank, title in enumerate(jev_order, start=1):
                job = by_title[title]
                source_url = (job.get("sources") or [{}])[0].get("source_url") or ""
                rows.append(
                    {
                        "id": case_by_title[title].job.external_id,
                        "title": job["title"],
                        "human_relevance": case_by_title[title].relevance,
                        "keyword_hits": keyword_hits(job, profile),
                        "jev_rank": rank,
                        "fit_score": job.get("combined_score"),
                        "confidence": job.get("confidence"),
                        "score_state": job.get("score_state"),
                        "freshness": job.get("freshness_status"),
                        "canonical_link_valid": _link_is_structurally_valid(source_url),
                    }
                )
            report = {
                "candidate_and_jobs_are_synthetic": True,
                "api_key_value_printed": False,
                "api_requests": usage["requests"],
                "app_ledger_cost_usd": usage["used_usd"],
                "app_ledger_open_reserve_usd": sum(_usage_rows(settings.database_path)),
                "app_budget_usd": usage["budget_usd"],
                "duplicate_records_detected": duplicate_report.deduplicated,
                "hard_filter_expected_passes": len(expected),
                "hard_filter_actual_passes": len(actual),
                "hard_filter_false_positives": false_positives,
                "hard_filter_false_negatives": false_negatives,
                "stale_filtered_results": stale_ids,
                "canonical_links_structurally_valid": all(
                    row["canonical_link_valid"] for row in rows
                ),
                "jev_ndcg_at_5": ndcg_at_k(jev_order, relevance, 5),
                "keyword_ndcg_at_5": ndcg_at_k(keyword_order, relevance, 5),
                "scored_count": fit_result.scored_count,
                "unscored_count": fit_result.unscored_count,
                "jev_message": fit_result.message,
                "ranked_results": rows,
            }
        return report
    except Exception as exc:  # noqa: BLE001 - keep failure output free of payloads and credentials.
        raise BenchmarkRunError(phase, type(exc).__name__) from None


def _usage_rows(database_path: Path) -> list[float]:
    from clue_ai.repository import connect

    with connect(database_path) as db:
        return [
            float(row["reserved_usd"] or 0)
            for row in db.execute("SELECT reserved_usd FROM jev_usage WHERE status = 'reserved'")
        ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic-only Jev ranking benchmark.")
    parser.add_argument(
        "--live",
        action="store_true",
        help="Send this synthetic benchmark to Jev once; all data and the usage ledger are temporary.",
    )
    args = parser.parse_args()
    if not args.live:
        print("No API request made. Review the synthetic data, then pass --live to call Jev once.")
        return 0
    try:
        report = run_live_benchmark()
    except Exception as exc:  # noqa: BLE001 - keep CLI output free of request details and credentials.
        phase = exc.phase if isinstance(exc, BenchmarkRunError) else "initialize benchmark"
        error_type = exc.error_type if isinstance(exc, BenchmarkRunError) else type(exc).__name__
        print(json.dumps({"error": error_type, "phase": phase, "request_details_printed": False}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
