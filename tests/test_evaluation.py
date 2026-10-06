from __future__ import annotations

from types import SimpleNamespace

from clue_ai.config import Settings, _money
from clue_ai.evaluation import (
    _link_is_structurally_valid,
    keyword_hits,
    ndcg_at_k,
    run_live_benchmark,
    synthetic_benchmark,
)
from clue_ai.filters import filter_jobs


def test_synthetic_jev_benchmark_hard_filters_match_the_fixed_expected_labels():
    profile, criteria, cases = synthetic_benchmark()
    selected = filter_jobs([case.job.__dict__ for case in cases], criteria)
    selected_titles = {job["title"] for job in selected}
    expected_titles = {
        case.job.title for case in cases if case.should_pass_hard_filters
    }

    assert len(cases) == 8
    assert selected_titles == expected_titles
    assert len({case.job.title for case in cases}) == len(cases)
    assert profile.profile_language == "en"


def test_synthetic_benchmark_includes_stale_duplicate_and_local_only_links():
    profile, _criteria, cases = synthetic_benchmark()
    stale_jobs = [case.job for case in cases if "SYN-05" == case.job.external_id]

    assert len(stale_jobs) == 1
    assert _link_is_structurally_valid(cases[0].job.canonical_url)
    assert not _link_is_structurally_valid("http://benchmark.example/jobs/unsafe")
    assert keyword_hits(cases[0].job.__dict__, profile) > keyword_hits(
        cases[3].job.__dict__, profile
    )


def test_ndcg_rewards_a_relevance_ordered_rank_and_stays_within_zero_and_one():
    relevance = {"best": 4, "middle": 2, "low": 1}

    ideal = ndcg_at_k(["best", "middle", "low"], relevance, 3)
    reversed_order = ndcg_at_k(["low", "middle", "best"], relevance, 3)

    assert ideal == 1.0
    assert 0 <= reversed_order < ideal


def test_benchmark_harness_uses_one_synthetic_batch_and_reads_metrics_before_cleanup(
    tmp_path, monkeypatch
):
    settings = Settings(
        data_dir=tmp_path / "unused",
        api_key="synthetic-key",
        model="jev-1.13.0",
        monthly_jev_budget_usd=4.0,
    )
    monkeypatch.setattr("clue_ai.evaluation.Settings.from_environment", lambda: settings)
    calls = []

    class FakeClient:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def system_one(self, *, state, questions):
            calls.append((state, questions))
            return SimpleNamespace(
                model="jev-test",
                usage=SimpleNamespace(input_tokens=1_200),
                choices={
                    name: SimpleNamespace(
                        choice="3", confidence=0.8, probabilities={"3": 1.0}
                    )
                    for name in questions
                },
            )

    report = run_live_benchmark(lambda **_kwargs: FakeClient())

    assert len(calls) == 1
    assert len(calls[0][1]) == 63
    assert report["api_requests"] == 1
    assert report["scored_count"] == 5
    assert report["unscored_count"] == 0
    assert report["hard_filter_false_positives"] == []
    assert report["hard_filter_false_negatives"] == []
    assert report["duplicate_records_detected"] == 1
    assert 0 <= report["jev_ndcg_at_5"] <= 1
    assert 0 <= report["keyword_ndcg_at_5"] <= 1
    assert report["app_ledger_open_reserve_usd"] == 0


def test_app_jev_budget_configuration_cannot_exceed_four_dollars():
    assert _money("9", 4.0) == 4.0
    assert _money("3.5", 4.0) == 3.5
