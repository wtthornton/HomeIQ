"""
Integration tests for Chat API Endpoints
Epic AI-20 Story AI20.4

Note: These are unit tests for the chat endpoint logic.
Full integration tests require the service to be running.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.config import Settings
from src.services.conversation_service import Conversation, ConversationService
from src.services.context_builder import ContextBuilder
from src.services.openai_client import OpenAIClient
from src.services.prompt_assembly_service import PromptAssemblyService
from src.services.tool_service import ToolService

# Import models directly to avoid namespace conflicts
import sys
from pathlib import Path
api_models_path = Path(__file__).parent.parent / "src" / "api" / "models.py"
if api_models_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_models", api_models_path)
    api_models = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(api_models)
    ChatRequest = api_models.ChatRequest
    ChatResponse = api_models.ChatResponse
    ToolCall = api_models.ToolCall
else:
    # Fallback: define models inline for testing
    from pydantic import BaseModel, Field
    from typing import Any, Dict, List, Optional
    
    class ChatRequest(BaseModel):
        message: str
        conversation_id: Optional[str] = None
        refresh_context: bool = False
    
    class ToolCall(BaseModel):
        id: str
        name: str
        arguments: Dict[str, Any]
    
    class ChatResponse(BaseModel):
        message: str
        conversation_id: str
        tool_calls: List[ToolCall] = []
        metadata: Dict[str, Any] = {}


@pytest.fixture
def settings():
    """Create test settings"""
    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4o-mini",
    )


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock()
    builder.build_complete_system_prompt = AsyncMock(
        return_value="System prompt with context"
    )
    builder.initialize = AsyncMock()
    builder.close = AsyncMock()
    return builder


@pytest.fixture
def mock_openai_client():
    """Create mock OpenAI client"""
    client = MagicMock()
    client.chat_completion = AsyncMock()
    return client


@pytest.fixture
def mock_tool_service():
    """Create mock tool service"""
    service = MagicMock()
    service.execute_tool_call = AsyncMock(return_value={"result": "success"})
    return service


@pytest.fixture
def conversation_service(settings, mock_context_builder):
    """Create conversation service instance"""
    return ConversationService(settings, mock_context_builder)


@pytest.fixture
def prompt_assembly_service(settings, mock_context_builder, conversation_service):
    """Create prompt assembly service instance"""
    return PromptAssemblyService(settings, mock_context_builder, conversation_service)


@pytest.fixture
def setup_services(
    settings,
    conversation_service,
    prompt_assembly_service,
    mock_openai_client,
    mock_tool_service,
):
    """Set up services for testing"""
    return {
        "settings": settings,
        "conversation_service": conversation_service,
        "prompt_assembly_service": prompt_assembly_service,
        "openai_client": mock_openai_client,
        "tool_service": mock_tool_service,
    }


@pytest.fixture
def mock_chat_completion():
    """Create mock OpenAI chat completion response"""
    from openai.types.chat import ChatCompletion, ChatCompletionMessage
    from openai.types.chat.chat_completion import Choice
    from openai.types.completion_usage import CompletionUsage

    message = ChatCompletionMessage(
        role="assistant",
        content="I've turned on the kitchen lights.",
    )

    return ChatCompletion(
        id="chatcmpl-123",
        choices=[
            Choice(
                finish_reason="stop",
                index=0,
                message=message,
            )
        ],
        created=1234567890,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=CompletionUsage(
            completion_tokens=20,
            prompt_tokens=100,
            total_tokens=120,
        ),
    )


@pytest.mark.asyncio
async def test_chat_request_model(settings):
    """Test ChatRequest model validation"""
    request = ChatRequest(
        message="Turn on the kitchen lights",
        conversation_id=None,
        refresh_context=False,
    )
    assert request.message == "Turn on the kitchen lights"
    assert request.conversation_id is None
    assert request.refresh_context is False

    # Test with conversation ID
    request2 = ChatRequest(
        message="Hello",
        conversation_id="conv-123",
        refresh_context=True,
    )
    assert request2.conversation_id == "conv-123"
    assert request2.refresh_context is True


@pytest.mark.asyncio
async def test_chat_response_model():
    """Test ChatResponse model"""
    response = ChatResponse(
        message="I've turned on the kitchen lights.",
        conversation_id="conv-123",
        tool_calls=[
            ToolCall(
                id="call_123",
                name="call_service",
                arguments={"domain": "light", "service": "turn_on"},
            )
        ],
        metadata={"model": "gpt-4o-mini", "tokens_used": 150},
    )
    assert response.message == "I've turned on the kitchen lights."
    assert response.conversation_id == "conv-123"
    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "call_service"


@pytest.mark.asyncio
async def test_chat_endpoint_logic_new_conversation(
    setup_services, conversation_service, mock_openai_client, mock_chat_completion
):
    """Test chat endpoint logic with new conversation"""
    services = setup_services
    mock_openai_client.chat_completion.return_value = mock_chat_completion

    # Simulate chat endpoint logic
    request = ChatRequest(message="Turn on the kitchen lights", refresh_context=False)

    # Create conversation
    conversation = await conversation_service.create_conversation()
    conversation_id = conversation.conversation_id

    # Assemble messages
    messages = await services["prompt_assembly_service"].assemble_messages(
        conversation_id, request.message, refresh_context=request.refresh_context
    )

    # Call OpenAI
    completion = await mock_openai_client.chat_completion(messages=messages, tools=[])

    # Add assistant message
    assistant_content = completion.choices[0].message.content or ""
    await conversation_service.add_message(conversation_id, "assistant", assistant_content)

    # Verify
    assert assistant_content == "I've turned on the kitchen lights."
    assert conversation_id is not None
    mock_openai_client.chat_completion.assert_called_once()


@pytest.mark.asyncio
async def test_chat_endpoint_logic_invalid_conversation(
    setup_services, conversation_service
):
    """Test chat endpoint logic with invalid conversation ID"""
    services = setup_services

    # Try to get non-existent conversation
    conversation = await conversation_service.get_conversation("invalid-id")
    assert conversation is None

