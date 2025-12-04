"""
Health check router for websocket-ingestion service.
"""

from fastapi import APIRouter, Request
from typing import Any

from ...api.models import HealthResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthResponse)
async def health_check(request: Request):
    """
    Health check endpoint.
    
    Returns service health status including connection and subscription information.
    """
    service = request.app.state.service
    # Access the health handler from the service
    if hasattr(service, 'health_handler'):
        handler = service.health_handler
        return await handler.handle_fastapi()
    else:
        return {
            "status": "healthy",
            "service": "websocket-ingestion",
            "timestamp": None
        }
