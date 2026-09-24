import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from orchestrator.agents.base import get_configured_provider, OpenAICompatibleProvider, GeminiProvider
from orchestrator.git_service import GitService
from orchestrator.engine.verifier import VerifierEngine, VerificationResult


class ModelCascadingAndTieringTests(unittest.TestCase):
    def test_tiered_model_selection_openai(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test", "LLM_PROVIDER": "openai"}):
            fast_p = get_configured_provider(tier="fast")
            self.assertEqual(fast_p.model, "gpt-4o-mini")

            primary_p = get_configured_provider(tier="primary")
            self.assertEqual(primary_p.model, "gpt-4o")

    def test_tiered_model_selection_fast_model_env_override(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "LLM_PROVIDER": "openai",
            "FAST_MODEL": "gpt-4o-mini-2024-07-18"
        }):
            p = get_configured_provider(tier="fast")
            self.assertEqual(p.model, "gpt-4o-mini-2024-07-18")

    def test_agent_specific_model_override(self):
        with patch.dict(os.environ, {
            "OPENAI_API_KEY": "sk-test",
            "LLM_PROVIDER": "openai",
            "PRODUCT_AGENT_MODEL": "gpt-4o-mini-special"
        }):
            p = get_configured_provider(agent_name="ProductAgent")
            self.assertEqual(p.model, "gpt-4o-mini-special")


class GitServicePRAutomationTests(unittest.TestCase):
    def test_pr_description_generation(self):
        desc = GitService.generate_pr_description(
            goal="Add high-throughput Kafka producer",
            files=["internal/kafka/producer.go", "internal/kafka/producer_test.go"],
            role="provider",
            linked_repos=[{"name": "consumer-service", "branch": "ascm/add-kafka-consumer", "role": "consumer"}],
            prd_summary="Provide robust Kafka event publishing with exponential retries.",
        )
        self.assertIn("# Feature: Add high-throughput Kafka producer", desc)
        self.assertIn("`PROVIDER`", desc)
        self.assertIn("internal/kafka/producer.go", desc)
        self.assertIn("consumer-service", desc)
        self.assertIn("ascm/add-kafka-consumer", desc)
        self.assertIn("Verification & Quality Assurance", desc)

    def test_write_pr_artifact(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_content = "# Sample PR Content"
            path = GitService.write_pr_artifact(tmp_dir, sample_content, "PULL_REQUEST.md")
            self.assertTrue(Path(path).exists())
            self.assertEqual(Path(path).read_text(encoding="utf-8"), sample_content)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_create_github_pr_success(self, mock_run, mock_which):
        mock_which.return_value = "/usr/local/bin/gh"
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "https://github.com/org/repo/pull/42\n"
        mock_run.return_value = mock_res

        url = GitService.create_github_pr("/tmp/repo", "ascm/branch", "feat: test", "body")
        self.assertEqual(url, "https://github.com/org/repo/pull/42")
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        self.assertIn("gh", cmd)
        self.assertIn("create", cmd)

    @patch("shutil.which")
    def test_create_github_pr_unavailable_gh(self, mock_which):
        mock_which.return_value = None
        url = GitService.create_github_pr("/tmp/repo", "ascm/branch", "feat: test", "body")
        self.assertIsNone(url)


class VerifierSandboxingTests(unittest.TestCase):
    @patch.dict(os.environ, {"USE_DOCKER_SANDBOX": "true"})
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_sandboxed_execution_wraps_in_docker(self, mock_run, mock_which):
        mock_which.return_value = "/usr/local/bin/docker"
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = "ok"
        mock_res.stderr = ""
        mock_run.return_value = mock_res

        with tempfile.TemporaryDirectory() as tmp_dir:
            res, is_sandboxed = VerifierEngine._execute(["go", "test", "./..."], tmp_dir, "golang:1.22-alpine")
            self.assertTrue(is_sandboxed)
            self.assertTrue(mock_run.called)
            cmd = mock_run.call_args[0][0]
            self.assertEqual(cmd[0], "docker")
            self.assertEqual(cmd[1], "run")
            self.assertIn("--network", cmd)
            self.assertIn("none", cmd)
            self.assertIn("golang:1.22-alpine", cmd)


if __name__ == "__main__":
    unittest.main()
