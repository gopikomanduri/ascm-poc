import unittest

from orchestrator.agents.base import _validate_http_endpoint


class LLMEndpointValidationTests(unittest.TestCase):
    def test_accepts_https_provider_endpoint(self):
        self.assertEqual(
            _validate_http_endpoint("https://api.example.com/v1"),
            "https://api.example.com/v1",
        )

    def test_accepts_local_http_model_endpoint(self):
        self.assertEqual(
            _validate_http_endpoint("http://localhost:11434"),
            "http://localhost:11434",
        )
        self.assertEqual(
            _validate_http_endpoint("http://192.168.1.22:8000/v1"),
            "http://192.168.1.22:8000/v1",
        )

    def test_rejects_non_https_public_endpoint(self):
        with self.assertRaises(ValueError):
            _validate_http_endpoint("http://api.example.com/v1")

    def test_rejects_non_http_schemes_and_embedded_credentials(self):
        with self.assertRaises(ValueError):
            _validate_http_endpoint("file:///etc/passwd")
        with self.assertRaises(ValueError):
            _validate_http_endpoint("https://user:secret@example.com/v1")


if __name__ == "__main__":
    unittest.main()
