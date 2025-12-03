"""Tests for HA AI Agent Client"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from src.clients.ha_agent_client import HAAgentClient


@pytest.mark.asyncio
async def test_send_message_success():
    """Test successful message sending"""
    client = HAAgentClient(base_url="http://test-ha-agent:8030")

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": "I've created the automation for you.",
        "conversation_id": "conv-123",
        "tool_calls": [],
        "metadata": {"model": "gpt-4o-mini", "tokens_used": 150},
    }
    mock_response.raise_for_status = AsyncMock()

    with patch.object(client.client, 'post', return_value=mock_response):
        result = await client.send_message("Create an automation to turn on lights at sunset")

        assert result is not None
        assert result["message"] == "I've created the automation for you."
        assert result["conversation_id"] == "conv-123"
        assert "tool_calls" in result

    await client.close()


@pytest.mark.asyncio
async def test_send_message_with_conversation_id():
    """Test sending message with existing conversation ID"""
    client = HAAgentClient(base_url="http://test-ha-agent:8030")

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": "I've updated the automation.",
        "conversation_id": "conv-456",
        "tool_calls": [],
        "metadata": {},
    }
    mock_response.raise_for_status = AsyncMock()

    with patch.object(client.client, 'post', return_value=mock_response):
        result = await client.send_message(
            "Update the automation",
            conversation_id="conv-456"
        )

        assert result is not None
        assert result["conversation_id"] == "conv-456"

    await client.close()


@pytest.mark.asyncio
async def test_send_message_with_refresh_context():
    """Test sending message with refresh_context flag"""
    client = HAAgentClient(base_url="http://test-ha-agent:8030")

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "message": "Context refreshed and automation created.",
        "conversation_id": "conv-789",
        "tool_calls": [],
        "metadata": {},
    }
    mock_response.raise_for_status = AsyncMock()

    with patch.object(client.client, 'post', return_value=mock_response) as mock_post:
        result = await client.send_message(
            "Create automation",
            refresh_context=True
        )

        assert result is not None
        # Verify refresh_context was sent in payload
        call_args = mock_post.call_args
        assert call_args[1]["json"]["refresh_context"] is True

    await client.close()


@pytest.mark.asyncio
async def test_send_message_connection_error():
    """Test graceful degradation on connection error"""
    client = HAAgentClient(base_url="http://test-ha-agent:8030")

    with patch.object(client.client, 'post', side_effect=Exception("Connection failed")):
        result = await client.send_message("Test message")
        assert result is None  # Graceful degradation

    await client.close()


@pytest.mark.asyncio
async def test_send_message_timeout():
    """Test graceful degradation on timeout"""
    client = HAAgentClient(base_url="http://test-ha-agent:8030", timeout=5)

    import httpx
    with patch.object(client.client, 'post', side_effect=httpx.TimeoutException("Timeout")):
        result = await client.send_message("Test message")
        assert result is None  # Graceful degradation

    await client.close()


@pytest.mark.asyncio
async def test_send_message_invalid_response():
    """Test handling of invalid response structure"""
    client = HAAgentClient(base_url="http://test-ha-agent:8030")

    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "invalid": "response",
        # Missing required fields
    }
    mock_response.raise_for_status = AsyncMock()

    with patch.object(client.client, 'post', return_value=mock_response):
        result = await client.send_message("Test message")
        assert result is None  # Invalid response rejected

    await client.close()


@pytest.mark.asyncio
async def test_validate_response_valid():
    """Test response validation with valid response"""
    client = HAAgentClient()

    valid_response = {
        "message": "Test response",
        "conversation_id": "conv-123",
        "tool_calls": [],
        "metadata": {},
    }

    assert client._validate_response(valid_response) is True


@pytest.mark.asyncio
async def test_validate_response_invalid():
    """Test response validation with invalid response"""
    client = HAAgentClient()

    invalid_response = {
        "message": "Test response",
        # Missing conversation_id
    }

    assert client._validate_response(invalid_response) is False


@pytest.mark.asyncio
async def test_close_client():
    """Test client cleanup"""
    client = HAAgentClient()
    await client.close()
    # Should not raise exception

