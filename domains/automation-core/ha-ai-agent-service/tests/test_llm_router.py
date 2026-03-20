"""Tests for LLM Router (Stories 97.3, 97.6).

Tests provider selection, fallback, circuit breaker, and complexity detection.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.llm_models import LLMResponse, TokenUsage
from src.services.llm_router import LLMRouter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides):
    """Create a mock Settings object."""
    defaults = {
        "llm_provider": "anthropic",
        "llm_fallback_provider": "openai",
        "anthropic_api_key": MagicMock(get_secret_value=MagicMock(return_value="sk-ant-test")),
        "anthropic_model": "claude-sonnet-4-6",
        "openai_api_key": MagicMock(get_secret_value=MagicMock(return_value="sk-oai-test")),
        "openai_model": "gpt-5.2-codex",
    }
    defaults.update(overrides)
    settings = MagicMock()
    for k, v in defaults.items():
        setattr(settings, k, v)
    return settings


def _make_llm_response(provider: str = "anthropic") -> LLMResponse:
    return LLMResponse(
        content="Test response",
        provider=provider,
        model="claude-sonnet-4-6" if provider == "anthropic" else "gpt-5.2",
        usage=TokenUsage(input_tokens=100, output_tokens=50, total_tokens=150),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLLMRouterInit:
    """Story 97.3: Router initialization."""

    def test_creates_anthropic_primary(self):
        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.return_value = MagicMock()
            settings = _make_settings(llm_provider="anthropic")
            router = LLMRouter(settings)
            assert router.primary_provider == "anthropic"

    def test_creates_openai_fallback(self):
        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.return_value = MagicMock()
            settings = _make_settings(llm_fallback_provider="openai")
            router = LLMRouter(settings)
            assert router.fallback_provider == "openai"

    def test_no_fallback_when_none(self):
        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.return_value = MagicMock()
            settings = _make_settings(llm_fallback_provider=None)
            router = LLMRouter(settings)
            assert router._fallback is None


class TestProviderStatus:
    """Story 97.3: Health endpoint status."""

    def test_returns_provider_status(self):
        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.return_value = MagicMock()
            settings = _make_settings()
            router = LLMRouter(settings)
            status = router.get_provider_status()
            assert "primary" in status
            assert status["primary"]["provider"] == "anthropic"
            assert status["primary"]["available"] is True

    def test_fallback_status_included(self):
        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.return_value = MagicMock()
            settings = _make_settings()
            router = LLMRouter(settings)
            status = router.get_provider_status()
            assert "fallback" in status
            assert status["fallback"]["provider"] == "openai"


class TestComplexityDetection:
    """Story 97.6: Complexity detection for extended thinking."""

    def test_simple_request_not_complex(self):
        assert not LLMRouter._is_complex_automation("Turn on office lights at sunset")

    def test_short_request_not_complex(self):
        assert not LLMRouter._is_complex_automation("lights on")

    def test_complex_multi_condition(self):
        msg = (
            "If motion is detected in the office and it's after sunset, "
            "turn on the lights unless they're already on, and also set "
            "the temperature to 72 and send me a notification"
        )
        assert LLMRouter._is_complex_automation(msg)

    def test_complex_multiple_ands(self):
        msg = (
            "When I come home and it's dark and the temperature is below 70 "
            "and no one else is home, then turn on the lights and heat and "
            "play my arrival playlist"
        )
        assert LLMRouter._is_complex_automation(msg)

    def test_complex_with_keywords(self):
        msg = (
            "Create a sequence of actions: when motion in hallway, unless "
            "it's between midnight and 6am, turn on lights at 30% brightness "
            "and then gradually increase over 5 minutes"
        )
        assert LLMRouter._is_complex_automation(msg)

    def test_moderate_request_not_complex(self):
        # Has one keyword but is short — should not trigger
        assert not LLMRouter._is_complex_automation("Schedule lights to turn on at 7pm")

    def test_long_but_simple_not_complex(self):
        # Long but no complexity keywords or multiple conditions
        msg = "a" * 250  # Long but just filler
        assert not LLMRouter._is_complex_automation(msg)


class TestChatCompletionRouting:
    """Story 97.3: Routing and fallback."""

    @pytest.mark.asyncio
    async def test_routes_to_anthropic_primary(self):
        mock_client = AsyncMock()
        mock_client.chat_completion = AsyncMock(return_value=_make_llm_response())

        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.side_effect = lambda p, s: mock_client if p == "anthropic" else None
            settings = _make_settings(llm_fallback_provider=None)
            router = LLMRouter(settings)

            result = await router.chat_completion(
                system_prompt="sys",
                messages=[{"role": "user", "content": "test"}],
            )

            assert result.provider == "anthropic"
            mock_client.chat_completion.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_when_openai_primary_no_anthropic_fallback(self):
        """OpenAI primary with no Anthropic fallback raises NotImplementedError."""
        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.return_value = "openai"
            settings = _make_settings(
                llm_provider="openai",
                llm_fallback_provider=None,
            )
            router = LLMRouter(settings)

            with pytest.raises(RuntimeError):
                await router.chat_completion(
                    system_prompt="sys",
                    messages=[{"role": "user", "content": "test"}],
                )

    @pytest.mark.asyncio
    async def test_extended_thinking_for_complex_request(self):
        mock_client = AsyncMock()
        mock_client.chat_completion = AsyncMock(return_value=_make_llm_response())

        with patch("src.services.llm_router.LLMRouter._create_client") as mock_create:
            mock_create.side_effect = lambda p, s: mock_client if p == "anthropic" else None
            settings = _make_settings(llm_fallback_provider=None)
            router = LLMRouter(settings)

            complex_msg = (
                "If motion in office and it's after sunset, unless already on, "
                "turn on lights and set temperature and send notification, "
                "then after 30 minutes if no motion turn everything off"
            )
            await router.chat_completion(
                system_prompt="sys",
                messages=[{"role": "user", "content": complex_msg}],
                user_message=complex_msg,
            )

            call_kwargs = mock_client.chat_completion.call_args.kwargs
            assert call_kwargs["thinking"] == {"type": "enabled", "budget_tokens": 4096}
