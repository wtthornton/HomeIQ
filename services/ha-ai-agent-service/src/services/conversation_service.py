"""
Conversation Service
Epic AI-20 Story AI20.2: Conversation Service Foundation
Epic AI-20 Story AI20.6: Conversation Persistence

Manages conversation state, message history, and context injection.
Database-backed implementation with SQLite persistence.
"""

import logging
from datetime import datetime

from ..config import Settings
from ..database import get_session
from .context_builder import ContextBuilder
from .conversation_models import Conversation, ConversationState, Message
from .conversation_persistence import (
    add_message as db_add_message,
)
from .conversation_persistence import (
    count_conversations as db_count_conversations,
)
from .conversation_persistence import (
    create_conversation as db_create_conversation,
)
from .conversation_persistence import (
    delete_conversation as db_delete_conversation,
)
from .conversation_persistence import (
    get_conversation as db_get_conversation,
    get_conversation_by_debug_id as db_get_conversation_by_debug_id,
)
from .conversation_persistence import (
    list_conversations as db_list_conversations,
)

logger = logging.getLogger(__name__)


def is_generic_welcome_message(content: str) -> bool:
    """
    Detect if message is a generic welcome message.
    
    Args:
        content: Message content to check
        
    Returns:
        True if message appears to be a generic welcome message
    """
    if not content or not content.strip():
        return False
    
    content_lower = content.lower()
    generic_patterns = [
        "how can i assist you",
        "what can i help you with",
        "i'm here to help",
        "how can i help you",
        "what would you like to do",
        "how can i assist you with your home assistant automations today",
        "i can help you control your home assistant",
    ]
    
    # Check if content matches generic patterns
    matched_pattern = None
    for pattern in generic_patterns:
        if pattern in content_lower:
            matched_pattern = pattern
            # Additional check: if the message is very short and only contains generic text
            if len(content.strip()) < 150:  # Generic messages are usually short
                logger.debug(
                    f"[Generic Detection] Matched pattern '{pattern}' in message "
                    f"(length: {len(content.strip())}). Content: {content[:100]}..."
                )
                return True
    
    # Log if pattern matched but message was too long (might be false positive)
    if matched_pattern:
        logger.debug(
            f"[Generic Detection] Pattern '{matched_pattern}' found but message too long "
            f"({len(content.strip())} chars). Not flagged as generic."
        )
    
    return False


class ConversationService:
    """
    Manages conversations, message history, and context injection.

    Epic AI-20 Story AI20.2: Conversation Service Foundation
    """

    def __init__(self, settings: Settings, context_builder: ContextBuilder):
        """
        Initialize conversation service.

        Args:
            settings: Application settings
            context_builder: ContextBuilder instance for context injection
        """
        self.settings = settings
        self.context_builder = context_builder
        logger.info("✅ Conversation service initialized (database-backed)")

    async def create_conversation(
        self, conversation_id: str | None = None
    ) -> Conversation:
        """
        Create a new conversation.

        Args:
            conversation_id: Optional conversation ID (generated if not provided)

        Returns:
            Created Conversation instance
        """
        async for session in get_session():
            return await db_create_conversation(session, conversation_id)

    async def get_conversation_by_debug_id(self, debug_id: str) -> Conversation | None:
        """Get a conversation by debug_id (troubleshooting ID)"""
        async for session in get_session():
            return await db_get_conversation_by_debug_id(session, debug_id)

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        """
        Get a conversation by ID.

        Args:
            conversation_id: Conversation ID

        Returns:
            Conversation instance or None if not found
        """
        async for session in get_session():
            return await db_get_conversation(session, conversation_id)

    async def list_conversations(
        self,
        state: ConversationState | None = None,
        limit: int | None = None,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[Conversation]:
        """
        List conversations with optional filtering and pagination.

        Args:
            state: Optional state filter (ACTIVE or ARCHIVED)
            limit: Optional limit on number of results
            offset: Offset for pagination
            start_date: Optional filter for conversations created after this date
            end_date: Optional filter for conversations created before this date

        Returns:
            List of Conversation instances
        """
        async for session in get_session():
            return await db_list_conversations(
                session, state, limit, offset, start_date, end_date
            )

    async def count_conversations(
        self,
        state: ConversationState | None = None,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> int:
        """
        Count conversations with optional filtering.

        Args:
            state: Optional state filter (ACTIVE or ARCHIVED)
            start_date: Optional filter for conversations created after this date
            end_date: Optional filter for conversations created before this date

        Returns:
            Number of conversations matching the filters
        """
        async for session in get_session():
            return await db_count_conversations(session, state, start_date, end_date)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if deleted, False if not found
        """
        async for session in get_session():
            return await db_delete_conversation(session, conversation_id)

    async def add_message(
        self, conversation_id: str, role: str, content: str
    ) -> Message | None:
        """
        Add a message to a conversation.

        Args:
            conversation_id: Conversation ID
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            Created Message instance or None if conversation not found
        """
        async for session in get_session():
            return await db_add_message(session, conversation_id, role, content)

    async def get_messages(self, conversation_id: str) -> list[Message]:
        """
        Get all messages for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            List of Message instances (empty if conversation not found)
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return []
        return conversation.get_messages()

    async def get_openai_messages(
        self, conversation_id: str, include_system: bool = True
    ) -> list[dict[str, str]]:
        """
        Get messages in OpenAI API format with optional system prompt.

        Args:
            conversation_id: Conversation ID
            include_system: Whether to include system prompt with context

        Returns:
            List of message dicts in OpenAI format
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return []

        messages = conversation.get_openai_messages()

        # Add system prompt with context if requested
        if include_system:
            system_prompt = await self._get_system_prompt_with_context(conversation)
            messages.insert(0, {"role": "system", "content": system_prompt})

        return messages

    async def _get_system_prompt_with_context(
        self, conversation: Conversation
    ) -> str:
        """
        Get system prompt with context injection for a conversation.

        Uses cached context if available and recent, otherwise rebuilds context.

        Args:
            conversation: Conversation instance

        Returns:
            Complete system prompt with context
        """
        # Check if we should refresh context
        # Refresh if:
        # 1. No cached context exists
        # 2. Context is older than 5 minutes (configurable)
        # 3. Conversation has new messages since last context update

        should_refresh = False
        if not conversation._context_cache:
            should_refresh = True
        elif conversation._context_updated_at:
            # Refresh if context is older than 5 minutes
            age_seconds = (datetime.now() - conversation._context_updated_at).total_seconds()
            if age_seconds > 300:  # 5 minutes
                should_refresh = True

        if should_refresh:
            logger.debug(
                f"Refreshing context for conversation {conversation.conversation_id}"
            )
            context = await self.context_builder.build_complete_system_prompt()
            conversation.set_context_cache(context)
        else:
            logger.debug(
                f"Using cached context for conversation {conversation.conversation_id}"
            )

        return conversation.get_context_cache() or ""

    async def archive_conversation(self, conversation_id: str) -> bool:
        """
        Archive a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if archived, False if not found
        """
        from .conversation_persistence import update_conversation_state
        async for session in get_session():
            return await update_conversation_state(
                session, conversation_id, ConversationState.ARCHIVED
            )

    async def activate_conversation(self, conversation_id: str) -> bool:
        """
        Activate an archived conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if activated, False if not found
        """
        from .conversation_persistence import update_conversation_state
        async for session in get_session():
            return await update_conversation_state(
                session, conversation_id, ConversationState.ACTIVE
            )

    async def set_pending_preview(self, conversation_id: str, preview: dict) -> bool:
        """
        Store pending automation preview for a conversation.

        Args:
            conversation_id: Conversation ID
            preview: Preview dictionary from preview_automation_from_prompt tool

        Returns:
            True if stored, False if conversation not found
        """
        from .conversation_persistence import set_pending_preview
        async for session in get_session():
            result = await set_pending_preview(session, conversation_id, preview)
            if result:
                # Also update in-memory conversation if loaded
                conversation = await self.get_conversation(conversation_id)
                if conversation:
                    conversation.set_pending_preview(preview)
            return result

    async def get_pending_preview(self, conversation_id: str) -> dict | None:
        """
        Get pending automation preview for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            Preview dictionary or None if not found
        """
        conversation = await self.get_conversation(conversation_id)
        if not conversation:
            return None
        return conversation.get_pending_preview()

    async def clear_pending_preview(self, conversation_id: str) -> bool:
        """
        Clear pending automation preview for a conversation.

        Args:
            conversation_id: Conversation ID

        Returns:
            True if cleared, False if conversation not found
        """
        from .conversation_persistence import clear_pending_preview
        async for session in get_session():
            result = await clear_pending_preview(session, conversation_id)
            if result:
                # Also update in-memory conversation if loaded
                conversation = await self.get_conversation(conversation_id)
                if conversation:
                    conversation.clear_pending_preview()
            return result

