import tempfile
import unittest
from pathlib import Path
from unittest import mock

from orchestrator.mentor.daemon import UniversalASCMDaemon


class FakeContext:
    def __init__(self, goal=None):
        self.goal = goal
        self.current_task = None

    def load(self):
        return {"current_goal": self.goal}

    def update(self, **kwargs):
        if "current_goal" in kwargs:
            self.goal = kwargs["current_goal"]
        if "current_task" in kwargs:
            self.current_task = kwargs["current_task"]
        return {"current_goal": self.goal, "current_task": self.current_task}


class FakeMentor:
    def __init__(self, goal=None):
        self.founder_context = FakeContext(goal)
        self.clarified = []
        self.recommendations = []

    def clarify_goal_and_pre_validate(self, answer):
        self.clarified.append(answer)
        self.founder_context.update(current_goal=answer)
        return {"clarified_goal": answer, "pre_build_validation_plan": ["Interview three target users"]}

    def recommend_next_action(self, observation, evidence):
        self.recommendations.append((observation, evidence))
        return {"actions": [{"title": "Check reuse first", "rationale": "Avoid rebuilding solved problems."}]}


class ProactiveDaemonPromptTests(unittest.TestCase):
    def _daemon(self, tmp, goal=None):
        daemon = UniversalASCMDaemon.__new__(UniversalASCMDaemon)
        daemon.history_dir = Path(tmp)
        daemon.history_dir.mkdir(parents=True, exist_ok=True)
        daemon.mentor = FakeMentor(goal)
        return daemon

    def test_first_observed_edit_prompts_and_persists_goal_without_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            daemon = self._daemon(tmp)
            activity = {"filesystem_activity": {"recently_edited_files": ["/work/api.py"]}}
            state = {}
            with mock.patch(
                "orchestrator.mentor.daemon.CrossPlatformNotifier.prompt_dialog",
                return_value="Validate demand for invoice automation",
            ) as prompt, mock.patch(
                "orchestrator.mentor.daemon.CrossPlatformNotifier.notify"
            ) as notify:
                daemon._prompt_for_founder_context(activity, state, 100000)
            prompt.assert_called_once()
            self.assertFalse(prompt.call_args.kwargs["allow_terminal_fallback"])
            self.assertEqual(
                daemon.mentor.founder_context.goal,
                "Validate demand for invoice automation",
            )
            self.assertEqual(daemon.mentor.clarified, ["Validate demand for invoice automation"])
            self.assertEqual(state["last_founder_context_prompt_at"], 100000)
            self.assertTrue((Path(tmp) / "daemon_state.json").exists())
            notify.assert_called_once()

    def test_known_goal_captures_task_and_immediately_recommends_next_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            daemon = self._daemon(tmp, goal="Launch a secure customer portal")
            activity = {"filesystem_activity": {"recently_edited_files": ["/work/auth.py"]}}
            with mock.patch(
                "orchestrator.mentor.daemon.CrossPlatformNotifier.prompt_dialog",
                return_value="Implement authentication",
            ), mock.patch("orchestrator.mentor.daemon.CrossPlatformNotifier.notify") as notify:
                daemon._prompt_for_founder_context(activity, {}, 100000)
            self.assertEqual(daemon.mentor.founder_context.current_task, "Implement authentication")
            self.assertEqual(
                daemon.mentor.recommendations,
                [("code_activity", {"task_description": "Implement authentication"})],
            )
            self.assertIn("Check reuse first", notify.call_args.args[0])

    def test_persistent_cooldown_prevents_repeated_interruptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            daemon = self._daemon(tmp)
            activity = {"filesystem_activity": {"recently_edited_files": []}}
            state = {"last_founder_context_prompt_at": 100000}
            with mock.patch(
                "orchestrator.mentor.daemon.CrossPlatformNotifier.prompt_dialog"
            ) as prompt:
                daemon._prompt_for_founder_context(activity, state, 100100)
            prompt.assert_not_called()


if __name__ == "__main__":
    unittest.main()
