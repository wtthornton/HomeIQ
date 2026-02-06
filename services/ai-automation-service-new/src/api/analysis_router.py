"""
Analysis Router - Proxy to Pattern Service

Epic 39: Analysis endpoints are handled by ai-pattern-service, this router proxies requests.
M1 fix: Uses shared proxy_utils instead of duplicated proxy function.
"""

import logging

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ..api.proxy_utils import proxy_to_service
from ..config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/status")
async def get_analysis_status(
    request: Request
) -> Response:
    """Get analysis status from pattern service."""
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/analysis", "status"
    )


@router.get("/schedule")
async def get_analysis_schedule(
    request: Request
) -> Response:
    """Get analysis schedule from pattern service."""
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/analysis", "schedule"
    )


@router.post("/trigger")
async def trigger_analysis(
    request: Request
) -> Response:
    """Trigger analysis in pattern service."""
    body = None
    try:
        body = await request.json()
    except Exception:
        body = {}
    return await proxy_to_service(
        request, settings.pattern_service_url, "api/analysis", "trigger",
        method="POST", body=body
    )
