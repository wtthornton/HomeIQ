"""
Health check endpoints for AI Query Service

Epic 39, Story 39.9: Query Service Foundation
"""

import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Basic health check endpoint with database connectivity verification.

    Returns:
        dict: Health status information including service name and database status.
    """
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "service": "ai-query-service",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"[ERROR] Health check database probe failed: {e}", exc_info=True)
        return {
            "status": "degraded",
            "service": "ai-query-service",
            "database": "disconnected"
        }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Readiness check with database connectivity verification.
    
    Args:
        db: The database session dependency.
    
    Returns:
        dict: Readiness status including database connection status.
    """
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "service": "ai-query-service",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"[ERROR] Readiness check failed: {e}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "service": "ai-query-service",
                "database": "disconnected"
            }
        )


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, str]:
    """
    Liveness check endpoint.
    
    Returns:
        dict: Liveness status information.
    """
    return {
        "status": "live",
        "service": "ai-query-service"
    }

