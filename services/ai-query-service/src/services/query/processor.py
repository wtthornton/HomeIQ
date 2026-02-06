"""
Query Processor Service

Epic 39, Story 39.10: Query Service Migration
Extracts core query processing logic from ask_ai_router.py
"""

import logging
import re
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...config import settings
from ..confidence import calculate_entity_confidence

logger = logging.getLogger(__name__)

# Pattern to strip control characters (newlines, tabs, ANSI escapes) from user input before logging
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize_for_log(text: str, max_length: int = 100) -> str:
    """Strip control characters and truncate user input for safe logging."""
    return _CONTROL_CHAR_RE.sub("", text)[:max_length]


class QueryProcessor:
    """
    Core query processing service.
    
    Handles:
    - Query validation
    - Entity extraction
    - Clarification detection
    - Suggestion generation
    - Response building
    """
    
    def __init__(
        self,
        entity_extractor=None,
        clarification_service=None,
        suggestion_generator=None
    ):
        self.entity_extractor = entity_extractor
        self.clarification_service = clarification_service
        self.suggestion_generator = suggestion_generator
    
    async def process_query(
        self,
        query: str,
        user_id: str | None = None,
        db: AsyncSession | None = None,
        area_filter: str | None = None
    ) -> dict[str, Any]:
        """
        Process a natural language query and generate automation suggestions.
        
        Args:
            query: Natural language query string
            user_id: User ID for personalization
            db: Database session
            area_filter: Optional area filter (e.g., "office" or "office,kitchen")
            
        Returns:
            Dictionary with query_id, entities, suggestions, confidence, etc.
        """
        start_time = datetime.now()
        query_id = f"query-{uuid.uuid4().hex[:8]}"
        
        # Validate query
        if not query or not isinstance(query, str) or not query.strip():
            raise ValueError("Query is required and must be a non-empty string")
        
        if len(query) > settings.max_query_length:
            raise ValueError(f"Query exceeds maximum length of {settings.max_query_length} characters")
        
        logger.info(f"[QUERY] Processing query: {_sanitize_for_log(query)}...")
        
        try:
            # Step 1: Extract entities
            entities = []
            if self.entity_extractor:
                entities = await self.entity_extractor.extract(query, area_filter=area_filter)
                logger.info(f"✅ Extracted {len(entities)} entities")
            
            # Step 2: Check for clarification needs
            clarification_result = None
            if self.clarification_service:
                clarification_result = await self.clarification_service.detect_clarification_needs(
                    query=query,
                    entities=entities,
                    db=db
                )
                logger.info(f"🔍 Clarification check: needed={clarification_result.get('needed', False)}")
            
            # Step 3: Generate suggestions
            suggestions = []
            if self.suggestion_generator:
                suggestions = await self.suggestion_generator.generate(
                    query=query,
                    entities=entities,
                    user_id=user_id,
                    clarification_context=clarification_result,
                    query_id=query_id,
                    area_filter=area_filter,
                    db=db
                )
                logger.info(f"✅ Generated {len(suggestions)} suggestions")
            
            # Step 4: Calculate confidence
            confidence = self._calculate_confidence(entities, suggestions, clarification_result)
            
            # Step 5: Build response
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            
            response = {
                "query_id": query_id,
                "original_query": query,
                "extracted_entities": entities,
                "suggestions": suggestions,
                "confidence": confidence,
                "processing_time_ms": int(processing_time),
                "created_at": datetime.now().isoformat(),
                "clarification_needed": clarification_result.get("needed", False) if clarification_result else False,
                "clarification_session_id": clarification_result.get("session_id") if clarification_result else None,
                "questions": clarification_result.get("questions") if clarification_result else None,
                "message": self._build_message(entities, suggestions, clarification_result)
            }
            
            logger.info(f"✅ Query processed: {len(suggestions)} suggestions, {confidence:.2f} confidence, {processing_time:.0f}ms")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to process query: {e}", exc_info=True)
            raise
    
    def _calculate_confidence(
        self,
        entities: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        clarification_result: dict[str, Any] | None
    ) -> float:
        """Calculate confidence score based on entities, suggestions, and clarification needs."""
        base_confidence = calculate_entity_confidence(entities)

        # Boost based on suggestions
        if suggestions:
            base_confidence = min(0.9, base_confidence + (len(suggestions) * 0.1))

        # Reduce if clarification needed
        if clarification_result and clarification_result.get("needed"):
            base_confidence = max(0.3, base_confidence - 0.2)

        return min(0.95, base_confidence)
    
    def _build_message(
        self,
        entities: list[dict[str, Any]],
        suggestions: list[dict[str, Any]],
        clarification_result: dict[str, Any] | None
    ) -> str:
        """Build user-friendly message based on query results."""
        if clarification_result and clarification_result.get("needed"):
            questions_count = len(clarification_result.get("questions", []))
            if suggestions:
                return f"I've generated {len(suggestions)} preliminary suggestion(s), but please answer {questions_count} question(s) to refine them."
            else:
                return f"Please answer {questions_count} question(s) to help me create the automation accurately."
        elif suggestions:
            device_names = [e.get('name', e.get('friendly_name', '')) for e in entities if e.get('type') == 'device']
            device_info = f" I detected these devices: {', '.join(device_names)}." if device_names else ""
            return f"I found {len(suggestions)} automation suggestion(s) for your request.{device_info}"
        else:
            device_info = " I couldn't identify specific devices." if not entities else ""
            return f"I couldn't generate automation suggestions for your request.{device_info} Please provide more details about the devices and locations you want to use."

