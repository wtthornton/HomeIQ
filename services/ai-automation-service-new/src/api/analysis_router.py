"""
Analysis Router - Proxy to Pattern Service

Epic 39: Analysis endpoints are handled by ai-pattern-service, this router proxies requests.
"""

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from ..api.dependencies import get_authenticated_user
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


async def _proxy_to_pattern_service(
    request: Request,
    path: str = "",
    method: str = "GET"
) -> Response:
    """Proxy request to pattern service."""
    try:
        pattern_service_url = settings.pattern_service_url.rstrip("/")
        url = f"{pattern_service_url}/api/analysis/{path}".rstrip("/")
        
        # Get auth headers from original request
        headers = {}
        if "authorization" in request.headers:
            headers["Authorization"] = request.headers["authorization"]
        if "x-homeiq-api-key" in request.headers:
            headers["X-HomeIQ-API-Key"] = request.headers["x-homeiq-api-key"]
        
        # Read request body for POST requests
        body = None
        if method == "POST":
            try:
                body = await request.json()
            except Exception:
                # No body or invalid JSON, use empty dict
                body = {}
        
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
        logger.error(f"Unexpected error proxying to pattern service: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/status")
async def get_analysis_status(
    request: Request
) -> Response:
    """Get analysis status from pattern service."""
    return await _proxy_to_pattern_service(request, "status", "GET")


@router.get("/schedule")
async def get_analysis_schedule(
    request: Request
) -> Response:
    """Get analysis schedule from pattern service."""
    return await _proxy_to_pattern_service(request, "schedule", "GET")


@router.post("/trigger")
async def trigger_analysis(
    request: Request
) -> Response:
    """Trigger analysis in pattern service."""
    return await _proxy_to_pattern_service(request, "trigger", "POST")

