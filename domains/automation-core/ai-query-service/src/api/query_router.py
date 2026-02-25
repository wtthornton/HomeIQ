"""
Query Router - Natural Language Query Interface

Epic 39, Story 39.10: Query Service Implementation
Wired to QueryProcessor and backed by AskAIQuery / ClarificationSession models.

This router handles:
- POST /query - Process natural language queries
- GET /query/{query_id}/suggestions - Get query suggestions
- POST /query/{query_id}/refine - Refine query results
"""

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..database.models import AskAIQuery
from ..services.clarification.service import ClarificationService
from ..services.query.processor import QueryProcessor
from ..services.suggestion.generator import SuggestionGenerator

logger = logging.getLogger(__name__)


def _build_processor() -> QueryProcessor:
    """Build a fully-wired :class:`QueryProcessor`.

    Injects :class:`ClarificationService` (always available -- pure logic)
    and :class:`SuggestionGenerator` (uses OpenAI when configured, keyword
    fallback otherwise).
    """
    # OpenAI client -- only created when an API key is configured
    openai_client = None
    if settings.openai_api_key:
        try:
            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI(
                api_key=settings.openai_api_key,
                timeout=settings.openai_timeout,
            )
        except Exception:
            logger.warning("Failed to initialise OpenAI client", exc_info=True)

    clarification_service = ClarificationService()
    suggestion_generator = SuggestionGenerator(openai_client=openai_client)

    return QueryProcessor(
        clarification_service=clarification_service,
        suggestion_generator=suggestion_generator,
    )

# Pattern to strip control characters from user input before logging
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def _sanitize_for_log(text: str, max_length: int = 100) -> str:
    """Strip control characters and truncate user input for safe logging."""
    return _CONTROL_CHAR_RE.sub("", text)[:max_length]


router = APIRouter(prefix="/api/v1", tags=["Query"])


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """Request for natural language query processing."""

    query: str = Field(..., description="Natural language query", max_length=500)
    user_id: str | None = Field(None, description="User ID for personalization")
    context: dict | None = Field(None, description="Additional context")


class RefineRequest(BaseModel):
    """Request for refining query results based on user feedback."""

    feedback: str | None = Field(None, description="User feedback text", max_length=500)
    selected_entities: list[str] = Field(
        default_factory=list, description="User-selected entity IDs",
    )
    additional_context: dict | None = Field(
        None, description="Additional refinement context",
    )


class QueryResponse(BaseModel):
    """Response for query processing."""

    query_id: str
    status: str
    message: str
    suggestions: list[dict] = Field(default_factory=list)
    entities: list[dict] = Field(default_factory=list)
    confidence_score: float | None = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/query", response_model=QueryResponse, status_code=status.HTTP_201_CREATED)
async def process_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db),
) -> QueryResponse:
    """
    Process natural language query and generate automation suggestions.

    Creates a persistent AskAIQuery record, delegates processing to
    QueryProcessor, and updates the record with results.
    """
    logger.info("[QUERY] Processing query: %s...", _sanitize_for_log(request.query))

    # Create database record
    query_record = AskAIQuery(
        user_query=request.query,
        status="pending",
    )
    db.add(query_record)
    await db.flush()  # Populate id without committing

    try:
        # Process query via QueryProcessor (with wired services)
        query_record.status = "processing"
        processor = _build_processor()
        result = await processor.process_query(
            query=request.query,
            user_id=request.user_id,
            db=db,
        )

        # Update record with results
        query_record.status = "complete"
        query_record.entities = result.get("extracted_entities", [])
        query_record.suggestions = result.get("suggestions", [])
        query_record.confidence_score = result.get("confidence")

        return QueryResponse(
            query_id=query_record.id,
            status="complete",
            message=result.get("message", "Query processed successfully."),
            suggestions=result.get("suggestions", []),
            entities=result.get("extracted_entities", []),
            confidence_score=result.get("confidence"),
        )

    except Exception:
        query_record.status = "failed"
        logger.exception("Failed to process query %s", query_record.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the query.",
        ) from None


@router.get("/query/{query_id}/suggestions")
async def get_query_suggestions(
    query_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get all suggestions for a specific query."""
    logger.info("Getting suggestions for query: %s", query_id)

    result = await db.execute(
        select(AskAIQuery).where(AskAIQuery.id == query_id),
    )
    query_record = result.scalar_one_or_none()

    if not query_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found.",
        )

    suggestions = query_record.suggestions or []
    return {
        "query_id": query_id,
        "suggestions": suggestions,
        "total_count": len(suggestions),
        "status": query_record.status,
    }


@router.post("/query/{query_id}/refine")
async def refine_query(
    query_id: str,
    refinement: RefineRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Refine query results based on user feedback."""
    logger.info("Refining query: %s", query_id)

    result = await db.execute(
        select(AskAIQuery).where(AskAIQuery.id == query_id),
    )
    query_record = result.scalar_one_or_none()

    if not query_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Query {query_id} not found.",
        )

    try:
        # Build refined query from original + feedback
        refined_query = query_record.user_query
        if refinement.feedback:
            refined_query = f"{refined_query} ({refinement.feedback})"

        # Re-process with additional context (with wired services)
        query_record.status = "processing"
        processor = _build_processor()
        refined_result = await processor.process_query(
            query=refined_query,
            db=db,
        )

        # Update record with refined results
        query_record.status = "complete"
        query_record.entities = refined_result.get("extracted_entities", [])
        query_record.suggestions = refined_result.get("suggestions", [])
        query_record.confidence_score = refined_result.get("confidence")

        return {
            "query_id": query_id,
            "status": "complete",
            "message": refined_result.get("message", "Query refined successfully."),
            "suggestions": refined_result.get("suggestions", []),
            "entities": refined_result.get("extracted_entities", []),
            "confidence_score": refined_result.get("confidence"),
        }

    except Exception:
        query_record.status = "failed"
        logger.exception("Failed to refine query %s", query_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while refining the query.",
        ) from None
