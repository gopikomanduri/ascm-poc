"""Consent-aware LLM routing: cloud only with permission, else local Ollama, else stop."""

import json
import logging
import os
import urllib.request
from typing import Callable, Optional

import orchestrator.agents.base  # noqa: F401  (side effect: loads API keys from .env)
from orchestrator.mentor.assistant.consent import ConsentGate
from orchestrator.mentor.notifier import CrossPlatformNotifier

logger = logging.getLogger("ASCMAssistantLLM")


def _cloud_key_present() -> bool:
    return bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"))


def _gemini_call(prompt: str) -> str:
    from google import genai
    model = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL") or "gemini-3.5-flash-lite"
    client = genai.Client()  # keep a reference: a temporary client is closed by GC mid-request
    return client.models.generate_content(model=model, contents=prompt).text


def _ollama_host() -> str:
    return os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")


def _ollama_model() -> Optional[str]:
    """Return a model name if an Ollama server is reachable, else None."""
    try:
        with urllib.request.urlopen(_ollama_host() + "/api/tags", timeout=1.5) as r:
            models = [m["name"] for m in json.load(r).get("models", [])]
    except Exception:
        return None
    preferred = os.environ.get("OLLAMA_MODEL")
    if preferred:
        return preferred
    return models[0] if models else None


def _ollama_call(prompt: str, model: str) -> str:
    req = urllib.request.Request(
        _ollama_host() + "/api/generate",
        data=json.dumps({"model": model, "prompt": prompt, "stream": False}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["response"]


class AssistantLLM:
    """
    ask() policy:
      1. Ask permission to send data to the cloud model (Gemini).
      2. Yes  -> cloud call.
      3. No   -> local model (Ollama) if one is running.
      4. No local model -> tell the user nothing was sent, and stop (returns None).
    """

    def __init__(
        self,
        gate: ConsentGate,
        notify: Optional[Callable[[str, str], object]] = None,
        cloud_call: Callable[[str], str] = _gemini_call,
        cloud_available: Callable[[], bool] = _cloud_key_present,
        local_model: Callable[[], Optional[str]] = _ollama_model,
        local_call: Callable[[str, str], str] = _ollama_call,
    ):
        self.gate = gate
        self.notify = notify or (lambda t, m: CrossPlatformNotifier.notify(t, m, app_name="ASCM Assistant"))
        self._cloud_call, self._cloud_available = cloud_call, cloud_available
        self._local_model, self._local_call = local_model, local_call

    def ask(self, prompt: str, purpose: str, data_desc: str) -> Optional[str]:
        cloud_failed = None
        if self._cloud_available() and self.gate.check("Google Gemini (cloud)", purpose, data_desc):
            try:
                return self._cloud_call(prompt)
            except Exception as e:
                cloud_failed = str(e).splitlines()[0][:120]
                logger.warning(f"Cloud call failed ({cloud_failed}); trying local model.")

        model = self._local_model()
        if model:
            try:
                return self._local_call(prompt, model)
            except Exception as e:
                logger.warning(f"Local model call failed: {e}")
                return None

        if cloud_failed:
            self.notify("No model available",
                        f"The cloud request failed ({cloud_failed}) and no local model is running (e.g. `ollama serve`).")
        else:
            self.notify("No model available",
                        "Nothing was sent anywhere. Allow the cloud model or start a local one (e.g. `ollama serve`).")
        return None
