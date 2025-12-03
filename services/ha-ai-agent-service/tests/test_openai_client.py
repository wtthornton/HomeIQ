"""
Unit tests for OpenAI Client Service
Epic AI-20 Story AI20.1
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Settings
from src.services.openai_client import (
    OpenAIClient,
    OpenAIError,
    OpenAIRateLimitError,
    OpenAITokenBudgetExceededError,
)


@pytest.fixture
def settings():
    """Create test settings"""
    return Settings(
        openai_api_key="test-api-key",
        openai_model="gpt-4o-mini",
        openai_max_tokens=4096,
        openai_temperature=0.7,
        openai_timeout=30,
        openai_max_retries=3,
    )


@pytest.fixture
def openai_client(settings):
    """Create OpenAI client instance"""
    return OpenAIClient(settings)


@pytest.mark.asyncio
async def test_client_initialization(settings):
    """Test OpenAI client initialization"""
    client = OpenAIClient(settings)

    assert client.model == "gpt-4o-mini"
    assert client.max_tokens == 4096
    assert client.temperature == 0.7
    assert client.total_tokens_used == 0
    assert client.total_requests == 0


def test_client_initialization_missing_api_key():
    """Test that client raises error if API key is missing"""
    settings = Settings(openai_api_key=None)

    with pytest.raises(ValueError, match="OpenAI API key is required"):
        OpenAIClient(settings)


@pytest.mark.asyncio
async def test_chat_completion_success(openai_client):
    """Test successful chat completion"""
    # Mock OpenAI API response
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="Test response",
                role="assistant",
                tool_calls=None,
            )
        )
    ]
    mock_response.usage = MagicMock(
        total_tokens=100,
        prompt_tokens=50,
        completion_tokens=50,
    )

    with patch.object(
        openai_client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ]

        response = await openai_client.chat_completion(messages)

        assert response.choices[0].message.content == "Test response"
        assert openai_client.total_tokens_used == 100
        assert openai_client.total_requests == 1
        assert openai_client.total_errors == 0

        # Verify API was called correctly
        mock_create.assert_called_once()
        call_args = mock_create.call_args[1]
        assert call_args["model"] == "gpt-4o-mini"
        assert call_args["messages"] == messages
        assert call_args["temperature"] == 0.7
        assert call_args["max_tokens"] == 4096


@pytest.mark.asyncio
async def test_chat_completion_with_tools(openai_client):
    """Test chat completion with function calling tools"""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content=None,
                role="assistant",
                tool_calls=[
                    MagicMock(
                        id="call_123",
                        type="function",
                        function=MagicMock(
                            name="get_entity_state",
                            arguments='{"entity_id": "light.kitchen"}',
                        ),
                    )
                ],
            )
        )
    ]
    mock_response.usage = MagicMock(
        total_tokens=150,
        prompt_tokens=100,
        completion_tokens=50,
    )

    with patch.object(
        openai_client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        messages = [{"role": "user", "content": "Turn on the kitchen light"}]
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "get_entity_state",
                    "description": "Get entity state",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "entity_id": {"type": "string"},
                        },
                    },
                },
            }
        ]

        response = await openai_client.chat_completion(messages, tools=tools)

        assert response.choices[0].message.tool_calls is not None
        assert len(response.choices[0].message.tool_calls) == 1
        assert openai_client.total_tokens_used == 150

        # Verify tools were passed to API
        call_args = mock_create.call_args[1]
        assert "tools" in call_args
        assert len(call_args["tools"]) == 1


@pytest.mark.asyncio
async def test_chat_completion_simple(openai_client):
    """Test simple chat completion helper"""
    mock_response = MagicMock()
    mock_response.choices = [
        MagicMock(
            message=MagicMock(
                content="Hello! How can I help you?",
                role="assistant",
                tool_calls=None,
            )
        )
    ]
    mock_response.usage = MagicMock(
        total_tokens=50,
        prompt_tokens=30,
        completion_tokens=20,
    )

    with patch.object(
        openai_client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        response = await openai_client.chat_completion_simple(
            "You are a helpful assistant", "Hello"
        )

        assert response == "Hello! How can I help you?"
        assert openai_client.total_tokens_used == 50


@pytest.mark.asyncio
async def test_chat_completion_rate_limit_error(openai_client):
    """Test handling of rate limit errors (429)"""
    from openai import RateLimitError

    with patch.object(
        openai_client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(status_code=429),
            body=None,
        )

        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(OpenAIRateLimitError):
            await openai_client.chat_completion(messages)

            # Should have attempted retries (3 attempts)
            assert mock_create.call_count == 3
            # Error is counted once after all retries exhausted
            assert openai_client.total_errors == 1


@pytest.mark.asyncio
async def test_chat_completion_token_budget_error(openai_client):
    """Test handling of token budget errors"""
    from openai import APIError

    error = APIError(
        message="Token budget exceeded",
        request=MagicMock(),
        body={"error": {"message": "Token budget exceeded"}},
    )

    with patch.object(
        openai_client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = error

        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(OpenAITokenBudgetExceededError):
            await openai_client.chat_completion(messages)

        assert openai_client.total_errors == 1


@pytest.mark.asyncio
async def test_chat_completion_generic_error(openai_client):
    """Test handling of generic API errors"""
    with patch.object(
        openai_client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = Exception("Network error")

        messages = [{"role": "user", "content": "Hello"}]

        with pytest.raises(OpenAIError):
            await openai_client.chat_completion(messages)

        assert openai_client.total_errors == 1


def test_get_token_stats(openai_client):
    """Test token statistics tracking"""
    # Set some stats
    openai_client.total_tokens_used = 500
    openai_client.total_requests = 10
    openai_client.total_errors = 1

    stats = openai_client.get_token_stats()

    assert stats["total_tokens_used"] == 500
    assert stats["total_requests"] == 10
    assert stats["total_errors"] == 1
    assert stats["average_tokens_per_request"] == 50.0


def test_reset_stats(openai_client):
    """Test resetting token statistics"""
    # Set some stats
    openai_client.total_tokens_used = 500
    openai_client.total_requests = 10
    openai_client.total_errors = 1

    openai_client.reset_stats()

    assert openai_client.total_tokens_used == 0
    assert openai_client.total_requests == 0
    assert openai_client.total_errors == 0


@pytest.mark.asyncio
async def test_custom_max_tokens_and_temperature(openai_client):
    """Test custom max_tokens and temperature parameters"""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Test"))]
    mock_response.usage = MagicMock(total_tokens=100)

    with patch.object(
        openai_client.client.chat.completions, "create", new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = mock_response

        messages = [{"role": "user", "content": "Hello"}]

        await openai_client.chat_completion(
            messages, max_tokens=2000, temperature=0.9
        )

        call_args = mock_create.call_args[1]
        assert call_args["max_tokens"] == 2000
        assert call_args["temperature"] == 0.9

