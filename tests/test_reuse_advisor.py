import json
import unittest
from unittest import mock

from orchestrator.mentor.reuse_advisor import GitHubRepositoryAdvisor


class GitHubRepositoryAdvisorTests(unittest.TestCase):
    def test_normalizes_search_results_and_surfaces_license_caveat(self):
        payload = {
            "items": [{
                "full_name": "example/auth-lib",
                "html_url": "https://github.com/example/auth-lib",
                "description": "Authentication library",
                "stargazers_count": 1200,
                "score": 18.7,
                "forks_count": 120,
                "open_issues_count": 4,
                "language": "Python",
                "pushed_at": "2026-10-01T00:00:00Z",
                "archived": False,
                "license": {"spdx_id": "MIT", "name": "MIT License"},
                "default_branch": "main",
            }]
        }
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        with mock.patch("orchestrator.mentor.reuse_advisor.urlopen", return_value=response):
            result = GitHubRepositoryAdvisor(token="test-token").search("authentication library")
        self.assertEqual(result["repositories"][0]["name"], "example/auth-lib")
        self.assertEqual(result["repositories"][0]["license"], "MIT")
        self.assertEqual(result["repositories"][0]["search_score"], 18.7)
        self.assertEqual(result["repositories"][0]["language"], "Python")
        self.assertIn("not a quality or security endorsement", result["caveat"])

    def test_search_failure_is_a_non_fatal_empty_result(self):
        with mock.patch("orchestrator.mentor.reuse_advisor.urlopen", side_effect=TimeoutError()):
            result = GitHubRepositoryAdvisor().search("authentication library")
        self.assertEqual(result["repositories"], [])
        self.assertIn("unavailable", result["error"].lower())

    def test_validates_task_and_limit(self):
        advisor = GitHubRepositoryAdvisor()
        with self.assertRaises(ValueError):
            advisor.search(" ")
        with self.assertRaises(ValueError):
            advisor.search("auth", limit=11)


if __name__ == "__main__":
    unittest.main()
