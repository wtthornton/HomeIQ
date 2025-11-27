"""
Health check endpoints for AI Query Service

Epic 39, Story 39.9: Query Service Foundation
"""

import logging
from fastapi import APIRouter, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = None):
    """Basic health check endpoint."""
    return {
        "status": "ok",
        "service": "ai-query-service",
        "database": "unknown"
    }


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check(db: AsyncSession = None):
    """Readiness check with database connectivity verification."""
    try:
        if db is None:
            async for session in get_db():
                db = session
                break
        
        # Test database connection
        await db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "service": "ai-query-service",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "service": "ai-query-service",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check():
    """Liveness check endpoint."""
    return {
        "status": "live",
        "service": "ai-query-service"
    }

