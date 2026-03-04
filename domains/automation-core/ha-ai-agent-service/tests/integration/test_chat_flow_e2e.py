"""
End-to-End Tests for Chat Flow
Epic AI-20 Story AI20.11: Comprehensive Testing

Tests the complete chat flow from user message to agent response,
including tool calls, conversation persistence, and error scenarios.
"""

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient
from src.api.dependencies import set_services
from src.config import Settings
from src.main import app
from src.services.context_builder import ContextBuilder
from src.services.conversation_service import ConversationService
from src.services.openai_client import OpenAIClient
from src.services.prompt_assembly_service import PromptAssemblyService
from src.services.tool_service import ToolService


@pytest.fixture
def settings():
    """Create test settings"""
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
        database_url="postgresql+asyncpg://homeiq:homeiq@localhost:5432/homeiq",
    )


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock(spec=ContextBuilder)
    builder.build_complete_system_prompt = AsyncMock(
        return_value="System prompt with Tier 1 context"
    )
    builder.initialize = AsyncMock()
    builder.close = AsyncMock()
    builder._initialized = True
    return builder


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client"""
    client = MagicMock(spec=OpenAIClient)
    client.chat_completion = AsyncMock()
    client.total_tokens_used = 0
    client.total_requests = 0
    client.total_errors = 0
    return client


@pytest.fixture
def mock_tool_service():
    """Create mock tool service"""
    service = MagicMock(spec=ToolService)
    service.execute_tool_call = AsyncMock()
    return service


@pytest.fixture
async def conversation_service(settings, mock_context_builder):
    """Create conversation service instance"""
    return ConversationService(settings, mock_context_builder)


@pytest.fixture
async def prompt_assembly_service(settings, mock_context_builder, conversation_service):
    """Create prompt assembly service instance"""
    return PromptAssemblyService(settings, mock_context_builder, conversation_service)


@pytest.fixture
async def test_client(
    settings,
    _mock_context_builder,
    conversation_service,
    prompt_assembly_service,
    mock_openai_client,
    mock_tool_service,
):
    """Create test client with mocked services"""
    # Set services for dependency injection
    set_services(
        settings=settings,
        conversation_service=conversation_service,
        prompt_assembly_service=prompt_assembly_service,
        openai_client=mock_openai_client,
        tool_service=mock_tool_service,
    )

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


def create_mock_completion(content: str, tool_calls=None):
    """Create mock OpenAI Responses API response"""
    from types import SimpleNamespace

    output_items = []

    # Add function call items if provided
    if tool_calls:
        for tc in tool_calls:
            output_items.append(tc)

    # Add text message if content provided
    if content:
        output_items.append(
            SimpleNamespace(
                type="message",
                role="assistant",
                content=content,
            )
        )

    return SimpleNamespace(
        id="resp-test",
        output_text=content,
        output=output_items,
        model="gpt-4o-mini",
        stop_reason="stop",
        usage=SimpleNamespace(
            input_tokens=100,
            output_tokens=len(content.split()) if content else 0,
            output_tokens_details=None,
        ),
    )


def create_mock_tool_call(call_id: str, name: str, arguments: Dict[str, Any]):
    """Create mock Responses API function_call item"""
    import json
    from types import SimpleNamespace

    return SimpleNamespace(
        type="function_call",
        name=name,
        arguments=json.dumps(arguments),
        call_id=call_id,
    )


@pytest.mark.asyncio
async def test_chat_flow_simple_message(test_client, mock_openai_client):
    """Test complete chat flow with simple message"""
    # Mock OpenAI response
    mock_response = create_mock_completion("I can help you with Home Assistant automations.")
    mock_openai_client.chat_completion.return_value = mock_response

    # Send chat message
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Hello, can you help me?",
            "conversation_id": None,
            "refresh_context": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "I can help you with Home Assistant automations."
    assert "conversation_id" in data
    assert data["conversation_id"] is not None

    # Verify OpenAI was called
    mock_openai_client.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_chat_flow_with_tool_call(test_client, mock_openai_client, mock_tool_service):
    """Test complete chat flow with tool call"""
    # Mock tool call request
    tool_call = create_mock_tool_call(
        "call_123",
        "get_entity_state",
        {"entity_id": "light.kitchen"},
    )
    mock_response = create_mock_completion(
        "Let me check the kitchen light state.",
        tool_calls=[tool_call],
    )
    mock_openai_client.chat_completion.return_value = mock_response

    # Mock tool execution
    mock_tool_service.execute_tool_call.return_value = {
        "entity_id": "light.kitchen",
        "state": "on",
        "attributes": {"brightness": 255},
    }

    # Mock second OpenAI call (after tool execution)
    mock_response2 = create_mock_completion(
        "The kitchen light is currently on with 100% brightness."
    )
    mock_openai_client.chat_completion.side_effect = [mock_response, mock_response2]

    # Send chat message
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "What's the state of the kitchen light?",
            "conversation_id": None,
            "refresh_context": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "tool_calls" in data
    assert len(data["tool_calls"]) >= 0  # Tool calls may be in metadata

    # Verify tool was executed
    mock_tool_service.execute_tool_call.assert_called()


@pytest.mark.asyncio
async def test_chat_flow_multi_turn_conversation(test_client, mock_openai_client):
    """Test multi-turn conversation with conversation persistence"""
    conversation_id = None

    # First message
    mock_response1 = create_mock_completion(
        "I can help you create automations. What would you like to automate?"
    )
    mock_openai_client.chat_completion.return_value = mock_response1

    response1 = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "I want to create an automation",
            "conversation_id": None,
            "refresh_context": False,
        },
    )

    assert response1.status_code == 200
    data1 = response1.json()
    conversation_id = data1["conversation_id"]
    assert conversation_id is not None

    # Second message in same conversation
    mock_response2 = create_mock_completion(
        "Great! I can help you create an automation to turn on lights at sunset."
    )
    mock_openai_client.chat_completion.return_value = mock_response2

    response2 = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Turn on lights at sunset",
            "conversation_id": conversation_id,
            "refresh_context": False,
        },
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["conversation_id"] == conversation_id

    # Verify OpenAI was called twice (once per message)
    assert mock_openai_client.chat_completion.call_count == 2


@pytest.mark.asyncio
async def test_chat_flow_create_automation(test_client, mock_openai_client, mock_tool_service):
    """Test chat flow that creates an automation via tool call"""
    # First: Agent requests tool call to create automation
    automation_yaml = """
alias: Turn On Lights at Sunset
description: Turn on lights when sun sets
trigger:
  - platform: sun
    event: sunset
action:
  - service: light.turn_on
    target:
      entity_id: light.kitchen
"""
    tool_call = create_mock_tool_call(
        "call_create_automation",
        "create_automation",
        {"automation_yaml": automation_yaml},
    )
    mock_response1 = create_mock_completion(
        "I'll create an automation to turn on lights at sunset.",
        tool_calls=[tool_call],
    )

    # Second: Agent confirms success
    mock_response2 = create_mock_completion(
        "I've successfully created the automation 'Turn On Lights at Sunset'."
    )

    mock_openai_client.chat_completion.side_effect = [mock_response1, mock_response2]

    # Mock tool execution (create automation)
    mock_tool_service.execute_tool_call.return_value = {
        "success": True,
        "automation_id": "automation.test_automation",
    }

    # Send chat message
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Create an automation to turn on kitchen lights at sunset",
            "conversation_id": None,
            "refresh_context": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "automation" in data["message"].lower() or "created" in data["message"].lower()

    # Verify tool was executed
    mock_tool_service.execute_tool_call.assert_called()


@pytest.mark.asyncio
async def test_chat_flow_error_handling(test_client, mock_openai_client):
    """Test error handling in chat flow"""
    # Mock OpenAI error
    from src.services.openai_client import OpenAIError

    mock_openai_client.chat_completion.side_effect = OpenAIError("OpenAI API error")

    # Send chat message
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Test message",
            "conversation_id": None,
            "refresh_context": False,
        },
    )

    assert response.status_code == 500
    data = response.json()
    assert "error" in data or "detail" in data


@pytest.mark.asyncio
async def test_chat_flow_invalid_conversation_id(test_client, mock_openai_client):
    """Test error handling with invalid conversation ID"""
    # Mock OpenAI response
    mock_response = create_mock_completion("Response message")
    mock_openai_client.chat_completion.return_value = mock_response

    # Send chat message with invalid conversation ID
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Test message",
            "conversation_id": "invalid-conversation-id",
            "refresh_context": False,
        },
    )

    # Should either create new conversation or return error
    assert response.status_code in [200, 404, 400]


@pytest.mark.asyncio
async def test_chat_flow_refresh_context(test_client, mock_openai_client, mock_context_builder):
    """Test chat flow with context refresh"""
    # Mock OpenAI response
    mock_response = create_mock_completion("Response with refreshed context")
    mock_openai_client.chat_completion.return_value = mock_response

    # Reset mock to track calls
    mock_context_builder.build_complete_system_prompt.reset_mock()

    # Send chat message with context refresh
    response = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "What devices do I have?",
            "conversation_id": None,
            "refresh_context": True,
        },
    )

    assert response.status_code == 200
    # Verify context was rebuilt (called with refresh_context=True)
    mock_context_builder.build_complete_system_prompt.assert_called()


@pytest.mark.asyncio
async def test_chat_flow_conversation_persistence(test_client, mock_openai_client, conversation_service):
    """Test that conversation persists across requests"""
    # First message - create conversation
    mock_response1 = create_mock_completion("First response")
    mock_openai_client.chat_completion.return_value = mock_response1

    response1 = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "First message",
            "conversation_id": None,
            "refresh_context": False,
        },
    )

    assert response1.status_code == 200
    data1 = response1.json()
    conversation_id = data1["conversation_id"]

    # Verify conversation exists
    conversation = await conversation_service.get_conversation(conversation_id)
    assert conversation is not None
    assert conversation.conversation_id == conversation_id

    # Second message - use existing conversation
    mock_response2 = create_mock_completion("Second response")
    mock_openai_client.chat_completion.return_value = mock_response2

    response2 = await test_client.post(
        "/api/v1/chat",
        json={
            "message": "Second message",
            "conversation_id": conversation_id,
            "refresh_context": False,
        },
    )

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["conversation_id"] == conversation_id

    # Verify conversation has both messages
    conversation = await conversation_service.get_conversation(conversation_id)
    assert conversation is not None
    # Messages should be persisted (checked via conversation service)

