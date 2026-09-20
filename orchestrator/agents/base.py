from google import genai
from google.genai import types

class BaseAgent:
    def __init__(self, system_instruction: str):
        self.client = genai.Client()
        self.system_instruction = system_instruction
        # The designated lightweight, high-capacity model
        self.model_name = "gemini-3.5-flash-lite"

    def call(self, prompt: str, json_mode: bool = False) -> str:
        config = types.GenerateContentConfig(
            system_instruction=self.system_instruction,
            temperature=0.1,
            response_mime_type="application/json" if json_mode else "text/plain"
        )
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=config
        )
        return response.text.strip()
