"""
Synergy Router - Proxy to Pattern Service

Epic 39: Synergies are handled by ai-pattern-service, this router proxies requests.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response

from ..api.dependencies import get_authenticated_user
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/synergies", tags=["synergies"])


async def _proxy_to_pattern_service(
    request: Request,
    path: str = "",
    method: str = "GET",
    body: dict | None = None
) -> Response:
    """Proxy request to pattern service."""
    try:
        pattern_service_url = settings.pattern_service_url.rstrip("/")
        url = f"{pattern_service_url}/api/v1/synergies/{path}".rstrip("/")
        
        # Get auth headers from original request
        headers = {}
        if "authorization" in request.headers:
            headers["Authorization"] = request.headers["authorization"]
        if "x-homeiq-api-key" in request.headers:
            headers["X-HomeIQ-API-Key"] = request.headers["x-homeiq-api-key"]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=headers, params=dict(request.query_params))
            elif method == "POST":
                response = await client.post(url, headers=headers, json=body)
            else:
                raise HTTPException(status_code=405, detail=f"Method {method} not supported")
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type="application/json"
            )
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy to pattern service: {e}")
        raise HTTPException(status_code=502, detail="Pattern service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error proxying to pattern service: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/list")
async def list_synergies(
    request: Request,
    synergy_type: str | None = Query(None),
    min_confidence: float | None = Query(None),
    synergy_depth: int | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    order_by_priority: bool = Query(True)
) -> Response:
    """List synergies from pattern service."""
    path = "list"
    return await _proxy_to_pattern_service(request, path, "GET")


@router.get("/stats")
async def get_synergy_stats(request: Request) -> Response:
    """Get synergy statistics from pattern service."""
    path = "stats"
    return await _proxy_to_pattern_service(request, path, "GET")

