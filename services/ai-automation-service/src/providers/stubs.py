"""
Stub Provider Implementations
Placeholder implementations for future provider support.
"""

import logging
from typing import Any

from .base import BaseProvider

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseProvider):
    """Stub implementation for Anthropic Claude."""

    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229"):
        self._api_key = api_key
        self._model = model
        self._provider_id = "anthropic"

    def provider_id(self) -> str:
        return self._provider_id

    def model_id(self) -> str:
        return self._model

    async def generate_json(
        self,
        *,
        schema: dict[str, Any],
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        msg = "Anthropic provider not yet implemented"
        raise NotImplementedError(msg)


class GoogleProvider(BaseProvider):
    """Stub implementation for Google Gemini."""

    def __init__(self, api_key: str, model: str = "gemini-pro"):
        self._api_key = api_key
        self._model = model
        self._provider_id = "google"

    def provider_id(self) -> str:
        return self._provider_id

    def model_id(self) -> str:
        return self._model

    async def generate_json(
        self,
        *,
        schema: dict[str, Any],
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        msg = "Google provider not yet implemented"
        raise NotImplementedError(msg)


class GroqProvider(BaseProvider):
    """Stub implementation for Groq."""

    def __init__(self, api_key: str, model: str = "llama3-70b-8192"):
        self._api_key = api_key
        self._model = model
        self._provider_id = "groq"

    def provider_id(self) -> str:
        return self._provider_id

    def model_id(self) -> str:
        return self._model

    async def generate_json(
        self,
        *,
        schema: dict[str, Any],
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        msg = "Groq provider not yet implemented"
        raise NotImplementedError(msg)


class OllamaProvider(BaseProvider):
    """Stub implementation for Ollama (local LLM)."""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2"):
        self._base_url = base_url
        self._model = model
        self._provider_id = "ollama"

    def provider_id(self) -> str:
        return self._provider_id

    def model_id(self) -> str:
        return self._model

    async def generate_json(
        self,
        *,
        schema: dict[str, Any],
        prompt: str,
        tools: list[dict[str, Any]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict[str, Any]:
        msg = "Ollama provider not yet implemented (requires LOCAL_LLM_ENABLED=true)"
        raise NotImplementedError(msg)

