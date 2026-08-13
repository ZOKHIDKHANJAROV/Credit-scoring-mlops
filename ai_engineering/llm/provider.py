"""LLM provider abstraction for OpenAI-compatible APIs such as vLLM."""

from __future__ import annotations

import os
from typing import Any


class LLMProvider:
    """Minimal provider contract used by the orchestrator."""

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        raise NotImplementedError


class OpenAICompatibleProvider(LLMProvider):
    """Provider for OpenAI-compatible chat APIs, including local vLLM."""

    def __init__(self, base_url: str | None = None, api_key: str | None = None, model: str | None = None) -> None:
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:8000/v1")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "local")
        self.model = model or os.getenv("LLM_MODEL", "Qwen/Qwen3-8B")

    def generate(self, system_prompt: str, user_prompt: str, **kwargs: Any) -> str:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the 'openai' package to use the LLM provider") from exc

        client = OpenAI(base_url=self.base_url, api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=kwargs.get("temperature", 0.0),
        )
        return response.choices[0].message.content or ""
