"""
Query Router - Natural Language Query Interface

Epic 39, Story 39.9: Query Service Foundation
Extracted from ai-automation-service for low-latency query processing.

This router handles:
- POST /query - Process natural language queries
- POST /clarify - Clarification endpoints
- GET /query/{query_id}/suggestions - Get query suggestions
- POST /query/{query_id}/refine - Refine query results

Note: This is a foundation implementation. Full extraction from ask_ai_router.py
will be completed in Story 39.10.
"""

import logging
import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

logger = logging.getLogger(__name__)

# Pattern to strip control characters (newlines, tabs, ANSI escapes) from user input before logging
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize_for_log(text: str, max_length: int = 100) -> str:
    """Strip control characters and truncate user input for safe logging."""
    return _CONTROL_CHAR_RE.sub("", text)[:max_length]

router = APIRouter(prefix="/api/v1", tags=["Query"])


# Request/Response Models
class QueryRequest(BaseModel):
    """Request for natural language query processing"""
    query: str = Field(..., description="Natural language query", max_length=500)
    user_id: str | None = Field(None, description="User ID for personalization")
    context: dict | None = Field(None, description="Additional context")


class RefineRequest(BaseModel):
    """Request for refining query results based on user feedback"""
    feedback: str | None = Field(None, description="User feedback text", max_length=500)
    selected_entities: list[str] = Field(default_factory=list, description="User-selected entity IDs")
    additional_context: dict | None = Field(None, description="Additional refinement context")


class QueryResponse(BaseModel):
    """Response for query processing"""
    query_id: str
    status: str
    message: str
    suggestions: list[dict] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)


@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
async def process_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
) -> QueryResponse:
    """
    Process natural language query and generate automation suggestions.
    
    This is the main endpoint for the Ask AI tab.
    
    Note: Full implementation will be migrated from ask_ai_router.py in Story 39.10.
    """
    logger.info(f"[QUERY] Processing query: {_sanitize_for_log(request.query)}...")
    
    # TODO: Story 39.10 - Full implementation
    # - Entity extraction using UnifiedExtractionPipeline
    # - Clarification detection
    # - Suggestion generation
    # - Response optimization for <500ms P95 latency
    
    # Placeholder response
    return QueryResponse(
        query_id=f"query-{uuid.uuid4().hex[:8]}",
        status="pending",
        message="Query service foundation created. Full implementation in Story 39.10.",
        suggestions=[],
        entities=[]
    )


@router.get("/query/{query_id}/suggestions")
async def get_query_suggestions(
    query_id: str,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Get all suggestions for a specific query.
    
    Note: Full implementation will be migrated from ask_ai_router.py in Story 39.10.
    """
    logger.info(f"📋 Getting suggestions for query: {query_id}")
    
    # TODO: Story 39.10 - Full implementation
    return {
        "query_id": query_id,
        "suggestions": [],
        "total_count": 0,
        "status": "pending"
    }


@router.post("/query/{query_id}/refine")
async def refine_query(
    query_id: str,
    refinement: RefineRequest,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Refine query results based on user feedback.
    
    Note: Full implementation will be migrated from ask_ai_router.py in Story 39.10.
    """
    logger.info(f"✏️ Refining query: {query_id}")
    
    # TODO: Story 39.10 - Full implementation
    return {
        "query_id": query_id,
        "status": "pending",
        "message": "Refinement endpoint - implementation in Story 39.10"
    }

