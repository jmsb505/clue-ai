from clue_ai.job_focus import assess_focus


def test_ai_architecture_analyst_with_engineering_work_reaches_jev():
    decision = assess_focus(
        {
            "title": "AI LLM Technology Architecture Analyst (Early Career)",
            "description": (
                "As a hands-on AI Engineer, this is a technical role. THE WORK: "
                "Design, build, and configure individual agents. Integrate foundation "
                "models into applications and develop end-to-end AI pipelines."
            ),
        }
    )

    assert decision.accepted
    assert decision.reason == "AI title with model implementation evidence"


def test_analyst_without_engineering_evidence_stays_out_of_jev():
    decision = assess_focus(
        {
            "title": "AI Analyst",
            "description": "Prepare business reports and summarize AI market trends.",
        }
    )

    assert not decision.accepted
