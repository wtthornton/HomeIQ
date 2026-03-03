"""
Tests for openai_client.py
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestOpenAIClient:
    """Test OpenAIClient class."""

    @patch("src.clients.openai_client.settings")
    def test___init___with_api_key(self, mock_settings):
        """Test initialization with API key sets up client."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        with patch("src.clients.openai_client.AsyncOpenAI") as mock_openai:
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="gpt-4o-mini")

            assert client.api_key == "sk-test-key"
            assert client.model == "gpt-4o-mini"
            assert client.is_fine_tuned is False
            assert client.total_tokens_used == 0
            assert client.total_cost_usd == 0.0
            mock_openai.assert_called_once_with(api_key="sk-test-key")

    @patch("src.clients.openai_client.settings")
    def test___init___without_api_key(self, mock_settings):
        """Test initialization without API key logs warning."""
        mock_settings.openai_api_key = None
        mock_settings.openai_model = "gpt-4o-mini"

        from src.clients.openai_client import OpenAIClient

        client = OpenAIClient(api_key=None, model="gpt-4o-mini")

        assert client.client is None

    @patch("src.clients.openai_client.settings")
    def test___init___fine_tuned_model(self, mock_settings):
        """Test initialization with fine-tuned model prefix."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        with patch("src.clients.openai_client.AsyncOpenAI"):
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="ft:gpt-4o-mini:org:name:id")

            assert client.is_fine_tuned is True
            assert client.model == "ft:gpt-4o-mini:org:name:id"

    @patch("src.clients.openai_client.settings")
    def test_get_usage_stats(self, mock_settings):
        """Test get_usage_stats returns correct structure."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        with patch("src.clients.openai_client.AsyncOpenAI"):
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="gpt-4o-mini")
            client.total_tokens_used = 150
            client.total_cost_usd = 0.005

            stats = client.get_usage_stats()

            assert stats["total_tokens"] == 150
            assert stats["total_cost_usd"] == 0.005
            assert stats["model"] == "gpt-4o-mini"

    @patch("src.clients.openai_client.settings")
    def test_reset_usage_stats(self, mock_settings):
        """Test reset_usage_stats clears counters."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        with patch("src.clients.openai_client.AsyncOpenAI"):
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="gpt-4o-mini")
            client.total_tokens_used = 150
            client.total_cost_usd = 0.005

            client.reset_usage_stats()

            assert client.total_tokens_used == 0
            assert client.total_cost_usd == 0.0

    @patch("src.clients.openai_client.settings")
    def test_supports_temperature_for_gpt4(self, mock_settings):
        """Test temperature support for standard models."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        with patch("src.clients.openai_client.AsyncOpenAI"):
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="gpt-4o-mini")
            assert client.supports_temperature is True

    @patch("src.clients.openai_client.settings")
    def test_no_temperature_for_reasoning_models(self, mock_settings):
        """Test temperature disabled for o1/o3/gpt-5 models."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        with patch("src.clients.openai_client.AsyncOpenAI"):
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="o1-preview")
            assert client.supports_temperature is False
            assert client.is_reasoning_model is True

    @pytest.mark.asyncio
    @patch("src.clients.openai_client.settings")
    async def test_generate_yaml_no_client_raises(self, mock_settings):
        """Test generate_yaml raises when no API key."""
        mock_settings.openai_api_key = None
        mock_settings.openai_model = "gpt-4o-mini"

        from src.clients.openai_client import OpenAIClient

        client = OpenAIClient(api_key=None, model="gpt-4o-mini")

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            await client.generate_yaml("Turn on the lights")

    @pytest.mark.asyncio
    @patch("src.clients.openai_client.settings")
    async def test_generate_yaml_success(self, mock_settings):
        """Test generate_yaml returns cleaned YAML."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_response = MagicMock()
        mock_response.output_text = "alias: Test\ntrigger:\n  - platform: state"
        mock_response.usage = MagicMock(input_tokens=70, output_tokens=30)

        mock_async_openai = MagicMock()
        mock_async_openai.responses.create = AsyncMock(return_value=mock_response)

        with patch("src.clients.openai_client.AsyncOpenAI", return_value=mock_async_openai):
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="gpt-4o-mini")

            result = await client.generate_yaml("Turn on the lights")

            assert "alias: Test" in result
            assert "trigger:" in result
            assert client.total_tokens_used == 100

    @pytest.mark.asyncio
    @patch("src.clients.openai_client.settings")
    async def test_generate_yaml_strips_code_blocks(self, mock_settings):
        """Test generate_yaml strips markdown code blocks."""
        mock_settings.openai_api_key = "sk-test-key"
        mock_settings.openai_model = "gpt-4o-mini"

        mock_response = MagicMock()
        mock_response.output_text = "```yaml\nalias: Test\ntrigger:\n  - platform: state\n```"
        mock_response.usage = MagicMock(input_tokens=30, output_tokens=20)

        mock_async_openai = MagicMock()
        mock_async_openai.responses.create = AsyncMock(return_value=mock_response)

        with patch("src.clients.openai_client.AsyncOpenAI", return_value=mock_async_openai):
            from src.clients.openai_client import OpenAIClient

            client = OpenAIClient(api_key="sk-test-key", model="gpt-4o-mini")

            result = await client.generate_yaml("Turn on the lights")

            assert not result.startswith("```")
            assert "alias: Test" in result

    @pytest.mark.asyncio
    @patch("src.clients.openai_client.settings")
    async def test_generate_structured_plan_no_client_raises(self, mock_settings):
        """Test generate_structured_plan raises when no API key."""
        mock_settings.openai_api_key = None
        mock_settings.openai_model = "gpt-4o-mini"

        from src.clients.openai_client import OpenAIClient

        client = OpenAIClient(api_key=None, model="gpt-4o-mini")

        with pytest.raises(ValueError, match="OpenAI API key not configured"):
            await client.generate_structured_plan("Turn on the lights")
