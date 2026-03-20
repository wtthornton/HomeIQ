"""Anthropic Claude LLM client with prompt caching support.

Epic 97: Prompt Caching & Claude Provider
Story 97.1: AnthropicLLMClient
Story 97.2: Prompt caching with cache_control breakpoints
Story 97.6: Extended thinking for complex automations
"""

from __future__ import annotations

import logging
from typing import Any

import anthropic

from ..models.llm_models import LLMResponse, TokenUsage, ToolCall
from ..utils.tool_translator import (
    anthropic_tool_use_to_openai,
    openai_messages_to_anthropic,
    openai_tools_to_anthropic,
)

logger = logging.getLogger(__name__)


class AnthropicLLMClient:
    """Claude LLM client with prompt caching support."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

        # Token tracking
        self.total_tokens_used = 0
        self.total_cached_tokens = 0
        self.total_cache_creation_tokens = 0
        self.total_requests = 0
        self.total_errors = 0

    async def chat_completion(
        self,
        system_prompt: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        enable_caching: bool = True,
        entity_context: str | None = None,
        thinking: dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Call Claude API with prompt caching support.

        Accepts OpenAI-format messages and tools, translates internally.

        Args:
            system_prompt: System prompt text (static sections).
            messages: Conversation messages in OpenAI format.
            tools: Tool schemas in OpenAI format (auto-translated).
            max_tokens: Maximum response tokens.
            temperature: Sampling temperature.
            enable_caching: Add cache_control breakpoints to system prompt.
            entity_context: Entity inventory text (cached separately).
            thinking: Extended thinking config, e.g. {"type": "enabled", "budget_tokens": 4096}.

        Returns:
            Provider-agnostic LLMResponse.
        """
        self.total_requests += 1

        # Build system content blocks with cache breakpoints
        system_blocks = self._build_system_blocks(
            system_prompt, entity_context, enable_caching
        )

        # Convert messages from OpenAI format
        anthropic_messages, _ = openai_messages_to_anthropic(
            [{"role": "system", "content": ""}, *messages]
            if messages and messages[0].get("role") != "system"
            else messages
        )
        # Remove any empty messages that may result from the system extraction
        anthropic_messages = [m for m in anthropic_messages if m.get("content")]

        # Translate tools
        anthropic_tools = openai_tools_to_anthropic(tools) if tools else None

        # Build request
        request_params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system_blocks,
            "messages": anthropic_messages,
        }

        if anthropic_tools:
            request_params["tools"] = anthropic_tools

        # Extended thinking (Story 97.6)
        if thinking:
            request_params["thinking"] = thinking
            # Extended thinking requires temperature=1 (Anthropic constraint)
        else:
            request_params["temperature"] = temperature

        try:
            response = await self.client.messages.create(**request_params)
            return self._parse_response(response)
        except anthropic.RateLimitError as e:
            self.total_errors += 1
            logger.warning("Anthropic rate limit exceeded: %s", e)
            raise
        except anthropic.APIError as e:
            self.total_errors += 1
            logger.error("Anthropic API error: %s", e)
            raise

    def _build_system_blocks(
        self,
        system_prompt: str,
        entity_context: str | None,
        enable_caching: bool,
    ) -> list[dict[str, Any]]:
        """Build system content blocks with cache breakpoints.

        Cache breakpoint strategy (Story 97.2):
          BP1: System prompt (sections 0-9, ~3K tokens) — stable across all requests
          BP2: Entity inventory (~5-15K tokens) — stable for ~5 min
          Remaining context (RAG, patterns, sensors) added per-message, not cached here.
        """
        blocks: list[dict[str, Any]] = []

        # Block 1: Static system prompt (cache breakpoint 1)
        system_block: dict[str, Any] = {
            "type": "text",
            "text": system_prompt,
        }
        if enable_caching:
            system_block["cache_control"] = {"type": "ephemeral"}
        blocks.append(system_block)

        # Block 2: Entity context (cache breakpoint 2)
        if entity_context:
            entity_block: dict[str, Any] = {
                "type": "text",
                "text": entity_context,
            }
            if enable_caching:
                entity_block["cache_control"] = {"type": "ephemeral"}
            blocks.append(entity_block)

        return blocks

    def _parse_response(self, response: Any) -> LLMResponse:
        """Parse Anthropic response into provider-agnostic LLMResponse."""
        content_text = ""
        tool_calls: list[ToolCall] = []
        thinking_text: str | None = None

        for block in response.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                openai_tc = anthropic_tool_use_to_openai(block)
                tool_calls.append(ToolCall(
                    id=openai_tc["id"],
                    name=openai_tc["function"]["name"],
                    arguments=openai_tc["function"]["arguments"],
                ))
            elif block.type == "thinking":
                thinking_text = getattr(block, "thinking", "")

        # Token usage
        usage = response.usage
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        cache_creation = getattr(usage, "cache_creation_input_tokens", 0) or 0
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0

        self.total_tokens_used += input_tokens + output_tokens
        self.total_cached_tokens += cached
        self.total_cache_creation_tokens += cache_creation

        # Log cache performance (Story 97.2)
        total_input = input_tokens + cached + cache_creation
        if total_input > 0:
            cache_pct = (cached / total_input * 100) if total_input else 0
            logger.info(
                "Prompt cache: %d/%d tokens cached (%.1f%%)",
                cached, total_input, cache_pct,
            )

        token_usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cached_tokens=cached,
            cache_creation_tokens=cache_creation,
        )

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls if tool_calls else None,
            usage=token_usage,
            model=response.model,
            provider="anthropic",
            cached_tokens=cached,
            thinking=thinking_text,
        )

    def get_token_stats(self) -> dict[str, Any]:
        """Get token usage statistics."""
        return {
            "total_tokens_used": self.total_tokens_used,
            "total_cached_tokens": self.total_cached_tokens,
            "total_cache_creation_tokens": self.total_cache_creation_tokens,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "cache_hit_rate": (
                self.total_cached_tokens / (self.total_tokens_used + self.total_cached_tokens)
                if (self.total_tokens_used + self.total_cached_tokens) > 0
                else 0
            ),
        }

    def reset_stats(self) -> None:
        """Reset token usage statistics."""
        self.total_tokens_used = 0
        self.total_cached_tokens = 0
        self.total_cache_creation_tokens = 0
        self.total_requests = 0
        self.total_errors = 0
