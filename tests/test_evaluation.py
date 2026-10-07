from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

from clue_ai.config import Settings, _money
from clue_ai.database import connect, initialize
from clue_ai.evaluation import (
    MAX_EVALUATION_BUDGET_USD,
    SYNTHETIC_PREPARATION_PROJECTS,
    WRITING_RUBRIC,
    _bounded_evaluation_budget,
    _diagnoser_quality_check,
    _EvaluationTemporaryDirectory,
    _hiring_manager_quality_check,
    _link_is_structurally_valid,
    _portfolio_specificity_check,
    _recruiter_quality_check,
    _synthetic_preparation_case,
    _synthetic_writing_rubric,
    binary_metrics,
    categorical_metrics,
    keyword_hits,
    ndcg_at_k,
    run_live_benchmark,
    run_live_grounding_benchmark,
    synthetic_benchmark,
    synthetic_grounding_benchmark,
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
    assert all(case.rationale for case in cases)
    assert profile.target_roles.startswith("Junior AI Engineer")
    assert sum(case.should_pass_hard_filters for case in cases) == 5
    assert {case.expected_jev_filter_status for case in cases[:5]} == {
        "match", "review", "conflict"
    }


def test_ndcg_rewards_a_relevance_ordered_rank_and_stays_within_zero_and_one():
    relevance = {"best": 4, "middle": 2, "low": 1}

    ideal = ndcg_at_k(["best", "middle", "low"], relevance, 3)
    reversed_order = ndcg_at_k(["low", "middle", "best"], relevance, 3)

    assert ideal == 1.0
    assert 0 <= reversed_order < ideal


def test_binary_metrics_report_filter_false_positives_and_false_negatives():
    metrics = binary_metrics(
        {"eligible": True, "wrong-country": False, "missing-skill": False},
        {"eligible": True, "wrong-country": True, "missing-skill": False},
    )

    assert metrics == {
        "true_positive": 1,
        "false_positive": 1,
        "false_negative": 0,
        "true_negative": 1,
        "precision": 0.5,
        "recall": 1.0,
        "f1": 2 / 3,
        "accuracy": 2 / 3,
        "case_count": 3,
    }


def test_grounding_benchmark_covers_supported_contradicted_and_missing_evidence():
    cases = synthetic_grounding_benchmark()
    expected = {case.case_id: case.expected for case in cases}
    metrics = categorical_metrics(expected, expected)

    assert len(cases) == 12
    assert {case.expected for case in cases} == {"supported", "contradicted", "unresolved"}
    assert all(case.assertion and case.evidence and case.rationale for case in cases)
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert metrics["confusion_matrix"]["supported"]["supported"] == 5
    assert metrics["confusion_matrix"]["contradicted"]["contradicted"] == 3
    assert metrics["confusion_matrix"]["unresolved"]["unresolved"] == 4


def test_grounding_metrics_reject_a_false_supported_label():
    metrics = categorical_metrics(
        {"metric": "unresolved", "degree": "contradicted", "paraphrase": "supported"},
        {"metric": "supported", "degree": "contradicted", "paraphrase": "supported"},
    )

    assert metrics["accuracy"] == 2 / 3
    assert metrics["per_class"]["supported"]["precision"] == 0.5
    assert metrics["per_class"]["unresolved"]["recall"] == 0.0


def test_writing_rubric_names_all_requested_quality_dimensions():
    assert {
        "evidence_traceability",
        "factual_accuracy",
        "role_specificity",
        "voice",
        "xyz_integrity",
        "question_adherence",
        "research_provenance",
        "concision",
    } <= set(WRITING_RUBRIC)
    assert all(WRITING_RUBRIC.values())


def test_live_preparation_rubric_fails_a_title_only_cover_letter():
    rubric = _synthetic_writing_rubric(
        grounding_results=[
            {"status": "supported", "included_in_artifact": True},
            {"status": "unresolved", "included_in_artifact": False},
        ],
        diagnoser_line_ids_valid=True,
        recruiter_selected_cv_correct=True,
        resume_line_order_complete=True,
        artifact_checks=[
            {
                "artifact_type": "cover_letter",
                "generated": False,
                "body_paragraph_count": 0,
            }
        ],
    )

    assert rubric["status"] == "fail"
    assert rubric["mechanical_gates"]["only_jev_supported_blocks_included"] == "pass"
    assert rubric["mechanical_gates"]["cover_letter_body_present"] == "fail"
    assert rubric["criteria"]["voice"] == "human_review_required"
    assert rubric["criteria"]["question_adherence"] == "not_applicable_no_questions"


def test_live_preparation_fixture_represents_a_multi_project_portfolio():
    names = [item["name"] for item in SYNTHETIC_PREPARATION_PROJECTS]
    families = {family for item in SYNTHETIC_PREPARATION_PROJECTS for family in item["role_families"]}

    assert len(names) >= 12
    assert len(set(names)) == len(names)
    assert {"llm", "computer_vision", "agents", "data", "evaluation"} <= families
    assert all(item["claim"] in item["resume_line"] for item in SYNTHETIC_PREPARATION_PROJECTS)
    assert any(
        marker.replace(" ", "").casefold() in item["claim"].replace(" ", "").casefold()
        for item in SYNTHETIC_PREPARATION_PROJECTS
        for marker in item["evidence_markers"]
    )


def test_portfolio_specificity_requires_project_and_supported_detail_in_cover_letter():
    project = SYNTHETIC_PREPARATION_PROJECTS[0]
    resume = "\n".join(item["resume_line"] for item in SYNTHETIC_PREPARATION_PROJECTS)

    broad = _portfolio_specificity_check(resume, "I can bring useful technical experience.")
    specific = _portfolio_specificity_check(
        resume,
        f"In {project['name']}, I measured {project['evidence_markers'][-1]} while building the service.",
    )

    assert broad["status"] == "fail"
    assert broad["cover_letter_project_count"] == 0
    assert specific["status"] == "pass"
    assert specific["cover_letter_project_count"] == 1
    assert specific["cover_letter_evidence_marker_count"] >= 1


def test_portfolio_specificity_requires_project_evidence_for_the_target_family():
    resume = "\n".join(item["resume_line"] for item in SYNTHETIC_PREPARATION_PROJECTS)
    llm_project = next(item for item in SYNTHETIC_PREPARATION_PROJECTS if item["name"] == "SignalForge")
    vision_project = next(item for item in SYNTHETIC_PREPARATION_PROJECTS if item["name"] == "EdgeReg")
    unrelated_letter = f"In {llm_project['name']}, {llm_project['evidence_markers'][0]} supported retrieval quality."
    targeted_letter = f"In {vision_project['name']}, the work reached {vision_project['evidence_markers'][0]}."

    assert _portfolio_specificity_check(
        resume,
        unrelated_letter,
        target_family="computer_vision",
    )["status"] == "fail"
    targeted = _portfolio_specificity_check(
        resume,
        targeted_letter,
        target_family="computer_vision",
    )
    assert targeted["status"] == "pass"
    assert targeted["cover_letter_relevant_projects_with_supported_detail"] == ["EdgeReg"]


def test_synthetic_preparation_cases_cover_two_eligible_role_families():
    llm_case = _synthetic_preparation_case("SYN-01")
    vision_case = _synthetic_preparation_case("SYN-02")

    assert llm_case.job.title == "Junior LLM Engineer"
    assert vision_case.job.title == "Entry-Level Computer Vision Engineer"
    assert llm_case.expected_jev_filter_status == vision_case.expected_jev_filter_status == "match"
    try:
        _synthetic_preparation_case("SYN-07")
    except ValueError:
        pass
    else:
        raise AssertionError("An ineligible case was accepted for live preparation evaluation.")


def test_diagnoser_fixture_allows_clean_cv_but_requires_known_defect_detection():
    clean = _diagnoser_quality_check(
        {"diagnostics": [], "overall_note": "No concrete extraction risks were visible."},
        source_id="cv-synthetic",
        valid_line_ids={"L0001"},
    )
    assert clean["status"] == "pass"
    assert clean["detection_recall_measured"] is False

    detected = _diagnoser_quality_check(
        {
            "diagnostics": [
                {
                    "source_id": "synthetic-diagnoser-challenge",
                    "line_id": "L0001",
                    "issue": "The letter-spaced section heading may be hard to recognize.",
                    "suggested_fix": "Use the standard Experience heading.",
                }
            ],
            "overall_note": "The fixture has one seeded heading defect.",
        },
        source_id="synthetic-diagnoser-challenge",
        valid_line_ids={"L0001", "L0002"},
        expected_line_id="L0001",
    )
    assert detected["status"] == "pass"
    assert detected["expected_line_detected"] is True

    missed = _diagnoser_quality_check(
        {"diagnostics": [], "overall_note": "No risks."},
        source_id="synthetic-diagnoser-challenge",
        valid_line_ids={"L0001", "L0002"},
        expected_line_id="L0001",
    )
    assert missed["status"] == "fail"
    assert missed["expected_line_detected"] is False


def test_recruiter_quality_requires_source_lines_and_role_coverage():
    output = {
        "selected_cv_id": "cv-synthetic",
        "requirements": [
            {
                "requirement": "Python and PyTorch for RAG retrieval",
                "document_coverage": "covered",
                "cv_line_ids": ["L0002"],
                "claim_ids": ["claim-1"],
            },
            {
                "requirement": "Evaluate citation quality",
                "document_coverage": "partial",
                "cv_line_ids": ["L0003"],
                "claim_ids": [],
            },
        ],
        "coverage_note": "CV evidence mapping only; it does not assess job fit.",
    }
    groups = (("retrieval", "rag"), ("python",), ("pytorch",), ("citation", "evaluation"))
    result = _recruiter_quality_check(
        output,
        selected_cv_id="cv-synthetic",
        valid_cv_line_ids={"L0001", "L0002", "L0003"},
        valid_claim_ids={"claim-1"},
        role_keyword_groups=groups,
    )
    assert result["status"] == "pass"
    assert result["role_keyword_groups_matched"] == 4

    output["requirements"][0]["cv_line_ids"] = []
    result = _recruiter_quality_check(
        output,
        selected_cv_id="cv-synthetic",
        valid_cv_line_ids={"L0001", "L0002", "L0003"},
        valid_claim_ids={"claim-1"},
        role_keyword_groups=groups,
    )
    assert result["status"] == "fail"
    assert result["covered_or_partial_requirements_have_cv_lines"] is False


def test_hiring_manager_quality_gate_checks_exact_question_and_answer_preservation():
    questions = ["Q1", "Q2", "Q3"]
    answers = [{"question": question, "answer": "Synthetic answer."} for question in questions]
    assessments = [
        {
            **answer,
            "technical_evidence": "Addresses the defined test fixture.",
            "reasoning": "Explains a comparison against a baseline.",
            "clarity": "The point is stated directly.",
            "suggested_practice": "Add a failure case and trade-off.",
        }
        for answer in answers
    ]
    output = {"questions": questions, "answer_assessments": assessments}

    passing = _hiring_manager_quality_check(
        session_state="complete",
        questions=questions,
        expected_answers=answers,
        output=output,
    )
    assert passing["status"] == "pass"
    assert passing["assessment_fields_complete"] is True

    output["answer_assessments"][0]["answer"] = "Changed answer."
    failing = _hiring_manager_quality_check(
        session_state="complete",
        questions=questions,
        expected_answers=answers,
        output=output,
    )
    assert failing["status"] == "fail"
    assert failing["synthetic_answers_preserved"] is False


def test_hiring_manager_quality_gate_checks_role_specific_question_content():
    questions = [
        "How would you measure retrieval quality for a RAG system?",
        "How would you investigate a citation mismatch in a PyTorch pipeline?",
        "Which baseline would you use before changing the retrieval strategy?",
    ]
    answers = [{"question": question, "answer": "Synthetic answer."} for question in questions]
    assessments = [
        {
            **answer,
            "technical_evidence": "Addresses the synthetic role detail.",
            "reasoning": "Compares a baseline with a failure case.",
            "clarity": "Uses a direct explanation.",
            "suggested_practice": "Add a measurable test and trade-off.",
        }
        for answer in answers
    ]
    role_groups = (("retrieval", "rag"), ("citation",), ("pytorch",))
    result = _hiring_manager_quality_check(
        session_state="complete",
        questions=questions,
        expected_answers=answers,
        output={"questions": questions, "answer_assessments": assessments},
        role_keyword_groups=role_groups,
    )
    assert result["status"] == "pass"
    assert result["questions_are_role_specific"] is True

    generic_questions = ["Tell me about yourself.", "How do you work in a team?", "What are your goals?"]
    generic_answers = [{"question": question, "answer": "Synthetic answer."} for question in generic_questions]
    result = _hiring_manager_quality_check(
        session_state="complete",
        questions=generic_questions,
        expected_answers=generic_answers,
        output={"questions": generic_questions, "answer_assessments": [
            {**answer, "technical_evidence": "Synthetic", "reasoning": "Synthetic", "clarity": "Synthetic", "suggested_practice": "Synthetic"}
            for answer in generic_answers
        ]},
        role_keyword_groups=role_groups,
    )
    assert result["status"] == "fail"
    assert result["questions_are_role_specific"] is False


def test_evaluation_jev_budget_cannot_exceed_small_pilot_cap():
    assert _bounded_evaluation_budget(4.0, MAX_EVALUATION_BUDGET_USD) == 0.05
    assert _bounded_evaluation_budget(0.01, MAX_EVALUATION_BUDGET_USD) == 0.01
    for invalid in (0.0, -0.01, 0.051, float("inf"), float("nan")):
        try:
            _bounded_evaluation_budget(4.0, invalid)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Accepted unsafe evaluation cap: {invalid!r}")


def test_evaluation_data_is_retained_when_either_provider_has_unresolved_usage(tmp_path):
    def database_path_for(data_dir: Path) -> Path:
        return Settings(
            data_dir=data_dir,
            api_key="synthetic-key",
            model="jev-test",
            monthly_jev_budget_usd=0.05,
        ).database_path

    temporary = _EvaluationTemporaryDirectory(
        "clue-evaluation-retention-test-",
        database_path_for,
        parent_directory=tmp_path,
    )
    data_dir = Path(temporary.name)
    database_path = database_path_for(data_dir)
    initialize(database_path)
    with connect(database_path) as db:
        db.execute(
            """INSERT INTO openai_usage
               (id, request_id, job_id, month_key, stage, model, estimated_input_bytes,
                reserved_input_tokens, max_output_tokens, reserved_usd, input_usd_per_million,
                output_usd_per_million, search_usd_per_thousand, status, created_at)
               VALUES ('usage-openai', 'request-local', 'job-synthetic', '2026-10',
                       'rewriter', 'gpt-6-luna', 800, 200, 1200, 0.0036, 0.10, 0.50,
                       0.0, 'unknown', '2026-10-06T00:00:00Z')"""
        )
        db.execute(
            """INSERT INTO jev_usage
               (run_id, month_key, model, started_at, reserved_tokens, reserved_usd, status)
               VALUES (NULL, '2026-10', 'jev-test', '2026-10-06T00:00:00Z', 80000,
                       0.01, 'reserved')"""
        )

    try:
        temporary.cleanup()

        assert temporary.usage_recovery is not None
        assert temporary.usage_recovery["directory"] == str(data_dir.resolve())
        assert {item["provider"] for item in temporary.usage_recovery["unresolved_usage"]} == {
            "openai",
            "jev",
        }
        assert database_path.is_file()
        with connect(database_path) as db:
            assert db.execute("SELECT status FROM openai_usage").fetchone()["status"] == "unknown"
            assert db.execute("SELECT status FROM jev_usage").fetchone()["status"] == "reserved"
    finally:
        if data_dir.exists():
            shutil.rmtree(data_dir)


def test_evaluation_data_is_deleted_after_all_provider_usage_is_settled(tmp_path):
    def database_path_for(data_dir: Path) -> Path:
        return Settings(
            data_dir=data_dir,
            api_key="synthetic-key",
            model="jev-test",
            monthly_jev_budget_usd=0.05,
        ).database_path

    temporary = _EvaluationTemporaryDirectory(
        "clue-evaluation-cleanup-test-",
        database_path_for,
        parent_directory=tmp_path,
    )
    data_dir = Path(temporary.name)
    initialize(database_path_for(data_dir))

    temporary.cleanup()

    assert temporary.usage_recovery is None
    assert not data_dir.exists()


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
            selected_cases = [case for case in synthetic_benchmark()[2] if case.should_pass_hard_filters]
            expected_checks = {index: case.expected_jev_filter_checks for index, case in enumerate(selected_cases)}
            return SimpleNamespace(
                model="jev-test",
                usage=SimpleNamespace(input_tokens=1_200),
                choices={
                    name: SimpleNamespace(
                        choice=(
                            expected_checks[int(name.split("_")[1])][name.rsplit("_", 1)[-1]]
                            if "filter_" in name
                            else "3"
                        ),
                        confidence=0.8,
                        probabilities={"3": 1.0},
                    )
                    for name in questions
                },
            )

    report = run_live_benchmark(lambda **_kwargs: FakeClient())

    assert len(calls) == 1
    assert len(calls[0][1]) >= 60
    assert report["api_requests"] == 1
    assert report["app_budget_usd"] == MAX_EVALUATION_BUDGET_USD
    assert report["labels_source"] == "assistant_authored_synthetic_not_owner_validation"
    assert "not a probability" in report["jev_confidence_semantics"]
    assert report["scored_count"] == 5
    assert report["unscored_count"] == 0
    assert report["hard_filter_false_positives"] == []
    assert report["hard_filter_false_negatives"] == []
    assert report["duplicate_records_detected"] == 1
    assert 0 <= report["jev_ndcg_at_5"] <= 1
    assert 0 <= report["keyword_ndcg_at_5"] <= 1
    assert report["hard_filter_metrics"]["false_positive"] == 0
    assert report["hard_filter_metrics"]["false_negative"] == 0
    assert report["jev_filter_metrics"]["case_count"] == 5
    assert report["jev_filter_metrics"]["accuracy"] == 1.0
    assert report["jev_filter_metrics"]["confusion_matrix"]["conflict"]["conflict"] == 2
    assert all(item["accuracy"] == 1.0 for item in report["jev_filter_check_metrics"].values())
    assert all("filter_status" in row for row in report["ranked_results"])
    assert all("filter_checks" in row for row in report["ranked_results"])
    assert all(case.rationale for case in synthetic_benchmark()[2])
    assert report["app_ledger_open_reserve_usd"] == 0


def test_live_grounding_harness_uses_synthetic_data_and_separate_metrics(tmp_path, monkeypatch):
    settings = Settings(
        data_dir=tmp_path / "unused",
        api_key="synthetic-key",
        model="jev-1.13.0",
        monthly_jev_budget_usd=4.0,
    )
    monkeypatch.setattr("clue_ai.evaluation.Settings.from_environment", lambda: settings)
    cases = synthetic_grounding_benchmark()
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
                usage=SimpleNamespace(input_tokens=900),
                choices={
                    case.case_id: SimpleNamespace(choice=case.expected, confidence=0.9)
                    for case in cases
                },
            )

    report = run_live_grounding_benchmark(lambda **_kwargs: FakeClient())

    assert len(calls) == 1
    assert report["candidate_and_evidence_are_synthetic"] is True
    assert report["labels_source"] == "assistant_authored_synthetic_not_owner_validation"
    assert report["api_requests"] == 1
    assert report["metrics"]["accuracy"] == 1.0
    assert report["metrics"]["macro_f1"] == 1.0
    assert "categorical support verdict is authoritative" in report["confidence_policy"]
    assert all(item["confidence"] == 0.9 for item in report["case_results"].values())
    assert report["app_ledger_open_reserve_usd"] == 0


def test_app_jev_budget_configuration_cannot_exceed_four_dollars():
    assert _money("9", 4.0) == 4.0
    assert _money("3.5", 4.0) == 3.5
