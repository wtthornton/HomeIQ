"""
Synergy Router - Proxy to Pattern Service

Epic 39: Synergies are handled by ai-pattern-service, this router proxies requests.
M1 fix: Uses shared proxy_utils instead of duplicated proxy function.
"""

import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from ..api.proxy_utils import proxy_to_service
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/synergies", tags=["synergies"])


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
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/v1/synergies", "list"
    )


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
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/v1/synergies", "list"
    )


@router.get("/stats")
async def get_synergy_stats(request: Request) -> Response:
    """Get synergy statistics from pattern service."""
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/v1/synergies", "statistics"
    )


@router.get("/{synergy_id}")
async def get_synergy(
    request: Request,
    synergy_id: str
) -> Response:
    """Get a single synergy by ID from pattern service."""
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/v1/synergies", synergy_id
    )
