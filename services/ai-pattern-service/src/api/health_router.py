"""
Health check router for Pattern Service

Epic 39, Story 39.5: Pattern Service Foundation
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """
    Health check endpoint.
    
    Verifies database connectivity by executing a simple query.
    
    Args:
        db: Database session dependency
        
    Returns:
        dict: Health status with database connection status
        
    Raises:
        HTTPException: If database connection fails (500 status)
    """
    try:
        # Attempt to execute a simple query to check database connectivity
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        # CRITICAL FIX: Don't leak exception details in error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database connection failed"  # Generic error message
        )


@router.get("/ready", status_code=status.HTTP_200_OK)
async def readiness_check() -> dict[str, str]:
    """
    Readiness check endpoint.
    
    Indicates whether the service is ready to accept traffic.
    
    Returns:
        dict: Readiness status
    """
    return {"status": "ready"}


@router.get("/live", status_code=status.HTTP_200_OK)
async def liveness_check() -> dict[str, str]:
    """
    Liveness check endpoint.
    
    Indicates whether the service is alive and running.
    
    Returns:
        dict: Liveness status
    """
    return {"status": "live"}

