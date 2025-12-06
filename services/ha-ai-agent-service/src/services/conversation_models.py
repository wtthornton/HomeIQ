"""
Conversation Domain Models
Epic AI-20 Story AI20.2: Conversation Service Foundation

Domain models for conversations and messages (separated from service to avoid circular imports).
"""

import logging
from datetime import datetime
from enum import Enum
from uuid import uuid4

logger = logging.getLogger(__name__)


class ConversationState(str, Enum):
    """Conversation state enum"""
    ACTIVE = "active"
    ARCHIVED = "archived"


class Message:
    """Represents a single message in a conversation"""

    def __init__(
        self,
        role: str,
        content: str,
        message_id: str | None = None,
        created_at: datetime | None = None,
    ):
        """
        Initialize a message.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content
            message_id: Optional message ID (generated if not provided)
            created_at: Optional creation timestamp (current time if not provided)
        """
        self.message_id = message_id or str(uuid4())
        self.role = role
        self.content = content
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> dict:
        """Convert message to dictionary"""
        return {
            "message_id": self.message_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
        }

    def to_openai_format(self) -> dict[str, str]:
        """Convert message to OpenAI API format"""
        return {
            "role": self.role,
            "content": self.content,
        }


class Conversation:
    """Represents a conversation with message history and metadata"""

    def __init__(
        self,
        conversation_id: str | None = None,
        created_at: datetime | None = None,
        state: ConversationState = ConversationState.ACTIVE,
        debug_id: str | None = None,
    ):
        """
        Initialize a conversation.

        Args:
            conversation_id: Optional conversation ID (generated if not provided)
            created_at: Optional creation timestamp (current time if not provided)
            state: Conversation state (default: ACTIVE)
            debug_id: Optional unique troubleshooting ID (generated if not provided)
        """
        self.conversation_id = conversation_id or str(uuid4())
        self.debug_id = debug_id or str(uuid4())  # Generate unique troubleshooting ID
        self.created_at = created_at or datetime.now()
        self.updated_at = self.created_at
        self.state = state
        self.messages: list[Message] = []
        self._context_cache: str | None = None
        self._context_updated_at: datetime | None = None
        self._pending_preview: dict | None = None  # 2025 Preview-and-Approval Workflow

    @property
    def message_count(self) -> int:
        """Get total message count"""
        return len(self.messages)

    def add_message(self, role: str, content: str) -> Message:
        """
        Add a message to the conversation.

        Args:
            role: Message role ('user' or 'assistant')
            content: Message content

        Returns:
            Created Message instance
        """
        message = Message(role=role, content=content)
        self.messages.append(message)
        self.updated_at = datetime.now()
        logger.debug(
            f"Added {role} message to conversation {self.conversation_id} "
            f"(total: {self.message_count})"
        )
        return message

    def get_messages(self) -> list[Message]:
        """Get all messages in the conversation"""
        return self.messages.copy()

    def get_openai_messages(self) -> list[dict[str, str]]:
        """Get messages in OpenAI API format"""
        return [msg.to_openai_format() for msg in self.messages]

    def archive(self) -> None:
        """Archive the conversation"""
        self.state = ConversationState.ARCHIVED
        self.updated_at = datetime.now()
        logger.debug(f"Archived conversation {self.conversation_id}")

    def activate(self) -> None:
        """Activate the conversation"""
        self.state = ConversationState.ACTIVE
        self.updated_at = datetime.now()
        logger.debug(f"Activated conversation {self.conversation_id}")

    def to_dict(self) -> dict:
        """Convert conversation to dictionary"""
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "state": self.state.value,
            "message_count": self.message_count,
            "messages": [msg.to_dict() for msg in self.messages],
        }

    def set_context_cache(self, context: str) -> None:
        """
        Cache context for this conversation.

        Args:
            context: Context string to cache
        """
        self._context_cache = context
        self._context_updated_at = datetime.now()

    def get_context_cache(self) -> str | None:
        """Get cached context if available"""
        return self._context_cache

    def set_pending_preview(self, preview: dict) -> None:
        """
        Store pending automation preview.

        Args:
            preview: Preview dictionary from preview_automation_from_prompt tool
        """
        self._pending_preview = preview
        self.updated_at = datetime.now()
        logger.debug(f"Stored pending preview for conversation {self.conversation_id}")

    def get_pending_preview(self) -> dict | None:
        """Get pending automation preview if available"""
        return self._pending_preview

    def clear_pending_preview(self) -> None:
        """Clear pending automation preview"""
        self._pending_preview = None
        self.updated_at = datetime.now()
        logger.debug(f"Cleared pending preview for conversation {self.conversation_id}")

