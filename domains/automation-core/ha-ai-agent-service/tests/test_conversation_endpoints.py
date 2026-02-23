"""
Unit tests for Conversation Management API Endpoints
Epic AI-20 Story AI20.5 & AI20.6

Tests the ConversationService methods used by the API endpoints.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from src.config import Settings
from src.database import init_database
from src.services.conversation_service import Conversation, ConversationService, ConversationState
from src.services.context_builder import ContextBuilder


@pytest_asyncio.fixture
async def settings():
    """Create test settings with in-memory database"""
    test_settings = Settings(
        database_url="sqlite+aiosqlite:///:memory:"
    )
    # Initialize database
    await init_database(test_settings.database_url)
    return test_settings


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock()
    builder.build_complete_system_prompt = AsyncMock(
        return_value="System prompt with context"
    )
    return builder


@pytest_asyncio.fixture
async def conversation_service(settings, mock_context_builder):
    """Create conversation service instance"""
    return ConversationService(settings, mock_context_builder)


@pytest.mark.asyncio
async def test_list_conversations_empty(conversation_service):
    """Test listing conversations when none exist"""
    conversations = await conversation_service.list_conversations()
    assert len(conversations) == 0
    
    count = await conversation_service.count_conversations()
    assert count == 0


@pytest.mark.asyncio
async def test_list_conversations_with_data(conversation_service):
    """Test listing conversations with data"""
    # Create some conversations
    conv1 = await conversation_service.create_conversation()
    conv2 = await conversation_service.create_conversation()
    conv3 = await conversation_service.create_conversation()
    
    # List all conversations
    conversations = await conversation_service.list_conversations()
    assert len(conversations) == 3
    
    # Count conversations
    count = await conversation_service.count_conversations()
    assert count == 3


@pytest.mark.asyncio
async def test_list_conversations_with_pagination(conversation_service):
    """Test listing conversations with pagination"""
    # Create 5 conversations
    for i in range(5):
        await conversation_service.create_conversation()
    
    # List with limit
    conversations = await conversation_service.list_conversations(limit=2)
    assert len(conversations) == 2
    
    # List with offset
    conversations = await conversation_service.list_conversations(limit=2, offset=2)
    assert len(conversations) == 2


@pytest.mark.asyncio
async def test_list_conversations_with_state_filter(conversation_service):
    """Test listing conversations with state filter"""
    # Create conversations
    conv1 = await conversation_service.create_conversation()
    conv2 = await conversation_service.create_conversation()
    
    # Archive one (using service method)
    await conversation_service.archive_conversation(conv2.conversation_id)
    
    # List active conversations
    active = await conversation_service.list_conversations(state=ConversationState.ACTIVE)
    assert len(active) == 1
    assert active[0].conversation_id == conv1.conversation_id
    
    # List archived conversations
    archived = await conversation_service.list_conversations(state=ConversationState.ARCHIVED)
    assert len(archived) == 1
    assert archived[0].conversation_id == conv2.conversation_id


@pytest.mark.asyncio
async def test_list_conversations_with_date_filter(conversation_service):
    """Test listing conversations with date filter"""
    # Create conversations at different times
    # Note: We can't easily set created_at in the past for new conversations
    # So we'll test with conversations created now and filter by a future date
    now = datetime.now()
    conv1 = await conversation_service.create_conversation()
    conv2 = await conversation_service.create_conversation()
    
    # Filter by start_date in the future (should return empty)
    future = now + timedelta(days=1)
    recent = await conversation_service.list_conversations(
        start_date=future
    )
    assert len(recent) == 0
    
    # Filter by end_date in the past (should return empty)
    past = now - timedelta(days=1)
    old = await conversation_service.list_conversations(
        end_date=past
    )
    assert len(old) == 0
    
    # Filter by date range that includes now (should return both)
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)
    both = await conversation_service.list_conversations(
        start_date=start, end_date=end
    )
    assert len(both) == 2


@pytest.mark.asyncio
async def test_count_conversations(conversation_service):
    """Test counting conversations"""
    # Create conversations
    for i in range(3):
        await conversation_service.create_conversation()
    
    # Count all
    count = await conversation_service.count_conversations()
    assert count == 3
    
    # Count with state filter
    count_active = await conversation_service.count_conversations(
        state=ConversationState.ACTIVE
    )
    assert count_active == 3


@pytest.mark.asyncio
async def test_delete_conversation(conversation_service):
    """Test deleting a conversation"""
    # Create conversation
    conversation = await conversation_service.create_conversation()
    conversation_id = conversation.conversation_id
    
    # Delete it
    result = await conversation_service.delete_conversation(conversation_id)
    assert result is True
    
    # Verify it's gone
    deleted = await conversation_service.get_conversation(conversation_id)
    assert deleted is None
    
    # Try to delete non-existent conversation
    result = await conversation_service.delete_conversation("invalid-id")
    assert result is False


@pytest.mark.asyncio
async def test_create_conversation_with_initial_message(conversation_service):
    """Test creating a conversation with an initial message"""
    # Create conversation
    conversation = await conversation_service.create_conversation()
    
    # Add initial message
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Hello, I need help"
    )
    
    # Get conversation and verify message
    updated = await conversation_service.get_conversation(conversation.conversation_id)
    assert updated is not None
    assert updated.message_count == 1
    assert len(updated.messages) == 1
    assert updated.messages[0].role == "user"
    assert updated.messages[0].content == "Hello, I need help"

