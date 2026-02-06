"""
Pattern Router - Proxy to Pattern Service

Epic 39: Patterns are handled by ai-pattern-service, this router proxies requests.
M1 fix: Uses shared proxy_utils instead of duplicated proxy function.
"""

import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from ..api.proxy_utils import proxy_to_service
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("/list")
async def list_patterns(
    request: Request,
    pattern_type: str | None = Query(None),
    min_confidence: float | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0)
) -> Response:
    """List patterns from pattern service."""
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/v1/patterns", "list"
    )


@router.get("/stats")
async def get_pattern_stats(request: Request) -> Response:
    """Get pattern statistics from pattern service."""
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/v1/patterns", "stats"
    )


@router.post("/analysis/run")
async def run_analysis(request: Request) -> Response:
    """Trigger pattern analysis in pattern service."""
    body = await request.json() if request.headers.get("content-type") == "application/json" else None
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/v1/patterns", "analysis/run",
        method="POST", body=body
    )
