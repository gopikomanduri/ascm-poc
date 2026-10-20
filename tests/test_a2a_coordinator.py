import pytest

from orchestrator.a2a.contracts import ApprovalScope, HandoffEnvelope, HandoffStatus
from orchestrator.a2a.coordinator import A2ACoordinator, HandoffError


def envelope(**overrides):
    values = dict(goal="Validate the product idea", sender="mentor", recipient="product",
                  expected_output="Validation plan")
    values.update(overrides)
    return HandoffEnvelope(**values)


def test_envelope_requires_identity_goal_and_supported_version():
    with pytest.raises(ValueError):
        envelope(goal=" ")
    with pytest.raises(ValueError):
        envelope(contract_version="9.9")


def test_handoff_retries_then_succeeds_and_records_audit():
    attempts, events = [], []
    def handler(task):
        attempts.append(task.task_id)
        if len(attempts) == 1:
            raise RuntimeError("transient")
        return {"recommendation": "Interview users"}
    coordinator = A2ACoordinator(handlers={"product": handler}, max_attempts=2, audit_sink=events.append)
    result = coordinator.dispatch(envelope())
    assert result["recommendation"] == "Interview users"
    assert len(attempts) == 2
    assert any(e["event"] == "attempt_failed" for e in events)
    assert events[-1]["event"] == "succeeded"


def test_idempotent_replay_does_not_repeat_handler():
    calls = []
    coordinator = A2ACoordinator(handlers={"product": lambda task: calls.append(1) or {"ok": True}})
    task = envelope()
    assert coordinator.dispatch(task) == {"ok": True}
    assert coordinator.dispatch(task) == {"ok": True}
    assert len(calls) == 1


def test_reused_task_id_with_different_payload_is_rejected():
    coordinator = A2ACoordinator(handlers={"product": lambda task: {"ok": True}})
    task = envelope()
    coordinator.dispatch(task)
    with pytest.raises(HandoffError):
        coordinator.dispatch(envelope(task_id=task.task_id, goal="Different goal"))


def test_proposed_side_effect_requires_scoped_approval():
    coordinator = A2ACoordinator(handlers={"gtm": lambda task: {"published": True}})
    with pytest.raises(HandoffError, match="scoped approval"):
        coordinator.dispatch(envelope(recipient="gtm", proposed_action="publish_campaign"))
    authorized = ApprovalScope(required=True, actions=("publish_campaign",),
                               approved_by="founder", approved_at="2026-10-20T10:00:00+05:30",
                               approval_id="approval-1")
    wrong_scope = ApprovalScope(required=True, actions=("draft_campaign",),
                                approved_by="founder", approved_at="2026-10-20T10:00:00+05:30",
                                approval_id="approval-2")
    with pytest.raises(HandoffError, match="scoped approval"):
        coordinator.dispatch(envelope(recipient="gtm", proposed_action="publish_campaign", approval_scope=wrong_scope))
    task = envelope(recipient="gtm", proposed_action="publish_campaign", approval_scope=authorized)
    assert coordinator.dispatch(task)["published"] is True


def test_conflicting_recommendations_escalate_instead_of_auto_selecting():
    coordinator = A2ACoordinator(handlers={"product": lambda task: {
        "conflicting_recommendations": [{"agent": "gtm"}, {"agent": "security"}]
    }})
    result = coordinator.dispatch(envelope())
    assert result["status"] == HandoffStatus.NEEDS_HUMAN_REVIEW.value
    assert "Resolve conflicting" in result["follow_up"]


def test_unknown_agent_is_rejected_without_dispatch():
    coordinator = A2ACoordinator(handlers={})
    task = envelope(recipient="not-registered")
    with pytest.raises(HandoffError, match="No handler"):
        coordinator.dispatch(task)
    assert task.status is HandoffStatus.REJECTED
