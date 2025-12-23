"""
Health check router for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
"""

import logging
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.middlewares import get_error_counts, get_performance_metrics
from ..database import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Health check endpoint with basic metrics.
    
    Returns:
        Health status, database connectivity, and basic metrics
    """
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        # Get performance metrics
        perf_metrics = get_performance_metrics()
        error_counts = get_error_counts()
        
        # Calculate total errors
        total_errors = sum(error_counts.values())
        
        # Get key endpoint metrics (if available)
        key_metrics = {}
        for endpoint in ["POST /api/suggestions/generate", "GET /api/suggestions/list", 
                        "POST /api/deployments/deploy", "GET /api/deployments/list"]:
            if endpoint in perf_metrics:
                key_metrics[endpoint] = {
                    "avg_response_time": round(perf_metrics[endpoint]["avg"], 3),
                    "p95_response_time": round(perf_metrics[endpoint]["p95"], 3),
                    "error_count": error_counts.get(endpoint, 0)
                }
        
        return {
            "status": "healthy",
            "service": "ai-automation-service",
            "version": "1.0.0",
            "database": "connected",
            "metrics": {
                "total_errors": total_errors,
                "endpoints": key_metrics
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "ai-automation-service",
            "error": str(e),
            "database": "disconnected"
        }, 503

