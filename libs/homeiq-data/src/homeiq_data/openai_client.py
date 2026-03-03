"""Standard OpenAI client wrapper for HomeIQ services.

Consolidates 3+ duplicate OpenAI client implementations with
retry logic, circuit breaker fallback, and token tracking.

Usage::

    from homeiq_data import StandardOpenAIClient

    client = StandardOpenAIClient(
        api_key="sk-...",
        model="gpt-5-mini",
    )

    response = await client.chat_completion(
        messages=[{"role": "user", "content": "Hello"}],
        temperature=0.7,
    )
"""

from __future__ import annotations

import logging
import os
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

logger = logging.getLogger(__name__)

# Lazy import to avoid hard dependency when OpenAI is not installed
_openai_module: Any = None


def _get_openai() -> Any:
    """Lazily import the openai module."""
    global _openai_module
    if _openai_module is None:
        try:
            import openai
            _openai_module = openai
        except ImportError as e:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            ) from e
    return _openai_module


class StandardOpenAIClient:
    """Unified OpenAI client with retry, fallback, and token tracking.

    Parameters
    ----------
    api_key:
        OpenAI API key.  Falls back to ``OPENAI_API_KEY`` env var.
    model:
        Model name.  Falls back to ``OPENAI_MODEL`` env var, then
        ``OPENAI_FINE_TUNED_MODEL`` env var, then ``gpt-5-mini``.
    timeout:
        Request timeout in seconds.
    max_retries:
        Maximum retry attempts for rate limit and API errors.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        *,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        openai = _get_openai()

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = (
            model
            or os.getenv("OPENAI_FINE_TUNED_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-5-mini"
        )
        self.timeout = timeout
        self.max_retries = max_retries

        self._client = openai.AsyncOpenAI(
            api_key=self.api_key,
            timeout=timeout,
        )

        # Token tracking
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_requests = 0

        if os.getenv("OPENAI_FINE_TUNED_MODEL"):
            logger.info("Using fine-tuned model: %s", self.model)
        else:
            logger.debug("OpenAI client initialized: model=%s", self.model)

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        response_format: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Send a chat completion request with retry.

        Parameters
        ----------
        messages:
            List of message dicts with ``role`` and ``content``.
        model:
            Override model for this request.
        temperature:
            Sampling temperature.
        max_tokens:
            Maximum tokens in response.
        response_format:
            Optional response format (e.g. ``{"type": "json_object"}``).

        Returns
        -------
        dict
            Response with keys: ``content``, ``model``, ``usage``,
            ``finish_reason``.
        """
        openai = _get_openai()
        use_model = model or self.model

        @retry(
            retry=retry_if_exception_type((openai.RateLimitError, openai.APIError)),
            stop=stop_after_attempt(self.max_retries),
            wait=wait_exponential(multiplier=2, min=2, max=60),
            reraise=True,
        )
        async def _do_request() -> Any:
            # Extract system message as instructions
            instructions = ""
            input_items: list[dict[str, Any]] = []
            for msg in messages:
                if msg.get("role") == "system":
                    instructions = msg.get("content", "")
                else:
                    input_items.append({"type": "message", "role": msg.get("role", "user"), "content": msg.get("content", "")})

            kwargs: dict[str, Any] = {
                "model": use_model,
                "instructions": instructions,
                "input": input_items,
                "temperature": temperature,
                "store": False,
            }
            if max_tokens is not None:
                kwargs["max_output_tokens"] = max_tokens
            if response_format is not None:
                kwargs["text"] = {"format": response_format}

            return await self._client.responses.create(**kwargs)

        try:
            response = await _do_request()
            self.total_requests += 1

            # Track token usage
            if response.usage:
                self.total_prompt_tokens += getattr(response.usage, "input_tokens", 0)
                self.total_completion_tokens += getattr(response.usage, "output_tokens", 0)

            return {
                "content": response.output_text or "",
                "model": response.model,
                "usage": {
                    "prompt_tokens": getattr(response.usage, "input_tokens", 0) if response.usage else 0,
                    "completion_tokens": getattr(response.usage, "output_tokens", 0) if response.usage else 0,
                    "total_tokens": (getattr(response.usage, "input_tokens", 0) + getattr(response.usage, "output_tokens", 0)) if response.usage else 0,
                },
                "finish_reason": getattr(response, "stop_reason", None),
            }
        except Exception:
            logger.warning("OpenAI chat completion failed (model=%s)", use_model)
            raise

    def get_token_stats(self) -> dict[str, int]:
        """Return accumulated token usage statistics."""
        return {
            "total_requests": self.total_requests,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
        }
