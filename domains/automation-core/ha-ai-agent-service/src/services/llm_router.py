"""LLM Router — routes calls to configured provider with fallback.

Epic 97: Prompt Caching & Claude Provider
Story 97.3: Provider Selection & Fallback
Story 97.6: Extended thinking for complex automations
"""

from __future__ import annotations

import logging
import re
from typing import Any

from homeiq_resilience import CircuitBreaker

from ..config import Settings
from ..models.llm_models import LLMResponse

logger = logging.getLogger(__name__)

# Complexity indicators for extended thinking (Story 97.6)
_COMPLEX_KEYWORDS = frozenset([
    "if then else", "between", "unless", "except when",
    "multiple", "sequence", "chain", "schedule",
    "for each", "every room", "all lights",
])


class LLMRouter:
    """Routes LLM calls to configured provider with automatic fallback."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.primary_provider = settings.llm_provider
        self.fallback_provider = settings.llm_fallback_provider

        self._primary = self._create_client(self.primary_provider, settings)
        self._fallback = (
            self._create_client(self.fallback_provider, settings)
            if self.fallback_provider and self.fallback_provider != self.primary_provider
            else None
        )

        self._circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            half_open_max_calls=1,
            name="llm_router",
        )

        logger.info(
            "LLM Router initialized: primary=%s, fallback=%s",
            self.primary_provider,
            self.fallback_provider or "none",
        )

    @staticmethod
    def _create_client(provider: str | None, settings: Settings) -> Any | None:
        """Create an LLM client for the given provider."""
        if not provider:
            return None

        if provider == "anthropic":
            from ..clients.anthropic_client import AnthropicLLMClient

            api_key = (
                settings.anthropic_api_key.get_secret_value()
                if settings.anthropic_api_key
                else ""
            )
            if not api_key:
                logger.warning("Anthropic API key not configured")
                return None
            return AnthropicLLMClient(
                api_key=api_key,
                model=settings.anthropic_model,
            )

        if provider == "openai":
            # OpenAI client is handled separately via existing OpenAIClient
            # Return a sentinel; the router delegates to the existing flow
            return "openai"

        logger.warning("Unknown LLM provider: %s", provider)
        return None

    async def chat_completion(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        enable_caching: bool = True,
        entity_context: str | None = None,
        user_message: str | None = None,
    ) -> LLMResponse:
        """Route chat completion to the configured provider.

        Args:
            system_prompt: System prompt text.
            messages: Conversation messages in OpenAI format.
            tools: Tool schemas in OpenAI format.
            max_tokens: Max response tokens.
            temperature: Sampling temperature.
            enable_caching: Enable prompt caching (Anthropic only).
            entity_context: Entity inventory for separate caching.
            user_message: Raw user message for complexity detection.

        Returns:
            Provider-agnostic LLMResponse.

        Raises:
            RuntimeError: If both primary and fallback fail.
        """
        try:
            if not await self._circuit_breaker.allow_request():
                raise RuntimeError("Circuit breaker open for primary LLM provider")
            result = await self._call_provider(
                provider_name=self.primary_provider,
                client=self._primary,
                system_prompt=system_prompt,
                messages=messages,
                tools=tools,
                max_tokens=max_tokens,
                temperature=temperature,
                enable_caching=enable_caching,
                entity_context=entity_context,
                user_message=user_message,
            )
            await self._circuit_breaker.record_success()
            return result
        except Exception as primary_err:
            await self._circuit_breaker.record_failure()
            if self._fallback:
                logger.warning(
                    "Primary LLM provider (%s) failed: %s — using fallback (%s)",
                    self.primary_provider,
                    primary_err,
                    self.fallback_provider,
                )
                return await self._call_provider(
                    provider_name=self.fallback_provider,
                    client=self._fallback,
                    system_prompt=system_prompt,
                    messages=messages,
                    tools=tools,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    enable_caching=enable_caching,
                    entity_context=entity_context,
                    user_message=user_message,
                )
            raise RuntimeError(
                f"LLM call failed (primary={self.primary_provider}, no fallback): {primary_err}"
            ) from primary_err

    async def _call_provider(
        self,
        provider_name: str | None,
        client: Any,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        enable_caching: bool = True,
        entity_context: str | None = None,
        user_message: str | None = None,
    ) -> LLMResponse:
        """Dispatch to a specific provider client."""
        if provider_name == "openai" or client == "openai":
            raise NotImplementedError(
                "OpenAI calls should go through the existing OpenAIClient path. "
                "LLMRouter handles Anthropic routing; OpenAI is the legacy default."
            )

        if not client or client == "openai":
            raise RuntimeError(f"No client available for provider: {provider_name}")

        # Determine if extended thinking should be enabled (Story 97.6)
        thinking = None
        if (
            provider_name == "anthropic"
            and user_message
            and self._is_complex_automation(user_message)
        ):
            thinking = {"type": "enabled", "budget_tokens": 4096}
            logger.info("Extended thinking enabled for complex automation request")

        return await client.chat_completion(
            system_prompt=system_prompt,
            messages=messages,
            tools=tools,
            max_tokens=max_tokens,
            temperature=temperature,
            enable_caching=enable_caching,
            entity_context=entity_context,
            thinking=thinking,
        )

    @staticmethod
    def _is_complex_automation(user_message: str) -> bool:
        """Detect if automation request is complex enough for extended thinking.

        Story 97.6: Complexity detection heuristic.
        """
        msg_lower = user_message.lower()
        indicators = [
            len(user_message) > 200,
            user_message.count(" and ") > 2,
            sum(1 for kw in _COMPLEX_KEYWORDS if kw in msg_lower) >= 1,
            len(re.findall(r"\b(if|when|while|then|else|unless)\b", msg_lower)) >= 3,
        ]
        return sum(indicators) >= 2

    def get_provider_status(self) -> dict[str, Any]:
        """Get status of primary and fallback providers for health endpoint."""
        status: dict[str, Any] = {
            "primary": {
                "provider": self.primary_provider,
                "available": self._primary is not None,
                "circuit_breaker": self._circuit_breaker.state if hasattr(self._circuit_breaker, "state") else "unknown",
            },
        }
        if self.fallback_provider:
            status["fallback"] = {
                "provider": self.fallback_provider,
                "available": self._fallback is not None,
            }
        return status
