"""
History Manager

Manages conversation history and context.
Tracks turns, entities, and accumulated information.

Created: Phase 2 - Core Service Refactoring
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class HistoryManager:
    """
    Manages conversation history and context.
    
    Handles:
    - Loading conversation history from database
    - Building context from history
    - Managing turn sequences
    """

    def __init__(self):
        """Initialize history manager"""
        logger.info("HistoryManager initialized")

    async def get_conversation_history(
        self,
        conversation_id: str,
        db: AsyncSession,
        limit: int | None = None
    ) -> list[dict[str, Any]]:
        """
        Get conversation history from database.
        
        Args:
            conversation_id: Conversation ID
            db: Database session
            limit: Optional limit on number of turns
        
        Returns:
            List of conversation turns
        """
        try:
            # Query conversation_turns table
            from sqlalchemy import text

            query = text("""
                SELECT * FROM conversation_turns
                WHERE conversation_id = :conversation_id
                ORDER BY turn_number ASC
                LIMIT :limit
            """)

            result = await db.execute(
                query,
                {"conversation_id": conversation_id, "limit": limit or 100}
            )

            turns = []
            for row in result:
                turns.append({
                    "id": row.id,
                    "conversation_id": row.conversation_id,
                    "turn_number": row.turn_number,
                    "role": row.role,
                    "content": row.content,
                    "response_type": row.response_type,
                    "intent": row.intent,
                    "extracted_entities": row.extracted_entities,
                    "confidence": row.confidence,
                    "processing_time_ms": row.processing_time_ms,
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })

            logger.info(f"Loaded {len(turns)} turns for conversation {conversation_id}")
            return turns

        except Exception as e:
            logger.error(f"Failed to load conversation history: {e}", exc_info=True)
            return []

    def build_context_from_history(
        self,
        history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Build context from conversation history.
        
        Args:
            history: List of conversation turns
        
        Returns:
            Context dictionary
        """
        if not history:
            return {}

        # Extract entities from all turns
        all_entities = []
        validated_entities = {}

        for turn in history:
            if turn.get("extracted_entities"):
                entities = turn["extracted_entities"]
                if isinstance(entities, list):
                    all_entities.extend(entities)
                elif isinstance(entities, dict):
                    all_entities.append(entities)

        # Build context
        context = {
            "turn_count": len(history),
            "entities": all_entities,
            "validated_entities": validated_entities,
            "last_turn": history[-1] if history else None,
            "first_query": history[0].get("content") if history else None
        }

        return context

