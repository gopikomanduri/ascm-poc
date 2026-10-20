import json

from orchestrator.testing_agent.product_scenario import (
    _parse_challenge_review,
    run_product_scenario,
)


class ChallengeClient:
    def __init__(self, verdict="CLEAR"):
        self.calls = []
        self.verdict = verdict

    def send(self, agent_id, prompt, session_id):
        self.calls.append((agent_id, prompt, session_id))
        if "ADVERSARIAL CHALLENGE REVIEW" in prompt:
            targets_line = next(line for line in prompt.splitlines() if line.startswith("REQUIRED_TARGETS_JSON:"))
            targets = json.loads(targets_line.split(":", 1)[1].strip())
            return json.dumps({
                "reviewer": agent_id,
                "reviews": [
                    {
                        "target_agent": target,
                        "verdict": self.verdict if target == "product" else "CLEAR",
                        "severity": "P1" if target == "product" and self.verdict != "CLEAR" else "P3",
                        "evidence": "Artifact excerpt was inspected.",
                        "reason": "Test fixture has an injected concern." if target == "product" and self.verdict != "CLEAR"
                                 else "No fixture contradiction was found.",
                    }
                    for target in targets
                ],
            })
        return (
            "Requirements acceptance criteria open questions assumptions dependencies workflow risks evidence. "
            "Founder goal next action measurable architecture components trade-off risk milestone verification rollback. "
            "Threat permission approval mitigation policy control test pass fail experiment customer hypothesis metric. "
            "Discovery qualification positioning audience pricing unvalidated review change."
        )


def test_adversarial_review_requires_exact_target_coverage_and_evidence():
    result = _parse_challenge_review(
        "qa",
        json.dumps({
            "reviewer": "qa",
            "reviews": [{
                "target_agent": "product", "verdict": "CLEAR", "severity": "P3",
                "evidence": "artifact excerpt", "reason": "No contradiction in the supplied excerpt.",
            }],
        }),
        ["product", "mentor"],
    )
    assert result["status"] == "review_required"
    assert result["schema_valid"] is False
    assert any("omitted target agents" in item for item in result["findings"])


def test_full_configured_stage_set_is_challenged_by_every_other_agent(tmp_path):
    client = ChallengeClient()
    stages = (
        ("product", "Product definition", ("requirements", "acceptance criteria", "open questions", "assumptions")),
        ("mentor", "Founder mentorship", ("founder goal", "next action", "assumption", "measurable")),
        ("qa", "Independent QA", ("test", "pass", "fail", "evidence")),
    )
    report = run_product_scenario(
        client, {"product_name": "ASCM", "product_summary": "Test scenario"},
        workspace=tmp_path, scenario_id="challenge-matrix-test", stages=stages,
        adversarial_review=True,
    )
    challenge_calls = [call for call in client.calls if "ADVERSARIAL CHALLENGE REVIEW" in call[1]]
    assert [call[0] for call in challenge_calls] == ["product", "mentor", "qa"]
    assert report["summary"]["challenge_reviews_requested"] == 3
    assert report["summary"]["challenge_handoffs_recorded"] == 3
    assert all(result["status"] == "passed" for result in report["challenge_results"])
    for reviewer_id, prompt, _ in challenge_calls:
        targets_line = next(line for line in prompt.splitlines() if line.startswith("REQUIRED_TARGETS_JSON:"))
        targets = json.loads(targets_line.split(":", 1)[1].strip())
        assert reviewer_id not in targets
        assert len(targets) == 2


def test_adversarial_concern_blocks_scenario_pass(tmp_path):
    client = ChallengeClient(verdict="CONCERN")
    stages = (
        ("product", "Product definition", ("requirements", "acceptance criteria", "open questions", "assumptions")),
        ("mentor", "Founder mentorship", ("founder goal", "next action", "assumption", "measurable")),
    )
    report = run_product_scenario(
        client, {"product_name": "ASCM", "product_summary": "Test scenario"},
        workspace=tmp_path, scenario_id="challenge-concern-test", stages=stages,
        adversarial_review=True,
    )
    assert report["passed"] is False
    assert report["summary"]["challenge_findings"] == 1
    assert report["summary"]["challenge_reviews_needing_review"] == 1
