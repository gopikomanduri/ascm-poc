import json

from orchestrator.testing_agent.product_scenario import (
    AGENT_STAGES,
    MAX_CHALLENGE_PROMPT_CHARS,
    run_product_scenario,
)


class LargeArtifactClient:
    def __init__(self):
        self.calls = []

    def send(self, agent_id, prompt, session_id):
        self.calls.append((agent_id, prompt, session_id))
        if "ADVERSARIAL CHALLENGE REVIEW" not in prompt:
            return ("requirements assumptions evidence workflow verification " * 1500)
        targets_line = next(
            line for line in prompt.splitlines()
            if line.startswith("REQUIRED_TARGETS_JSON:")
        )
        targets = json.loads(targets_line.split(":", 1)[1].strip())
        return json.dumps({
            "reviewer": agent_id,
            "reviews": [
                {
                    "target_agent": target,
                    "verdict": "CLEAR",
                    "severity": "P3",
                    "evidence": "Inspected supplied artifact excerpt.",
                    "reason": "No unsupported claim was found in the supplied excerpt.",
                }
                for target in targets
            ],
        })


def test_full_scenario_bounds_challenge_prompts_and_completes_pair_coverage(tmp_path):
    client = LargeArtifactClient()
    report = run_product_scenario(
        client,
        {"product_name": "ASCM", "product_summary": "Test large artifact handling"},
        workspace=tmp_path,
        scenario_id="challenge-payload-budget",
        stages=AGENT_STAGES[:13],
        adversarial_review=True,
    )
    challenge_prompts = [
        prompt for _, prompt, _ in client.calls
        if "ADVERSARIAL CHALLENGE REVIEW" in prompt
    ]
    assert len(challenge_prompts) == 13
    assert all(len(prompt) <= MAX_CHALLENGE_PROMPT_CHARS for prompt in challenge_prompts)
    assert report["summary"]["challenge_pairs_requested"] == 13 * 12
    assert report["summary"]["challenge_pairs_completed"] == 13 * 12
    assert report["summary"]["challenge_reviews_schema_valid"] == 13
