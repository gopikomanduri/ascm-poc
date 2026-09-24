import json
import os
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List


def _load_dotenv():
    current = Path.cwd()
    env_paths = [
        current / ".env",
        Path(__file__).resolve().parent.parent.parent / ".env",
    ]
    for env_path in env_paths:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if val and key not in os.environ:
                        os.environ[key] = val


class BaseLLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_instruction: str, json_mode: bool = False) -> str:
        pass


class GeminiProvider(BaseLLMProvider):
    def __init__(self, api_key: str, model: Optional[str] = None):
        from google import genai
        from google.genai.errors import ServerError
        self.client = genai.Client(api_key=api_key)
        self.ServerError = ServerError
        preferred = model or os.environ.get("GEMINI_MODEL") or os.environ.get("LLM_MODEL", "gemini-2.5-flash")
        valid_defaults = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
        self.candidate_models = list(dict.fromkeys([preferred] + valid_defaults))

    def generate(self, prompt: str, system_instruction: str, json_mode: bool = False) -> str:
        from google.genai import types
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1,
            response_mime_type="application/json" if json_mode else "text/plain",
        )
        last_exception = None
        for model in self.candidate_models:
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=config,
                    )
                    return response.text.strip()
                except self.ServerError as err:
                    last_exception = err
                    time.sleep(1.0 * (attempt + 1))
                except Exception as err:
                    last_exception = err
                    break
        raise RuntimeError(f"All candidate Gemini models failed. Last error: {last_exception}") from last_exception


class OpenAICompatibleProvider(BaseLLMProvider):
    """
    Supports OpenAI (GPT-4o, GPT-4o-mini), Azure OpenAI, Groq, DeepSeek, Together AI,
    vLLM, and any standard OpenAI-compatible API endpoint with zero external dependencies.
    """
    def __init__(self, api_key: str, base_url: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
        self.model = model or os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL", "gpt-4o-mini")

    def generate(self, prompt: str, system_instruction: str, json_mode: bool = False) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        messages = [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.1,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI-compatible API Error ({err.code}): {err_body}") from err
        except Exception as err:
            raise RuntimeError(f"Failed to communicate with OpenAI-compatible endpoint: {err}") from err


class AnthropicProvider(BaseLLMProvider):
    """
    Supports Anthropic Claude models (Claude 3.5 Sonnet, Claude 3.5 Haiku)
    using native HTTP requests with zero extra dependencies.
    """
    def __init__(self, api_key: str, model: Optional[str] = None):
        self.api_key = api_key
        self.model = model or os.environ.get("ANTHROPIC_MODEL") or os.environ.get("LLM_MODEL", "claude-3-5-sonnet-20241022")

    def generate(self, prompt: str, system_instruction: str, json_mode: bool = False) -> str:
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        sys_prompt = system_instruction
        if json_mode:
            sys_prompt += "\nIMPORTANT: You must respond ONLY with a valid JSON object matching the requested schema. Do not include markdown code block syntax or explanations."

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": sys_prompt,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                content = result.get("content", [])
                if content and "text" in content[0]:
                    return content[0]["text"].strip()
                return ""
        except urllib.error.HTTPError as err:
            err_body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Anthropic API Error ({err.code}): {err_body}") from err
        except Exception as err:
            raise RuntimeError(f"Failed to communicate with Anthropic API: {err}") from err


class OllamaProvider(BaseLLMProvider):
    """
    Supports local open-source models (Qwen 2.5 Coder, DeepSeek Coder, Llama 3)
    running offline via Ollama (100% free, private).
    """
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = (host or os.environ.get("OLLAMA_HOST", "http://localhost:11434")).rstrip("/")
        self.model = model or os.environ.get("OLLAMA_MODEL") or os.environ.get("LLM_MODEL", "qwen2.5-coder:latest")

    def generate(self, prompt: str, system_instruction: str, json_mode: bool = False) -> str:
        url = f"{self.host}/api/chat"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        if json_mode:
            payload["format"] = "json"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["message"]["content"].strip()
        except urllib.error.URLError as err:
            raise RuntimeError(
                f"Could not connect to Ollama at '{self.host}'. Is Ollama running?\n"
                f"Error: {err}"
            ) from err
        except Exception as err:
            raise RuntimeError(f"Ollama generation failed: {err}") from err


def get_configured_provider(
    provider_name: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    tier: str = "primary",
    agent_name: Optional[str] = None,
) -> BaseLLMProvider:
    _load_dotenv()
    name = (provider_name or os.environ.get("LLM_PROVIDER", "")).lower().strip()

    # Agent or Tier model resolution
    resolved_model = model
    if not resolved_model and agent_name:
        # Check specific agent override: e.g. PRODUCT_AGENT_MODEL or PRODUCTAGENT_MODEL
        resolved_model = os.environ.get(f"{agent_name.upper()}_MODEL") or os.environ.get(
            f"{agent_name.upper().replace('AGENT', '_AGENT')}_MODEL"
        )

    if not resolved_model and tier == "fast":
        resolved_model = os.environ.get("FAST_MODEL") or os.environ.get("FAST_LLM_MODEL")

    # 1. Explicit provider selection
    if name == "gemini":
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is required for 'gemini' provider.")
        target_model = resolved_model or (
            "gemini-1.5-flash" if tier == "fast" else os.environ.get("GEMINI_MODEL") or os.environ.get("LLM_MODEL", "gemini-2.5-flash")
        )
        return GeminiProvider(api_key=key, model=target_model)

    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is required for 'openai' provider.")
        target_model = resolved_model or (
            "gpt-4o-mini" if tier == "fast" else os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL", "gpt-4o")
        )
        return OpenAICompatibleProvider(api_key=key, base_url=base_url, model=target_model)

    if name == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is required for 'anthropic' provider.")
        target_model = resolved_model or (
            "claude-3-5-haiku-latest" if tier == "fast" else os.environ.get("ANTHROPIC_MODEL") or os.environ.get("LLM_MODEL", "claude-3-5-sonnet-20241022")
        )
        return AnthropicProvider(api_key=key, model=target_model)

    if name == "ollama":
        target_model = resolved_model or (
            os.environ.get("OLLAMA_FAST_MODEL", "llama3.2:3b") if tier == "fast" else os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:latest")
        )
        return OllamaProvider(host=base_url or os.environ.get("OLLAMA_HOST"), model=target_model)

    # 2. Auto-detection based on present environment keys (BYOK)
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        target_model = resolved_model or (
            "gemini-1.5-flash" if tier == "fast" else os.environ.get("GEMINI_MODEL") or os.environ.get("LLM_MODEL", "gemini-2.5-flash")
        )
        return GeminiProvider(api_key=key, model=target_model)

    if os.environ.get("OPENAI_API_KEY"):
        target_model = resolved_model or (
            "gpt-4o-mini" if tier == "fast" else os.environ.get("OPENAI_MODEL") or os.environ.get("LLM_MODEL", "gpt-4o")
        )
        return OpenAICompatibleProvider(api_key=os.environ["OPENAI_API_KEY"], base_url=base_url, model=target_model)

    if os.environ.get("ANTHROPIC_API_KEY"):
        target_model = resolved_model or (
            "claude-3-5-haiku-latest" if tier == "fast" else os.environ.get("ANTHROPIC_MODEL") or os.environ.get("LLM_MODEL", "claude-3-5-sonnet-20241022")
        )
        return AnthropicProvider(api_key=os.environ["ANTHROPIC_API_KEY"], model=target_model)

    if os.environ.get("OLLAMA_HOST") or os.environ.get("OLLAMA_MODEL"):
        target_model = resolved_model or (
            os.environ.get("OLLAMA_FAST_MODEL", "llama3.2:3b") if tier == "fast" else os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:latest")
        )
        return OllamaProvider(host=base_url, model=target_model)


    # 3. None configured - helpful BYOK prompt
    raise RuntimeError(
        "\n\n[!] No LLM Provider configured.\n"
        "Bring Your Own Key (BYOK) by setting any of the following in your environment or .env:\n"
        "  1. Google Gemini:    export GEMINI_API_KEY='your-key'\n"
        "  2. OpenAI / GPT-4o:  export OPENAI_API_KEY='your-key'\n"
        "  3. Anthropic Claude: export ANTHROPIC_API_KEY='your-key'\n"
        "  4. Local / Ollama:   export LLM_PROVIDER='ollama' (free, runs locally)\n"
        "Or pass via CLI: python main.py --provider [gemini|openai|anthropic|ollama] --repos ...\n"
    )


class BaseAgent:
    def __init__(
        self,
        system_instruction: str,
        provider: Optional[BaseLLMProvider] = None,
        tier: str = "primary",
    ):
        self.system_instruction = system_instruction
        self.tier = tier
        agent_name = self.__class__.__name__
        self.provider = provider or get_configured_provider(tier=self.tier, agent_name=agent_name)

    def call(self, prompt: str, json_mode: bool = False) -> str:
        from orchestrator.security.audit_logger import AUDIT_LOGGER
        from orchestrator.security.pii_scrubber import PIIScrubber

        sanitized_prompt = prompt
        if os.environ.get("SCRUB_OUTBOUND_PII", "").lower() in ("true", "1", "yes"):
            sanitized_prompt = PIIScrubber.scrub(prompt)

        start_time = time.time()
        agent_name = self.__class__.__name__
        try:
            response = self.provider.generate(
                prompt=sanitized_prompt,
                system_instruction=self.system_instruction,
                json_mode=json_mode,
            )
            elapsed_ms = (time.time() - start_time) * 1000
            provider_type = self.provider.__class__.__name__
            model_name = getattr(self.provider, "model", "default")
            AUDIT_LOGGER.log_llm_interaction(
                agent=agent_name,
                provider=provider_type,
                model=model_name,
                prompt=prompt,
                response=response,
                latency_ms=elapsed_ms,
                json_mode=json_mode,
            )
            return response
        except Exception as err:
            elapsed_ms = (time.time() - start_time) * 1000
            AUDIT_LOGGER.log_event(
                event_type="LLM_CALL_FAILURE",
                agent=agent_name,
                action="GENERATE_CONTENT",
                details={"error": str(err), "latency_ms": round(elapsed_ms, 2)},
                level="ERROR",
            )
            raise


