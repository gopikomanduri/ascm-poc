from orchestrator.testing_agent.product_scenario import evaluate_agent_output


ROLE_TERMS = ("discovery", "customer", "qualification", "evidence")


def test_fabricated_sales_operational_metrics_never_pass_heuristic_evaluation():
    output = (
        'Sales discovery summary: {"leads_discovered": 150, "verified_emails": 142, '
        '"first_sequence_dispatched": true}. Customer qualification and evidence are discussed. '
        "This response is detailed and contains role-specific concepts, but no audit record is supplied."
    )
    result = evaluate_agent_output("sales", output, ROLE_TERMS)
    assert result["status"] == "review_required"
    assert result["unsupported_outcome_claims"]
    assert any("operational or commercial result" in item for item in result["unsupported_outcome_claims"])


def test_roi_numbers_without_assumption_label_are_review_required():
    output = (
        "Revenue ROI pricing and metrics: expected savings are $1885 and "
        "14.5 hours saved per sprint. Evidence and next steps are included."
    )
    result = evaluate_agent_output("revenue_roi", output, ("pricing", "assumption", "metric", "unvalidated"))
    assert result["status"] == "review_required"
    assert result["unsupported_outcome_claims"]


def test_explicitly_hypothetical_commercial_example_is_not_mislabeled_as_observed_outcome():
    output = (
        "Pricing and ROI hypothesis: an illustrative, hypothetical example uses $1885 as an "
        "assumption only, not an observed result. The metric is unvalidated and requires evidence."
    )
    result = evaluate_agent_output("revenue_roi", output, ("pricing", "assumption", "metric", "unvalidated"))
    assert result["status"] == "passed"
    assert result["unsupported_outcome_claims"] == []


def test_agent_supplied_evidence_id_does_not_itself_verify_a_claim():
    output = (
        'Sales discovery: {"leads_discovered": 150}. Customer qualification and evidence are detailed. '
        "evidence_ref: sales-record-150 is claimed, but the evaluator cannot resolve that record."
    )
    result = evaluate_agent_output("sales", output, ROLE_TERMS)
    assert result["status"] == "review_required"
    assert result["unsupported_outcome_claims"]
