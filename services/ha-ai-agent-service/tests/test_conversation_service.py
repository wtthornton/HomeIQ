"""
Unit tests for Conversation Service
Epic AI-20 Story AI20.2
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.config import Settings
from src.services.conversation_service import (
    Conversation,
    ConversationService,
    ConversationState,
    Message,
    is_generic_welcome_message,
)


@pytest.fixture
def settings():
    """Create test settings"""
    return Settings()


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock()
    builder.build_complete_system_prompt = AsyncMock(
        return_value="System prompt with context"
    )
    return builder


@pytest.fixture
def conversation_service(settings, mock_context_builder):
    """Create conversation service instance"""
    return ConversationService(settings, mock_context_builder)


@pytest.mark.asyncio
async def test_create_conversation(conversation_service):
    """Test creating a new conversation"""
    conversation = await conversation_service.create_conversation()
    assert conversation is not None
    assert conversation.conversation_id is not None
    assert conversation.state == ConversationState.ACTIVE
    assert conversation.message_count == 0


@pytest.mark.asyncio
async def test_create_conversation_with_id(conversation_service):
    """Test creating a conversation with specific ID"""
    conversation = await conversation_service.create_conversation(
        conversation_id="test-id-123"
    )
    assert conversation.conversation_id == "test-id-123"
    assert await conversation_service.get_conversation("test-id-123") == conversation


@pytest.mark.asyncio
async def test_get_conversation(conversation_service):
    """Test getting a conversation"""
    conversation = await conversation_service.create_conversation()
    retrieved = await conversation_service.get_conversation(conversation.conversation_id)
    assert retrieved == conversation


@pytest.mark.asyncio
async def test_get_conversation_not_found(conversation_service):
    """Test getting a non-existent conversation"""
    result = await conversation_service.get_conversation("non-existent")
    assert result is None


@pytest.mark.asyncio
async def test_add_message(conversation_service):
    """Test adding a message to a conversation"""
    conversation = await conversation_service.create_conversation()
    message = await conversation_service.add_message(
        conversation.conversation_id, "user", "Hello, agent!"
    )
    assert message is not None
    assert message.role == "user"
    assert message.content == "Hello, agent!"
    assert conversation.message_count == 1


@pytest.mark.asyncio
async def test_add_message_to_nonexistent_conversation(conversation_service):
    """Test adding a message to a non-existent conversation"""
    message = await conversation_service.add_message(
        "non-existent", "user", "Hello!"
    )
    assert message is None


@pytest.mark.asyncio
async def test_get_messages(conversation_service):
    """Test getting messages from a conversation"""
    conversation = await conversation_service.create_conversation()
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Hello!"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "assistant", "Hi there!"
    )

    messages = await conversation_service.get_messages(conversation.conversation_id)
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"


@pytest.mark.asyncio
async def test_get_messages_nonexistent_conversation(conversation_service):
    """Test getting messages from a non-existent conversation"""
    messages = await conversation_service.get_messages("non-existent")
    assert messages == []


@pytest.mark.asyncio
async def test_get_openai_messages(conversation_service, mock_context_builder):
    """Test getting messages in OpenAI format"""
    conversation = await conversation_service.create_conversation()
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Hello!"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "assistant", "Hi there!"
    )

    messages = await conversation_service.get_openai_messages(
        conversation.conversation_id, include_system=True
    )
    assert len(messages) == 3  # system + user + assistant
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[2]["role"] == "assistant"
    mock_context_builder.build_complete_system_prompt.assert_called_once()


@pytest.mark.asyncio
async def test_get_openai_messages_without_system(conversation_service):
    """Test getting OpenAI messages without system prompt"""
    conversation = await conversation_service.create_conversation()
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Hello!"
    )

    messages = await conversation_service.get_openai_messages(
        conversation.conversation_id, include_system=False
    )
    assert len(messages) == 1
    assert messages[0]["role"] == "user"


@pytest.mark.asyncio
async def test_list_conversations(conversation_service):
    """Test listing conversations"""
    conv1 = await conversation_service.create_conversation()
    conv2 = await conversation_service.create_conversation()
    conv3 = await conversation_service.create_conversation()

    conversations = await conversation_service.list_conversations()
    assert len(conversations) == 3
    assert conv1 in conversations
    assert conv2 in conversations
    assert conv3 in conversations


@pytest.mark.asyncio
async def test_list_conversations_with_state_filter(conversation_service):
    """Test listing conversations with state filter"""
    conv1 = await conversation_service.create_conversation()
    conv2 = await conversation_service.create_conversation()
    await conversation_service.archive_conversation(conv2.conversation_id)

    active = await conversation_service.list_conversations(
        state=ConversationState.ACTIVE
    )
    archived = await conversation_service.list_conversations(
        state=ConversationState.ARCHIVED
    )

    assert len(active) == 1
    assert conv1 in active
    assert len(archived) == 1
    assert conv2 in archived


@pytest.mark.asyncio
async def test_list_conversations_with_pagination(conversation_service):
    """Test listing conversations with pagination"""
    # Create 5 conversations
    conversations = []
    for i in range(5):
        conv = await conversation_service.create_conversation()
        conversations.append(conv)

    # Get first 2
    first_page = await conversation_service.list_conversations(limit=2, offset=0)
    assert len(first_page) == 2

    # Get next 2
    second_page = await conversation_service.list_conversations(limit=2, offset=2)
    assert len(second_page) == 2

    # Verify no overlap
    assert first_page[0] != second_page[0]


@pytest.mark.asyncio
async def test_delete_conversation(conversation_service):
    """Test deleting a conversation"""
    conversation = await conversation_service.create_conversation()
    conversation_id = conversation.conversation_id

    result = await conversation_service.delete_conversation(conversation_id)
    assert result is True
    assert await conversation_service.get_conversation(conversation_id) is None


@pytest.mark.asyncio
async def test_delete_nonexistent_conversation(conversation_service):
    """Test deleting a non-existent conversation"""
    result = await conversation_service.delete_conversation("non-existent")
    assert result is False


@pytest.mark.asyncio
async def test_archive_conversation(conversation_service):
    """Test archiving a conversation"""
    conversation = await conversation_service.create_conversation()
    assert conversation.state == ConversationState.ACTIVE

    result = await conversation_service.archive_conversation(conversation.conversation_id)
    assert result is True
    assert conversation.state == ConversationState.ARCHIVED


@pytest.mark.asyncio
async def test_activate_conversation(conversation_service):
    """Test activating an archived conversation"""
    conversation = await conversation_service.create_conversation()
    await conversation_service.archive_conversation(conversation.conversation_id)
    assert conversation.state == ConversationState.ARCHIVED

    result = await conversation_service.activate_conversation(conversation.conversation_id)
    assert result is True
    assert conversation.state == ConversationState.ACTIVE


@pytest.mark.asyncio
async def test_conversation_message_ordering(conversation_service):
    """Test that messages are ordered correctly"""
    conversation = await conversation_service.create_conversation()
    await conversation_service.add_message(
        conversation.conversation_id, "user", "First"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "assistant", "Second"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Third"
    )

    messages = await conversation_service.get_messages(conversation.conversation_id)
    assert len(messages) == 3
    assert messages[0].content == "First"
    assert messages[1].content == "Second"
    assert messages[2].content == "Third"


@pytest.mark.asyncio
async def test_conversation_context_caching(conversation_service, mock_context_builder):
    """Test that context is cached and reused"""
    conversation = await conversation_service.create_conversation()

    # First call should build context
    messages1 = await conversation_service.get_openai_messages(
        conversation.conversation_id, include_system=True
    )
    assert mock_context_builder.build_complete_system_prompt.call_count == 1

    # Second call should use cached context
    messages2 = await conversation_service.get_openai_messages(
        conversation.conversation_id, include_system=True
    )
    assert mock_context_builder.build_complete_system_prompt.call_count == 1  # Still 1


@pytest.mark.asyncio
async def test_message_to_dict(conversation_service):
    """Test message serialization"""
    conversation = await conversation_service.create_conversation()
    message = await conversation_service.add_message(
        conversation.conversation_id, "user", "Test message"
    )

    message_dict = message.to_dict()
    assert message_dict["role"] == "user"
    assert message_dict["content"] == "Test message"
    assert "message_id" in message_dict
    assert "created_at" in message_dict


@pytest.mark.asyncio
async def test_conversation_to_dict(conversation_service):
    """Test conversation serialization"""
    conversation = await conversation_service.create_conversation()
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Test"
    )

    conv_dict = conversation.to_dict()
    assert conv_dict["conversation_id"] == conversation.conversation_id
    assert conv_dict["state"] == ConversationState.ACTIVE.value
    assert conv_dict["message_count"] == 1
    assert len(conv_dict["messages"]) == 1


# Tests for is_generic_welcome_message function
def test_is_generic_welcome_message_detects_generic_messages():
    """Test that generic welcome messages are detected"""
    generic_messages = [
        "How can I assist you with your Home Assistant automations today?",
        "What can I help you with?",
        "I'm here to help you with your automations.",
        "How can I help you?",
        "What would you like to do?",
    ]
    
    for msg in generic_messages:
        assert is_generic_welcome_message(msg), f"Should detect generic message: {msg}"


def test_is_generic_welcome_message_rejects_specific_responses():
    """Test that specific, non-generic messages are not detected as generic"""
    specific_messages = [
        "I've created an automation that makes the office lights blink red every 15 minutes.",
        "The automation has been created successfully with ID abc123.",
        "I found 3 lights in the office area.",
        "Here's the YAML for your automation:",
        "The office lights are currently off.",
    ]
    
    for msg in specific_messages:
        assert not is_generic_welcome_message(msg), f"Should not detect as generic: {msg}"


def test_is_generic_welcome_message_handles_empty_strings():
    """Test that empty strings are not detected as generic"""
    assert not is_generic_welcome_message("")
    assert not is_generic_welcome_message("   ")
    assert not is_generic_welcome_message(None)  # type: ignore


def test_is_generic_welcome_message_case_insensitive():
    """Test that detection is case-insensitive"""
    assert is_generic_welcome_message("HOW CAN I ASSIST YOU?")
    assert is_generic_welcome_message("how can i help you")
    assert is_generic_welcome_message("How Can I Assist You Today?")

