import os
from typing import List, Dict, Any

import requests
from dotenv import load_dotenv


class OpenRouterLLMClient:
    def __init__(self):
        load_dotenv()

        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.base_url = os.getenv(
            "OPENROUTER_BASE_URL",
            "https://openrouter.ai/api/v1",
        )
        self.model = os.getenv("OPENROUTER_MODEL", "openrouter/free")

        if not self.api_key:
            raise ValueError("Missing OPENROUTER_API_KEY in .env")

    def generate(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 1000,
        temperature: float = 0.1,
    ) -> str:
        url = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",
            "X-Title": "chatbot-rag-local-demo",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=90,
        )

        data = response.json()

        if response.status_code != 200:
            raise RuntimeError(f"OpenRouter API error: {data}")

        return data["choices"][0]["message"]["content"].strip()