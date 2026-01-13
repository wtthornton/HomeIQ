"""
Health Check Router

Health and readiness endpoints for RAG service.
Following 2025 patterns: simple health checks.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint.
    
    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "rag-service"
    }


@router.get("/health/ready")
async def readiness() -> dict[str, str]:
    """
    Readiness probe endpoint.
    
    Returns:
        Service readiness status
    """
    return {
        "status": "ready",
        "service": "rag-service"
    }
