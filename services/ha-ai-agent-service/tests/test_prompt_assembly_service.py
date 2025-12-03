"""
Unit tests for Prompt Assembly Service
Epic AI-20 Story AI20.3
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.config import Settings
from src.services.conversation_service import Conversation, ConversationService
from src.services.context_builder import ContextBuilder
from src.services.prompt_assembly_service import PromptAssemblyService


@pytest.fixture
def settings():
    """Create test settings"""
    return Settings(openai_model="gpt-4o-mini")


@pytest.fixture
def mock_context_builder():
    """Create mock context builder"""
    builder = MagicMock()
    builder.build_complete_system_prompt = AsyncMock(
        return_value="System prompt with Tier 1 context"
    )
    return builder


@pytest.fixture
def conversation_service(settings, mock_context_builder):
    """Create conversation service instance"""
    return ConversationService(settings, mock_context_builder)


@pytest.fixture
def prompt_assembly_service(settings, mock_context_builder, conversation_service):
    """Create prompt assembly service instance"""
    return PromptAssemblyService(settings, mock_context_builder, conversation_service)


@pytest.mark.asyncio
async def test_assemble_messages_basic(prompt_assembly_service, conversation_service):
    """Test basic message assembly"""
    conversation = await conversation_service.create_conversation()

    messages = await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "Hello, agent!"
    )

    assert len(messages) >= 2  # system + user
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "Hello, agent!"


@pytest.mark.asyncio
async def test_assemble_messages_with_history(
    prompt_assembly_service, conversation_service
):
    """Test message assembly with conversation history"""
    conversation = await conversation_service.create_conversation()

    # Add some history
    await conversation_service.add_message(
        conversation.conversation_id, "user", "First message"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "assistant", "First response"
    )

    # Add new message
    messages = await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "Second message"
    )

    assert len(messages) == 4  # system + user + assistant + user
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "First message"
    assert messages[2]["role"] == "assistant"
    assert messages[3]["role"] == "user"
    assert messages[3]["content"] == "Second message"


@pytest.mark.asyncio
async def test_assemble_messages_refresh_context(
    prompt_assembly_service, mock_context_builder, conversation_service
):
    """Test that context refresh works"""
    conversation = await conversation_service.create_conversation()

    # First call - should build context
    await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "Hello!", refresh_context=False
    )
    assert mock_context_builder.build_complete_system_prompt.call_count == 1

    # Second call with refresh=True - should rebuild context
    await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "Hello again!", refresh_context=True
    )
    assert mock_context_builder.build_complete_system_prompt.call_count == 2


@pytest.mark.asyncio
async def test_assemble_messages_uses_cached_context(
    prompt_assembly_service, mock_context_builder, conversation_service
):
    """Test that cached context is used when available"""
    conversation = await conversation_service.create_conversation()

    # First call - should build context
    await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "Hello!", refresh_context=False
    )
    assert mock_context_builder.build_complete_system_prompt.call_count == 1

    # Second call without refresh - should use cache
    await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "Hello again!", refresh_context=False
    )
    assert mock_context_builder.build_complete_system_prompt.call_count == 1  # Still 1


@pytest.mark.asyncio
async def test_token_budget_enforcement(
    prompt_assembly_service, conversation_service
):
    """Test that token budget is enforced by truncating history"""
    conversation = await conversation_service.create_conversation()

    # Add many large messages to exceed token budget
    # Each message is large enough to exceed budget when combined
    large_message = "This is a large message. " * 100  # ~2500 chars per message
    for i in range(50):
        await conversation_service.add_message(
            conversation.conversation_id, "user", f"{large_message} Message {i}"
        )
        await conversation_service.add_message(
            conversation.conversation_id, "assistant", f"{large_message} Response {i}"
        )

    # Check token count before assembly
    counts_before = await prompt_assembly_service.get_token_count(
        conversation.conversation_id, include_new_message="New message"
    )

    # Assemble messages - should truncate history if needed
    messages = await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "New message"
    )

    # Verify structure
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == "New message"

    # If token budget was exceeded, messages should be truncated
    if not counts_before["within_budget"]:
        # Should have fewer messages than original (system + 100 + new = 102)
        assert len(messages) < 102


@pytest.mark.asyncio
async def test_get_token_count(prompt_assembly_service, conversation_service):
    """Test token count retrieval"""
    conversation = await conversation_service.create_conversation()
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Test message"
    )

    counts = await prompt_assembly_service.get_token_count(conversation.conversation_id)

    assert "system_tokens" in counts
    assert "history_tokens" in counts
    assert "new_message_tokens" in counts
    assert "total_tokens" in counts
    assert "max_input_tokens" in counts
    assert "within_budget" in counts
    assert counts["system_tokens"] > 0
    assert counts["history_tokens"] > 0
    assert counts["total_tokens"] > 0


@pytest.mark.asyncio
async def test_get_token_count_with_new_message(
    prompt_assembly_service, conversation_service
):
    """Test token count with new message included"""
    conversation = await conversation_service.create_conversation()

    counts = await prompt_assembly_service.get_token_count(
        conversation.conversation_id, include_new_message="New user message"
    )

    assert counts["new_message_tokens"] > 0
    assert counts["total_tokens"] > counts["system_tokens"]


@pytest.mark.asyncio
async def test_get_token_count_nonexistent_conversation(prompt_assembly_service):
    """Test token count for non-existent conversation"""
    with pytest.raises(ValueError, match="not found"):
        await prompt_assembly_service.get_token_count("non-existent")


@pytest.mark.asyncio
async def test_assemble_messages_nonexistent_conversation(prompt_assembly_service):
    """Test assembling messages for non-existent conversation"""
    with pytest.raises(ValueError, match="not found"):
        await prompt_assembly_service.assemble_messages("non-existent", "Hello!")


@pytest.mark.asyncio
async def test_message_ordering_preserved(
    prompt_assembly_service, conversation_service
):
    """Test that message ordering is preserved"""
    conversation = await conversation_service.create_conversation()

    # Add messages in order
    await conversation_service.add_message(
        conversation.conversation_id, "user", "First"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "assistant", "Response 1"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "user", "Second"
    )
    await conversation_service.add_message(
        conversation.conversation_id, "assistant", "Response 2"
    )

    messages = await prompt_assembly_service.assemble_messages(
        conversation.conversation_id, "Third"
    )

    # Check ordering (system is first, new message is last)
    assert messages[0]["role"] == "system"
    assert messages[1]["content"] == "First"
    assert messages[2]["content"] == "Response 1"
    assert messages[3]["content"] == "Second"
    assert messages[4]["content"] == "Response 2"
    assert messages[5]["content"] == "Third"

