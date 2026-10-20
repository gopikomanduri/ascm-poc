import json
from unittest.mock import Mock

from orchestrator.testing_agent.runtime import ContinuousFounderTestingRuntime


def test_similar_unresolved_mentor_action_is_not_proposed_twice(tmp_path):
    runtime = ContinuousFounderTestingRuntime.__new__(ContinuousFounderTestingRuntime)
    runtime.history = tmp_path / ".ascm_history"
    runtime.session_id = "session-dedup-test"
    runtime.journey_events = []
    runtime.findings = []
    runtime.story_log = Mock()

    first = json.dumps({
        "pre_build_validation_plan": [
            "Interview 5-10 target users to observe and manually trace a cross-repository multi-role handoff."
        ]
    })
    second = json.dumps({
        "pre_build_validation_plan": [
            "Interview 5–10 target users to observe and manually trace a cross-repository, multi-role handoff."
        ]
    })
    runtime._record_mentor_action("problem and value proposition", first, "mentor-review:1")
    runtime._record_mentor_action("problem and value proposition", second, "mentor-review:2")

    proposals = [
        json.loads(line)
        for line in (runtime.history / "founder_actions.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert len(proposals) == 1
    assert proposals[0]["status"] == "proposed"
    assert proposals[0]["approved"] is False
    assert any(event.event_type == "mentor_action_deduplicated" for event in runtime.journey_events)
    assert any(call.args[2] == "action_deduplicated" for call in runtime.story_log.record.call_args_list)
