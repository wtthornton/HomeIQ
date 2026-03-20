"""Tests for LLM response models (Story 97.1.5)."""

from __future__ import annotations

from src.models.llm_models import LLMResponse, TokenUsage, ToolCall


class TestToolCall:
    def test_fields(self):
        tc = ToolCall(id="call_1", name="preview_automation_from_prompt", arguments='{"user_prompt": "test"}')
        assert tc.id == "call_1"
        assert tc.name == "preview_automation_from_prompt"
        assert tc.arguments == '{"user_prompt": "test"}'


class TestTokenUsage:
    def test_defaults_zero(self):
        usage = TokenUsage()
        assert usage.input_tokens == 0
        assert usage.output_tokens == 0
        assert usage.cached_tokens == 0

    def test_with_cache(self):
        usage = TokenUsage(input_tokens=500, cached_tokens=8000, cache_creation_tokens=0)
        assert usage.cached_tokens == 8000


class TestLLMResponse:
    def test_text_response(self):
        resp = LLMResponse(content="Hello", provider="anthropic", model="claude-sonnet-4-6")
        assert resp.content == "Hello"
        assert resp.tool_calls is None
        assert resp.thinking is None

    def test_with_tool_calls(self):
        tc = ToolCall(id="1", name="test", arguments="{}")
        resp = LLMResponse(content="", tool_calls=[tc], provider="openai", model="gpt-5.2")
        assert len(resp.tool_calls) == 1
        assert resp.provider == "openai"

    def test_with_thinking(self):
        resp = LLMResponse(
            content="Result",
            provider="anthropic",
            model="claude-sonnet-4-6",
            thinking="I need to analyze...",
        )
        assert resp.thinking == "I need to analyze..."

    def test_default_usage(self):
        resp = LLMResponse(content="test")
        assert resp.usage.total_tokens == 0
