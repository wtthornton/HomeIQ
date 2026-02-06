"""
RAG Router

API endpoints for RAG operations (store, retrieve, search, update).
Following 2025 patterns: dependency injection, async/await, type hints.
"""

import logging
import time
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..api.dependencies import RAGServiceDep
from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rag", tags=["rag"])


# Request/Response models
class StoreRequest(BaseModel):
    """Request model for storing knowledge."""
    text: str = Field(..., description="Text to store", min_length=1, max_length=10000)
    knowledge_type: str = Field(..., description="Knowledge type (e.g., 'query', 'pattern')", min_length=1, max_length=100)
    metadata: dict[str, Any] | None = Field(None, description="Optional metadata")
    success_score: float = Field(0.5, ge=0.0, le=1.0, description="Success score (0.0-1.0)")


class StoreResponse(BaseModel):
    """Response model for store operation."""
    id: int = Field(..., description="Stored entry ID")
    message: str = Field(..., description="Success message")


class RetrieveRequest(BaseModel):
    """Request model for retrieving knowledge."""
    query: str = Field(..., description="Query text", min_length=1, max_length=10000)
    knowledge_type: str | None = Field(None, description="Filter by knowledge type", max_length=100)
    top_k: int = Field(5, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class RetrieveResponse(BaseModel):
    """Response model for retrieve operation."""
    results: list[dict[str, Any]] = Field(..., description="List of similar entries")
    count: int = Field(..., description="Number of results returned")


class SearchRequest(BaseModel):
    """Request model for searching knowledge."""
    query: str = Field(..., description="Query text", min_length=1, max_length=10000)
    filters: dict[str, Any] | None = Field(None, description="Optional filters (supported: knowledge_type)")
    top_k: int = Field(5, ge=1, le=100, description="Number of results to return")
    min_similarity: float = Field(0.7, ge=0.0, le=1.0, description="Minimum similarity threshold")


class SearchResponse(BaseModel):
    """Response model for search operation."""
    results: list[dict[str, Any]] = Field(..., description="List of search results")
    count: int = Field(..., description="Number of results returned")


class UpdateSuccessRequest(BaseModel):
    """Request model for updating success score."""
    score: float = Field(..., ge=0.0, le=1.0, description="New success score (0.0-1.0)")


class UpdateSuccessResponse(BaseModel):
    """Response model for update success operation."""
    message: str = Field(..., description="Success message")


@router.post("/store", response_model=StoreResponse)
async def store_knowledge(
    request: StoreRequest,
    service: RAGServiceDep
) -> StoreResponse:
    """
    Store knowledge with semantic embedding.
    
    Args:
        request: Store request with text, type, metadata, success_score
        service: RAG service instance (dependency injection)
    
    Returns:
        Store response with entry ID
    
    Raises:
        HTTPException: If storage fails
    """
    start_time = time.time()
    metrics = get_metrics()
    
    try:
        entry_id, cache_hit = await service.store(
            text=request.text,
            knowledge_type=request.knowledge_type,
            metadata=request.metadata,
            success_score=request.success_score
        )
        
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_call('store', latency_ms, cache_hit)
        metrics.record_success_score(request.success_score)
        
        logger.info(f"Stored knowledge: id={entry_id}, type={request.knowledge_type}")
        return StoreResponse(
            id=entry_id,
            message="Knowledge stored successfully"
        )
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_error('storage')
        logger.error(f"Error storing knowledge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to store knowledge: {str(e)}")


@router.post("/retrieve", response_model=RetrieveResponse)
async def retrieve_knowledge(
    request: RetrieveRequest,
    service: RAGServiceDep
) -> RetrieveResponse:
    """
    Retrieve similar knowledge using semantic similarity.
    
    Args:
        request: Retrieve request with query, filters, top_k, min_similarity
        service: RAG service instance (dependency injection)
    
    Returns:
        Retrieve response with similar entries
    
    Raises:
        HTTPException: If retrieval fails
    """
    start_time = time.time()
    metrics = get_metrics()
    
    try:
        results, cache_hit = await service.retrieve(
            query=request.query,
            knowledge_type=request.knowledge_type,
            top_k=request.top_k,
            min_similarity=request.min_similarity
        )
        
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_call('retrieve', latency_ms, cache_hit)
        
        logger.info(f"Retrieved {len(results)} results for query: {request.query[:50]}...")
        return RetrieveResponse(
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_error('embedding')
        logger.error(f"Error retrieving knowledge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve knowledge: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(
    request: SearchRequest,
    service: RAGServiceDep
) -> SearchResponse:
    """
    Search knowledge with optional filters.
    
    Args:
        request: Search request with query, filters, top_k, min_similarity
        service: RAG service instance (dependency injection)
    
    Returns:
        Search response with results
    
    Raises:
        HTTPException: If search fails
    """
    start_time = time.time()
    metrics = get_metrics()
    
    try:
        results, cache_hit = await service.search(
            query=request.query,
            filters=request.filters,
            top_k=request.top_k,
            min_similarity=request.min_similarity
        )
        
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_call('search', latency_ms, cache_hit)
        
        logger.info(f"Searched {len(results)} results for query: {request.query[:50]}...")
        return SearchResponse(
            results=results,
            count=len(results)
        )
        
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        metrics.record_error('embedding')
        logger.error(f"Error searching knowledge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search knowledge: {str(e)}")


@router.put("/{id}/success", response_model=UpdateSuccessResponse)
async def update_success_score(
    id: int,
    request: UpdateSuccessRequest,
    service: RAGServiceDep
) -> UpdateSuccessResponse:
    """
    Update success score for a knowledge entry.
    
    Args:
        id: Entry ID
        request: Update request with new success score
        service: RAG service instance (dependency injection)
    
    Returns:
        Update response with success message
    
    Raises:
        HTTPException: If update fails
    """
    try:
        await service.update_success_score(id, request.score)
        metrics = get_metrics()
        metrics.record_success_score(request.score)
        
        logger.info(f"Updated success score for entry {id}: {request.score}")
        return UpdateSuccessResponse(
            message=f"Success score updated for entry {id}"
        )
        
    except ValueError as e:
        logger.error(f"Entry not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating success score: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update success score: {str(e)}")
