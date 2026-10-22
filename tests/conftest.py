"""
Test isolation: unit tests must not depend on a live LLM.

By default real network calls to LLM APIs fail fast, so agents take the deterministic synthetic fallback and the suite
behaves the same with or without a working API key (and runs fast). Tests that exercise a provider mock the HTTP layer
themselves and are unaffected. Set ASCM_LIVE_TESTS=1 to allow real calls.
"""
import os
import urllib.request

import pytest


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    monkeypatch.setenv("ASCM_LLM_RETRIES", "0")  # no real backoff sleeps in tests
    from orchestrator.agents.base import reset_llm_budget
    reset_llm_budget()
    monkeypatch.setenv("ASCM_NONINTERACTIVE", "1")  # never pop real consent dialogs during tests
    monkeypatch.setenv("ASCM_A2A_ALLOWED_HOSTS", "testserver")
    monkeypatch.setenv("ASCM_DEV_MODE", "1")  # local OTP echo is dev-only; production code never returns it
    if os.environ.get("ASCM_LIVE_TESTS") == "1":
        return
    # Tests exercise the deterministic synthetic fallback, which production code only uses when opted in.
    monkeypatch.setenv("ALLOW_SYNTHETIC_FALLBACK", "1")

    def offline(*args, **kwargs):
        raise ConnectionError("network disabled in tests (set ASCM_LIVE_TESTS=1 to allow real LLM calls)")

    monkeypatch.setattr(urllib.request, "urlopen", offline)           # OpenAI-compatible, Anthropic, Ollama providers
    from google.genai import models as genai_models                    # Gemini provider
    for name in ("generate_content", "generate_content_stream"):
        if hasattr(genai_models.Models, name):
            monkeypatch.setattr(genai_models.Models, name, offline)
