import unittest
from unittest import mock

from orchestrator.mentor.notifier import CrossPlatformNotifier


class BackgroundPromptTests(unittest.TestCase):
    def test_background_prompt_does_not_fall_back_to_blocking_terminal_input(self):
        with mock.patch("orchestrator.mentor.notifier.sys.platform", "linux"), \
             mock.patch("orchestrator.mentor.notifier.shutil.which", return_value=None), \
             mock.patch("builtins.input") as terminal_input:
            result = CrossPlatformNotifier.prompt_dialog(
                "What are you working on?",
                allow_terminal_fallback=False,
            )
        self.assertIsNone(result)
        terminal_input.assert_not_called()


if __name__ == "__main__":
    unittest.main()
