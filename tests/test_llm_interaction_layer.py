import json
import os
import unittest
from unittest.mock import patch

from orchestrator.agents.base import BaseAgent, OllamaProvider
from orchestrator.llm.interaction import LLMInteractionLayer, provider_for_agent, resolve_route


class LLMInteractionRoutingTests(unittest.TestCase):
    def test_infers_task_categories_for_common_agent_types(self):
        self.assertEqual(LLMInteractionLayer.infer_task("ProductAgent"), "product_discovery")
        self.assertEqual(LLMInteractionLayer.infer_task("CodeReviewAgent"), "code_review")
        self.assertEqual(LLMInteractionLayer.infer_task("ArchitectureReviewAgent"), "deep_reasoning")
        self.assertEqual(LLMInteractionLayer.infer_task("MentorAgent"), "mentoring")

    def test_routes_different_agents_to_different_models(self):
        routes = {
            "default": {"provider": "ollama", "model": "qwen2.5:1.5b"},
            "product_discovery": {"provider": "ollama", "model": "qwen2.5:3b"},
            "deep_reasoning": {"provider": "ollama", "model": "deepseek-r1:8b"},
            "ArchitectureReviewAgent": {"provider": "gemini", "model": "gemini-3.5-pro"},
        }
        layer = LLMInteractionLayer(routes=routes)
        product = layer.resolve("ProductAgent")
        architecture = layer.resolve("ArchitectureReviewAgent")
        mentor = layer.resolve("MentorAgent")

        self.assertEqual((product.provider, product.model, product.task), ("ollama", "qwen2.5:3b", "product_discovery"))
        self.assertEqual((architecture.provider, architecture.model), ("gemini", "gemini-3.5-pro"))
        self.assertEqual((mentor.provider, mentor.model), ("ollama", "qwen2.5:1.5b"))

    def test_environment_json_route_selects_local_model_without_api_key(self):
        env = {
            "ASCM_LLM_ROUTES_JSON": json.dumps({
                "ProductAgent": {"provider": "ollama", "model": "qwen2.5:1.5b"},
                "ArchitectureReviewAgent": {"provider": "ollama", "model": "deepseek-r1:8b"},
            }),
            "LLM_PROVIDER": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "OLLAMA_HOST": "http://localhost:11434",
            "OLLAMA_MODEL": "",
        }
        with patch.dict(os.environ, env, clear=True):
            provider = provider_for_agent("ProductAgent")
            self.assertIsInstance(provider, OllamaProvider)
            self.assertEqual(provider.model, "qwen2.5:1.5b")
            self.assertEqual(resolve_route("ArchitectureReviewAgent")["model"], "deepseek-r1:8b")

    def test_agent_specific_route_overrides_task_and_default(self):
        layer = LLMInteractionLayer(routes={
            "default": {"provider": "ollama", "model": "qwen2.5:1.5b"},
            "product_discovery": {"provider": "ollama", "model": "qwen2.5:3b"},
            "ProductAgent": {"provider": "gemini", "model": "gemini-custom"},
        })
        route = layer.resolve("ProductAgent")
        self.assertEqual((route.provider, route.model), ("gemini", "gemini-custom"))

    def test_rejects_invalid_route_json_and_unknown_fields(self):
        with patch.dict(os.environ, {"ASCM_LLM_ROUTES_JSON": "{bad"}, clear=False):
            with self.assertRaises(ValueError):
                LLMInteractionLayer()
        with self.assertRaises(ValueError):
            LLMInteractionLayer(routes={"default": {"provider": "ollama", "secret": "no"}})

    def test_base_agent_uses_interaction_layer_route(self):
        env = {
            "ASCM_LLM_ROUTES_JSON": json.dumps({
                "BaseAgent": {"provider": "ollama", "model": "qwen2.5:1.5b"}
            }),
            "LLM_PROVIDER": "",
            "GEMINI_API_KEY": "",
            "GOOGLE_API_KEY": "",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "OLLAMA_HOST": "http://localhost:11434",
            "OLLAMA_MODEL": "",
        }
        with patch.dict(os.environ, env, clear=True):
            agent = BaseAgent()
            self.assertIsInstance(agent.provider, OllamaProvider)
            self.assertEqual(agent.model_name, "qwen2.5:1.5b")

    def test_describe_route_does_not_claim_implicit_fallback(self):
        layer = LLMInteractionLayer(routes={
            "ProductAgent": {"provider": "ollama", "model": "qwen2.5:1.5b"}
        })
        self.assertEqual(layer.describe_route("ProductAgent")["provider"], "ollama")


if __name__ == "__main__":
    unittest.main()
