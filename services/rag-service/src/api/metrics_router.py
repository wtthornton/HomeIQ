"""
Metrics Router

API endpoints for RAG metrics (for RAG Status Monitor integration).
Following 2025 patterns: simple metrics exposure.
"""

import logging
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..utils.metrics import get_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metrics", tags=["metrics"])


class MetricsResponse(BaseModel):
    """Response model for metrics endpoint."""
    total_calls: int
    store_calls: int
    retrieve_calls: int
    search_calls: int
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    errors: int
    embedding_errors: int
    storage_errors: int
    error_rate: float
    avg_success_score: float
    total_latency_ms: float
    total_success_scores: int


@router.get("", response_model=MetricsResponse)
async def get_metrics_endpoint() -> MetricsResponse:
    """
    Get RAG service metrics.
    
    Returns:
        Current metrics snapshot
    """
    metrics = get_metrics()
    metrics_data = metrics.get_metrics()
    
    return MetricsResponse(**metrics_data)


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """
    Get detailed statistics (alias for metrics endpoint with different format).
    
    Returns:
        Detailed metrics dictionary
    """
    metrics = get_metrics()
    return metrics.get_metrics()


@router.post("/reset")
async def reset_metrics() -> dict[str, str]:
    """
    Reset all metrics (useful for testing and debugging).
    
    Returns:
        Success message
    """
    metrics = get_metrics()
    metrics.reset()
    logger.info("RAG metrics reset via API endpoint")
    return {"message": "Metrics reset successfully"}