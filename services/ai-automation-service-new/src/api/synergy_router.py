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
        # Construct URL properly - avoid double slashes and trailing slashes
        if path:
            url = f"{pattern_service_url}/api/v1/synergies/{path}".rstrip("/")
        else:
            url = f"{pattern_service_url}/api/v1/synergies"
        
        logger.debug(f"Proxying {method} request to: {url}")
        
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
            
            # Handle non-2xx responses
            if response.status_code >= 400:
                error_detail = "Pattern service error"
                try:
                    error_body = response.json()
                    if isinstance(error_body, dict):
                        error_detail = error_body.get("detail", error_body.get("message", str(error_body)))
                    else:
                        error_detail = str(error_body)
                except Exception:
                    error_detail = response.text[:200] if response.text else "Unknown error"
                
                logger.error(f"Pattern service returned {response.status_code}: {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=error_detail
                )
            
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={k: v for k, v in response.headers.items() if k.lower() not in ["content-length", "transfer-encoding"]},
                media_type="application/json"
            )
    except httpx.ConnectError as e:
        logger.error(f"Failed to connect to pattern service at {settings.pattern_service_url}: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Pattern service unavailable: Unable to connect to {settings.pattern_service_url}"
        )
    except httpx.TimeoutException as e:
        logger.error(f"Timeout connecting to pattern service: {e}")
        raise HTTPException(
            status_code=504,
            detail="Pattern service timeout: Request took too long"
        )
    except httpx.RequestError as e:
        logger.error(f"Failed to proxy to pattern service: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"Pattern service unavailable: {str(e)}"
        )
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Unexpected error proxying to pattern service: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("")
@router.get("/")
async def get_synergies_root(
    request: Request,
    synergy_type: str | None = Query(None),
    min_confidence: float | None = Query(None),
    validated_by_patterns: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    order_by_priority: bool = Query(True)
) -> Response:
    """
    Root endpoint for synergies - proxies to list endpoint.
    
    This endpoint handles requests to /api/synergies (without /list suffix)
    to maintain compatibility with frontend API calls.
    """
    # Proxy to the list endpoint in pattern service
    path = "list"
    return await _proxy_to_pattern_service(request, path, "GET")


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
    path = "statistics"  # Changed from "stats" to "statistics" to avoid route conflict
    return await _proxy_to_pattern_service(request, path, "GET")


@router.get("/{synergy_id}")
async def get_synergy(
    request: Request,
    synergy_id: str
) -> Response:
    """Get a single synergy by ID from pattern service."""
    path = synergy_id
    return await _proxy_to_pattern_service(request, path, "GET")

