"""Health check endpoint"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "proactive-agent-service",
        "version": "1.0.0"
    }

