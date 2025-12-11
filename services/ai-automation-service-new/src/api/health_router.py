"""
Health check router for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
"""

import logging
from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import engine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": "ai-automation-service",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "service": "ai-automation-service",
            "error": str(e)
        }, 503

