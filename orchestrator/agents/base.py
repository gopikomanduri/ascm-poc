import os
import time
from pathlib import Path
from google import genai
from google.genai import types
from google.genai.errors import ServerError, APIError


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
                    if val:
                        os.environ[key] = val


class BaseAgent:
    def __init__(self, system_instruction: str):
        _load_dotenv()
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "\n\n[!] GEMINI_API_KEY is not set.\n"
                "Please set your API key in your .env file:\n"
                "    GEMINI_API_KEY=your-api-key-here\n"
                "or export it in your shell:\n"
                "    export GEMINI_API_KEY='your-api-key-here'\n"
            )
        self.client = genai.Client(api_key=api_key)
        self.system_instruction = system_instruction
        preferred = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        valid_defaults = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-2.5-flash"]
        self.candidate_models = list(dict.fromkeys([preferred] + valid_defaults))

    def call(self, prompt: str, json_mode: bool = False) -> str:
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
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
                except ServerError as err:
                    last_exception = err
                    time.sleep(1.0 * (attempt + 1))
                except Exception as err:
                    last_exception = err
                    break

        raise RuntimeError(f"All candidate Gemini models failed. Last error: {last_exception}") from last_exception



