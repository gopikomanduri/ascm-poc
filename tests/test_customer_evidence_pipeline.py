from __future__ import annotations

import json

import pytest

from orchestrator.gtm.strategy.customer_evidence_pipeline import CustomerEvidencePipeline
from orchestrator.gtm.strategy.outcome_ledger import OutcomeLedger


def test_customer_evidence_is_redacted_and_never_auto_verified(tmp_path):
    pipeline = CustomerEvidencePipeline(tmp_path)
    fake_token = "ghp_" + ("a" * 24)  # Construct at runtime to avoid a scanner false positive.
    event = pipeline.record(
        feature_key="invoice feature owner@example.com",
        problem_area="billing +1 (415) 555-0198",
        source=f"interview token {fake_token}",
        demand_signal="strong",
        willingness_to_pay="confirmed",
        sentiment="interested",
        evidence_note="Customer wants invoice automation; contact user@example.com",
        experiment_id="experiment-1",
    )

    assert event["classification"] == "unverified_signal"
    assert event["verification_status"] == "requires_human_review"
    assert "owner@example.com" not in json.dumps(event)
    assert "user@example.com" not in json.dumps(event)
    assert "415" not in json.dumps(event)
    assert fake_token not in json.dumps(event)

    ledger_events = OutcomeLedger(tmp_path).recent_events()
    assert len(ledger_events) == 1
    stored = json.dumps(ledger_events[0])
    assert "Customer wants invoice automation" not in stored
    assert "user@example.com" not in stored
    assert ledger_events[0]["event_type"] == "feature_request"
    assert ledger_events[0]["metrics"]["demand_signal"] == "strong"


def test_customer_evidence_rejects_uncontrolled_labels(tmp_path):
    pipeline = CustomerEvidencePipeline(tmp_path)
    with pytest.raises(ValueError, match="demand_signal"):
        pipeline.record(
            feature_key="invoice automation",
            problem_area="billing",
            source="interview",
            demand_signal="verified",
            evidence_note="A short note",
            mirror_to_outcome_ledger=False,
        )


def test_customer_evidence_does_not_silently_hide_mirror_failure(tmp_path, monkeypatch):
    pipeline = CustomerEvidencePipeline(tmp_path)

    def fail(*args, **kwargs):
        raise OSError("ledger unavailable")

    monkeypatch.setattr(OutcomeLedger, "record", fail)
    with pytest.raises(OSError, match="ledger unavailable"):
        pipeline.record(
            feature_key="invoice automation",
            problem_area="billing",
            source="interview",
            evidence_note="Customer requested export",
        )

    # Local capture remains available, but the mirroring failure is visible to the caller.
    assert len(pipeline.list_recent()) == 1


def test_customer_evidence_list_limit_must_be_positive_integer(tmp_path):
    pipeline = CustomerEvidencePipeline(tmp_path)
    with pytest.raises(ValueError, match="positive integer"):
        pipeline.list_recent(0)
    with pytest.raises(ValueError, match="positive integer"):
        pipeline.list_recent(True)
