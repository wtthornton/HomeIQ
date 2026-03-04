"""
Health check router for websocket-ingestion service.
"""

from fastapi import APIRouter, Request

from ...api.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health/detailed", response_model=HealthResponse)
async def health_check_detailed(request: Request):
    """Detailed health check with connection and subscription information.

    The standard ``/health`` endpoint is provided by ``StandardHealthCheck``
    from homeiq-resilience.  This endpoint adds rich WebSocket-specific data.
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
