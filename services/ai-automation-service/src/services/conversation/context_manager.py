"""
Conversation Context Manager

Manages conversation context across multiple turns.
Tracks conversation state, entities, and accumulated context.

Created: Phase 2 - Core Service Refactoring
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


class ConversationContext:
    """Represents conversation context for a single conversation"""

    def __init__(self, conversation_id: str, user_id: str, initial_query: str):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.initial_query = initial_query
        self.turns: list[dict[str, Any]] = []
        self.entities: list[dict[str, Any]] = []
        self.validated_entities: dict[str, str] = {}
        self.ambiguities: list[dict[str, Any]] = []
        self.clarification_answers: list[dict[str, Any]] = []
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def add_turn(self, turn: dict[str, Any]):
        """Add a conversation turn"""
        self.turns.append(turn)
        self.updated_at = datetime.utcnow()

    def update_entities(self, entities: list[dict[str, Any]]):
        """Update entities in context"""
        self.entities = entities
        self.updated_at = datetime.utcnow()

    def update_validated_entities(self, validated: dict[str, str]):
        """Update validated entity mappings"""
        self.validated_entities.update(validated)
        self.updated_at = datetime.utcnow()


class ConversationContextManager:
    """
    Manages conversation context across multiple turns.
    
    Tracks:
    - Conversation history
    - Extracted entities
    - Validated entity mappings
    - Clarification answers
    - Accumulated context
    """

    def __init__(self):
        """Initialize context manager"""
        self._contexts: dict[str, ConversationContext] = {}
        logger.info("ConversationContextManager initialized")

    def get_context(self, conversation_id: str) -> ConversationContext | None:
        """Get conversation context"""
        return self._contexts.get(conversation_id)

    def create_context(
        self,
        conversation_id: str,
        user_id: str,
        initial_query: str
    ) -> ConversationContext:
        """Create new conversation context"""
        context = ConversationContext(
            conversation_id=conversation_id,
            user_id=user_id,
            initial_query=initial_query
        )
        self._contexts[conversation_id] = context
        logger.info(f"Created context for conversation: {conversation_id}")
        return context

    def update_from_turn(
        self,
        conversation_id: str,
        turn: dict[str, Any]
    ):
        """Update context from conversation turn"""
        context = self.get_context(conversation_id)
        if context:
            context.add_turn(turn)

            # Update entities if present
            if 'extracted_entities' in turn:
                context.update_entities(turn['extracted_entities'])

            # Update validated entities if present
            if 'validated_entities' in turn:
                context.update_validated_entities(turn['validated_entities'])
        else:
            logger.warning(f"Context not found for conversation: {conversation_id}")

    def get_accumulated_context(self, conversation_id: str) -> dict[str, Any]:
        """Get accumulated context for conversation"""
        context = self.get_context(conversation_id)
        if not context:
            return {}

        return {
            "conversation_id": context.conversation_id,
            "user_id": context.user_id,
            "initial_query": context.initial_query,
            "turn_count": len(context.turns),
            "entities": context.entities,
            "validated_entities": context.validated_entities,
            "ambiguities": context.ambiguities,
            "clarification_answers": context.clarification_answers,
            "created_at": context.created_at.isoformat(),
            "updated_at": context.updated_at.isoformat()
        }

    def clear_context(self, conversation_id: str):
        """Clear conversation context"""
        if conversation_id in self._contexts:
            del self._contexts[conversation_id]
            logger.info(f"Cleared context for conversation: {conversation_id}")

