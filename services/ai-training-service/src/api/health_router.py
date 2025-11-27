"""
Health check router for AI Training Service

Epic 39, Story 39.1: Training Service Foundation
"""

import json
from fastapi import APIRouter, Response
from sqlalchemy import text

router = APIRouter()


@router.get("/")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "ai-training-service",
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check():
    """Readiness check with database connectivity"""
    try:
        # Test database connection
        from ..database import get_db
        from sqlalchemy import text
        async for session in get_db():
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            break
        
        return {
            "status": "ready",
            "service": "ai-training-service",
            "database": "connected"
        }
    except Exception as e:
        from fastapi import Response
        return Response(
            content=json.dumps({
                "status": "not_ready",
                "service": "ai-training-service",
                "database": "disconnected",
                "error": str(e)
            }),
            status_code=503,
            media_type="application/json"
        )


@router.get("/live")
async def liveness_check():
    """Liveness check endpoint"""
    return {
        "status": "alive",
        "service": "ai-training-service"
    }

