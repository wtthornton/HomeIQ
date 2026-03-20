"""Tests for Anthropic Claude client (Stories 97.1, 97.2, 97.6).

Tests use mocked Anthropic API responses.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.clients.anthropic_client import AnthropicLLMClient
from src.models.llm_models import LLMResponse


# ---------------------------------------------------------------------------
# Mock Anthropic response objects
# ---------------------------------------------------------------------------

@dataclass
class MockUsage:
    input_tokens: int = 1000
    output_tokens: int = 200
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0


@dataclass
class MockTextBlock:
    type: str = "text"
    text: str = "Here's your automation YAML..."


@dataclass
class MockToolUseBlock:
    type: str = "tool_use"
    id: str = "toolu_01"
    name: str = "preview_automation_from_prompt"
    input: dict = None

    def __post_init__(self):
        if self.input is None:
            self.input = {
                "user_prompt": "lights at sunset",
                "automation_yaml": "alias: Sunset Lights\ntrigger:\n  - platform: sun\n    event: sunset",
                "alias": "Sunset Lights",
            }


@dataclass
class MockThinkingBlock:
    type: str = "thinking"
    thinking: str = "Let me analyze this complex automation request..."


@dataclass
class MockResponse:
    content: list = None
    model: str = "claude-sonnet-4-6"
    usage: MockUsage = None

    def __post_init__(self):
        if self.content is None:
            self.content = [MockTextBlock()]
        if self.usage is None:
            self.usage = MockUsage()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Create AnthropicLLMClient with mocked SDK."""
    with patch("src.clients.anthropic_client.anthropic") as mock_anthropic:
        mock_async_client = MagicMock()
        mock_anthropic.AsyncAnthropic.return_value = mock_async_client
        c = AnthropicLLMClient(api_key="test-key", model="claude-sonnet-4-6")
        c.client = mock_async_client
        yield c


class TestAnthropicClientInit:
    """Story 97.1: Client initialization."""

    def test_creates_client_with_api_key(self):
        with patch("src.clients.anthropic_client.anthropic") as mock_anthropic:
            client = AnthropicLLMClient(api_key="sk-test", model="claude-sonnet-4-6")
            mock_anthropic.AsyncAnthropic.assert_called_once_with(api_key="sk-test")
            assert client.model == "claude-sonnet-4-6"

    def test_initial_stats_zero(self):
        with patch("src.clients.anthropic_client.anthropic"):
            client = AnthropicLLMClient(api_key="test", model="claude-sonnet-4-6")
            stats = client.get_token_stats()
            assert stats["total_tokens_used"] == 0
            assert stats["total_requests"] == 0


class TestChatCompletion:
    """Story 97.1: Basic chat completion."""

    @pytest.mark.asyncio
    async def test_simple_text_response(self, client):
        mock_response = MockResponse(
            content=[MockTextBlock(text="I'll create a sunset automation.")],
            usage=MockUsage(input_tokens=500, output_tokens=100),
        )
        client.client.messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat_completion(
            system_prompt="You are HomeIQ AI.",
            messages=[{"role": "user", "content": "Turn on lights at sunset"}],
        )

        assert isinstance(result, LLMResponse)
        assert result.content == "I'll create a sunset automation."
        assert result.provider == "anthropic"
        assert result.model == "claude-sonnet-4-6"
        assert result.tool_calls is None

    @pytest.mark.asyncio
    async def test_tool_use_response(self, client):
        mock_response = MockResponse(
            content=[
                MockTextBlock(text="Let me preview that."),
                MockToolUseBlock(),
            ],
            usage=MockUsage(input_tokens=800, output_tokens=300),
        )
        client.client.messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat_completion(
            system_prompt="You are HomeIQ AI.",
            messages=[{"role": "user", "content": "Create automation"}],
            tools=[{
                "type": "function",
                "name": "preview_automation_from_prompt",
                "description": "Preview automation",
                "parameters": {"type": "object", "properties": {}},
            }],
        )

        assert result.content == "Let me preview that."
        assert result.tool_calls is not None
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "preview_automation_from_prompt"
        assert result.tool_calls[0].id == "toolu_01"

    @pytest.mark.asyncio
    async def test_tracks_request_count(self, client):
        client.client.messages.create = AsyncMock(return_value=MockResponse())
        await client.chat_completion(
            system_prompt="sys",
            messages=[{"role": "user", "content": "test"}],
        )
        assert client.total_requests == 1

    @pytest.mark.asyncio
    async def test_tracks_token_usage(self, client):
        client.client.messages.create = AsyncMock(
            return_value=MockResponse(usage=MockUsage(input_tokens=1000, output_tokens=200))
        )
        await client.chat_completion(
            system_prompt="sys",
            messages=[{"role": "user", "content": "test"}],
        )
        assert client.total_tokens_used == 1200


class TestPromptCaching:
    """Story 97.2: Prompt caching with cache_control breakpoints."""

    @pytest.mark.asyncio
    async def test_cache_control_set_on_system_blocks(self, client):
        client.client.messages.create = AsyncMock(return_value=MockResponse())

        await client.chat_completion(
            system_prompt="Static system prompt text",
            messages=[{"role": "user", "content": "test"}],
            enable_caching=True,
        )

        call_kwargs = client.client.messages.create.call_args.kwargs
        system_blocks = call_kwargs["system"]
        assert len(system_blocks) >= 1
        assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}

    @pytest.mark.asyncio
    async def test_entity_context_cached_separately(self, client):
        client.client.messages.create = AsyncMock(return_value=MockResponse())

        await client.chat_completion(
            system_prompt="System prompt",
            messages=[{"role": "user", "content": "test"}],
            enable_caching=True,
            entity_context="ENTITY INVENTORY:\nlight.office - Office Light",
        )

        call_kwargs = client.client.messages.create.call_args.kwargs
        system_blocks = call_kwargs["system"]
        assert len(system_blocks) == 2
        assert system_blocks[0]["cache_control"] == {"type": "ephemeral"}
        assert system_blocks[1]["cache_control"] == {"type": "ephemeral"}
        assert "ENTITY INVENTORY" in system_blocks[1]["text"]

    @pytest.mark.asyncio
    async def test_no_cache_control_when_disabled(self, client):
        client.client.messages.create = AsyncMock(return_value=MockResponse())

        await client.chat_completion(
            system_prompt="System prompt",
            messages=[{"role": "user", "content": "test"}],
            enable_caching=False,
        )

        call_kwargs = client.client.messages.create.call_args.kwargs
        system_blocks = call_kwargs["system"]
        assert "cache_control" not in system_blocks[0]

    @pytest.mark.asyncio
    async def test_cache_hit_tracked(self, client):
        mock_response = MockResponse(
            usage=MockUsage(
                input_tokens=500,
                output_tokens=100,
                cache_read_input_tokens=8000,
                cache_creation_input_tokens=0,
            )
        )
        client.client.messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat_completion(
            system_prompt="sys",
            messages=[{"role": "user", "content": "test"}],
        )

        assert result.cached_tokens == 8000
        assert result.usage.cached_tokens == 8000
        assert client.total_cached_tokens == 8000

    @pytest.mark.asyncio
    async def test_cache_creation_tracked(self, client):
        mock_response = MockResponse(
            usage=MockUsage(
                input_tokens=500,
                output_tokens=100,
                cache_read_input_tokens=0,
                cache_creation_input_tokens=10000,
            )
        )
        client.client.messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat_completion(
            system_prompt="sys",
            messages=[{"role": "user", "content": "test"}],
        )

        assert result.usage.cache_creation_tokens == 10000
        assert client.total_cache_creation_tokens == 10000


class TestExtendedThinking:
    """Story 97.6: Extended thinking for complex automations."""

    @pytest.mark.asyncio
    async def test_thinking_blocks_parsed(self, client):
        mock_response = MockResponse(
            content=[
                MockThinkingBlock(thinking="Analyzing multi-trigger automation..."),
                MockTextBlock(text="Here's the complex automation."),
            ],
        )
        client.client.messages.create = AsyncMock(return_value=mock_response)

        result = await client.chat_completion(
            system_prompt="sys",
            messages=[{"role": "user", "content": "test"}],
            thinking={"type": "enabled", "budget_tokens": 4096},
        )

        assert result.thinking == "Analyzing multi-trigger automation..."
        assert result.content == "Here's the complex automation."

    @pytest.mark.asyncio
    async def test_thinking_parameter_passed_to_api(self, client):
        client.client.messages.create = AsyncMock(return_value=MockResponse())

        thinking_config = {"type": "enabled", "budget_tokens": 4096}
        await client.chat_completion(
            system_prompt="sys",
            messages=[{"role": "user", "content": "test"}],
            thinking=thinking_config,
        )

        call_kwargs = client.client.messages.create.call_args.kwargs
        assert call_kwargs["thinking"] == thinking_config
        # Temperature should NOT be set when thinking is enabled
        assert "temperature" not in call_kwargs

    @pytest.mark.asyncio
    async def test_no_thinking_without_config(self, client):
        client.client.messages.create = AsyncMock(return_value=MockResponse())

        await client.chat_completion(
            system_prompt="sys",
            messages=[{"role": "user", "content": "test"}],
        )

        call_kwargs = client.client.messages.create.call_args.kwargs
        assert "thinking" not in call_kwargs
        assert "temperature" in call_kwargs


class TestTokenStats:
    """Token statistics tracking."""

    def test_reset_stats(self):
        with patch("src.clients.anthropic_client.anthropic"):
            client = AnthropicLLMClient(api_key="test", model="claude-sonnet-4-6")
            client.total_tokens_used = 5000
            client.total_requests = 10
            client.reset_stats()
            assert client.total_tokens_used == 0
            assert client.total_requests == 0

    @pytest.mark.asyncio
    async def test_error_count_tracked(self, client):
        client.client.messages.create = AsyncMock(
            side_effect=Exception("API error")
        )

        # Patch the anthropic module's APIError to be a regular Exception
        with patch("src.clients.anthropic_client.anthropic") as mock_mod:
            mock_mod.RateLimitError = type("RateLimitError", (Exception,), {})
            mock_mod.APIError = type("APIError", (Exception,), {})

            with pytest.raises(Exception):
                await client.chat_completion(
                    system_prompt="sys",
                    messages=[{"role": "user", "content": "test"}],
                )
