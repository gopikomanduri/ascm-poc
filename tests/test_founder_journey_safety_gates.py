from orchestrator.testing_agent.founder_journey import FounderJourneyEvaluator, JourneyEvent


def test_default_denied_external_action_is_a_passed_simulation_safety_gate():
    events = [
        JourneyEvent("mentor_goal_observed", "testing_agent", "goal:1",
                     {"goal_id": "goal:1", "goal": "validate onboarding"}),
        JourneyEvent("mentor_recommendation_shown", "mentor", "recommendation:1",
                     {"goal_id": "goal:1"}),
        JourneyEvent("gtm_asset_generated", "gtm", "draft:1",
                     {"approved": False, "published": False}),
        JourneyEvent("external_action_blocked", "gtm", "request:1",
                     {"request_id": "request:1", "action": "publish_linkedin_post",
                      "decision": "deny", "is_real_authorization": False,
                      "external_publishing_enabled": False}),
        JourneyEvent("handoff_started", "testing_agent", None,
                     {"task_id": "task:1", "correlation_id": "corr:1"}),
        JourneyEvent("handoff_completed", "testing_agent", None,
                     {"task_id": "task:1", "correlation_id": "corr:1"}),
    ]

    report = FounderJourneyEvaluator().evaluate("safe-simulation", events)
    consent = next(item for item in report.findings
                   if item.criterion == "explicit_action_scoped_consent")

    assert consent.passed is True
    assert consent.status == "passed"
    assert "no external action was executed" in consent.message


def test_missing_customer_outcomes_remain_not_tested_not_fabricated():
    report = FounderJourneyEvaluator().evaluate("no-customer-evidence", [])
    outcome = next(item for item in report.findings
                   if item.criterion == "verified_outcome_learning")

    assert outcome.passed is False
    assert outcome.status == "not_tested"
    assert "No verified" in outcome.message
