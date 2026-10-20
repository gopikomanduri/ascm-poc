from orchestrator.testing_agent.founder_journey import FounderJourneyEvaluator, JourneyEvent


def event(kind, source="ascm-ui", ref=None, **details):
    return JourneyEvent(kind, source, ref, details)


def test_complete_founder_journey_passes_only_with_evidence_and_scoped_consent():
    events = [
        event("mentor_goal_observed", ref="session:goal-1", goal_id="goal-1",
              goal="Validate cross-repository handoff pain", simulated=False),
        event("mentor_recommendation_shown", ref="session:mentor-1", goal_id="goal-1"),
        event("gtm_cycle_generated", ref="experiment:exp-1"),
        event("action_approved", ref="approval:1", action="send_outreach", request_id="request-1",
              approval_id="approval-1", approver="founder", is_real_authorization=True),
        event("external_action_completed", ref="audit:send-1", action="send_outreach", request_id="request-1"),
        event("handoff_started", task_id="task-1", correlation_id="corr-1"),
        event("handoff_completed", task_id="task-1", correlation_id="corr-1"),
        event("customer_reply", ref="crm:reply-1", verified=True, verified_by="founder"),
    ]
    report = FounderJourneyEvaluator().evaluate("founder-week-1", events)
    assert report.passed
    assert report.generated_asset_count == 1
    assert report.verified_outcome_counts["customer_reply"] == 1


def test_generated_gtm_asset_is_not_a_verified_outcome():
    report = FounderJourneyEvaluator().evaluate("gtm-draft", [
        event("mentor_goal_observed"),
        event("mentor_recommendation_shown"),
        event("gtm_cycle_generated"),
        event("handoff_started", task_id="t1", correlation_id="c1"),
    ])
    assert report.verified_outcome_counts["customer_reply"] == 0
    assert report.generated_asset_count == 1
    assert not report.passed


def test_external_action_without_matching_approval_fails():
    report = FounderJourneyEvaluator().evaluate("unsafe-send", [
        event("mentor_goal_observed"),
        event("mentor_recommendation_shown"),
        event("handoff_started", task_id="t1", correlation_id="c1"),
        event("external_action_completed", action="publish_campaign"),
    ])
    finding = next(f for f in report.findings if f.criterion == "explicit_action_scoped_consent")
    assert not finding.passed


def test_outcome_without_evidence_reference_does_not_pass_learning():
    report = FounderJourneyEvaluator().evaluate("unverified-reply", [
        event("mentor_goal_observed"),
        event("mentor_recommendation_shown"),
        event("handoff_started", task_id="t1", correlation_id="c1"),
        event("customer_reply"),
    ])
    finding = next(f for f in report.findings if f.criterion == "verified_outcome_learning")
    assert not finding.passed


def test_gtm_success_claim_without_verified_outcome_fails():
    report = FounderJourneyEvaluator().evaluate("false-success", [
        event("mentor_goal_observed"),
        event("mentor_recommendation_shown"),
        event("handoff_started", task_id="t1", correlation_id="c1"),
        event("gtm_success_claimed"),
    ])
    finding = next(f for f in report.findings if f.criterion == "gtm_proposal_distinguished_from_outcome")
    assert not finding.passed


def test_gtm_success_claim_requires_same_cycle_verified_outcome():
    unrelated = FounderJourneyEvaluator().evaluate("unrelated-outcome", [
        event("gtm_asset_generated", ref="draft:1"),
        event("gtm_success_claimed", ref="claim:1"),
        event("customer_reply", ref="crm:reply-1", verified=True, cycle_id="cycle-other"),
    ])
    linked = FounderJourneyEvaluator().evaluate("linked-outcome", [
        event("gtm_asset_generated", ref="draft:2"),
        event("gtm_success_claimed", ref="claim:2", cycle_id="cycle-2"),
        event("customer_reply", ref="crm:reply-2", verified=True, cycle_id="cycle-2"),
    ])
    unrelated_finding = next(f for f in unrelated.findings if f.criterion == "gtm_proposal_distinguished_from_outcome")
    linked_finding = next(f for f in linked.findings if f.criterion == "gtm_proposal_distinguished_from_outcome")
    assert unrelated_finding.passed is False
    assert linked_finding.passed is True


def test_approval_for_different_action_instance_does_not_authorize_external_action():
    report = FounderJourneyEvaluator().evaluate("wrong-approval", [
        event("mentor_goal_observed", ref="goal:1", goal_id="g1", goal="validate demand"),
        event("mentor_recommendation_shown", ref="mentor:1", goal_id="g1"),
        event("action_approved", ref="approval:1", action="send_outreach", request_id="request-old",
              approval_id="approval-1", approver="founder", is_real_authorization=True),
        event("external_action_completed", ref="audit:1", action="send_outreach", request_id="request-new"),
    ])
    finding = next(f for f in report.findings if f.criterion == "explicit_action_scoped_consent")
    assert finding.passed is False
