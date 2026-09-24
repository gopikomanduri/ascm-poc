import io
import json
import os
import unittest
import urllib.request
from unittest.mock import MagicMock, patch

from orchestrator.agents.base import (
    BaseAgent,
    GeminiProvider,
    OpenAICompatibleProvider,
    AnthropicProvider,
    OllamaProvider,
    get_configured_provider,
)


class MultiProviderBYOKTests(unittest.TestCase):
    def test_provider_auto_detect_gemini(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-gemini-key", "OPENAI_API_KEY": "", "ANTHROPIC_API_KEY": "", "LLM_PROVIDER": ""}):
            with patch("google.genai.Client") as mock_client:
                provider = get_configured_provider()
                self.assertIsInstance(provider, GeminiProvider)

    def test_provider_explicit_openai(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test-key", "LLM_PROVIDER": "openai"}):
            provider = get_configured_provider()
            self.assertIsInstance(provider, OpenAICompatibleProvider)
            self.assertEqual(provider.model, "gpt-4o-mini")

    def test_provider_explicit_anthropic(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-key", "LLM_PROVIDER": "anthropic"}):
            provider = get_configured_provider()
            self.assertIsInstance(provider, AnthropicProvider)
            self.assertEqual(provider.model, "claude-3-5-sonnet-20241022")

    def test_provider_explicit_ollama(self):
        with patch.dict(os.environ, {"LLM_PROVIDER": "ollama", "OLLAMA_MODEL": "qwen2.5-coder:32b"}):
            provider = get_configured_provider()
            self.assertIsInstance(provider, OllamaProvider)
            self.assertEqual(provider.model, "qwen2.5-coder:32b")

    def test_provider_no_keys_raises_helpful_byok_error(self):
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "LLM_PROVIDER": "",
            "OLLAMA_HOST": "",
            "OLLAMA_MODEL": "",
        }, clear=True):
            with self.assertRaises(RuntimeError) as ctx:
                get_configured_provider()
            self.assertIn("Bring Your Own Key (BYOK)", str(ctx.exception))
            self.assertIn("OpenAI", str(ctx.exception))
            self.assertIn("Anthropic", str(ctx.exception))
            self.assertIn("Ollama", str(ctx.exception))

    @patch("urllib.request.urlopen")
    def test_openai_generate_call(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "choices": [{"message": {"content": '{"status": "ok"}'}}]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        provider = OpenAICompatibleProvider(api_key="sk-test", model="gpt-4o")
        output = provider.generate("test prompt", "system instructions", json_mode=True)

        self.assertEqual(output, '{"status": "ok"}')
        self.assertTrue(mock_urlopen.called)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_header("Authorization"), "Bearer sk-test")
        body = json.loads(req.data.decode("utf-8"))
        self.assertEqual(body["model"], "gpt-4o")
        self.assertEqual(body["response_format"], {"type": "json_object"})

    @patch("urllib.request.urlopen")
    def test_anthropic_generate_call(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "content": [{"text": "Hello from Claude"}]
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        provider = AnthropicProvider(api_key="sk-ant-test", model="claude-3-5-sonnet-20241022")
        output = provider.generate("test prompt", "system instructions")

        self.assertEqual(output, "Hello from Claude")
        self.assertTrue(mock_urlopen.called)
        req = mock_urlopen.call_args[0][0]
        self.assertEqual(req.get_header("X-api-key"), "sk-ant-test")
        self.assertEqual(req.get_header("Anthropic-version"), "2023-06-01")

    @patch("urllib.request.urlopen")
    def test_ollama_generate_call(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "message": {"content": "Hello from local Qwen"}
        }).encode("utf-8")
        mock_response.__enter__.return_value = mock_response
        mock_urlopen.return_value = mock_response

        provider = OllamaProvider(host="http://localhost:11434", model="qwen2.5-coder:14b")
        output = provider.generate("test prompt", "system instructions")

        self.assertEqual(output, "Hello from local Qwen")
        self.assertTrue(mock_urlopen.called)
        req = mock_urlopen.call_args[0][0]
        self.assertIn("11434/api/chat", req.full_url)


if __name__ == "__main__":
    unittest.main()
