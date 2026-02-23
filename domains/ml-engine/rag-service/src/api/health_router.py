"""
Health Check Router

Health and readiness endpoints for RAG service.
Following 2025 patterns: simple health checks.
"""

import logging
from typing import Any

from fastapi import APIRouter, Request
from sqlalchemy import text

from ..database.session import async_session_maker

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """
    Health check endpoint (liveness probe).

    Returns:
        Service status
    """
    return {
        "status": "healthy",
        "service": "rag-service"
    }


@router.get("/health/ready")
async def readiness(request: Request) -> dict[str, Any]:
    """
    Readiness probe endpoint. Checks database connectivity
    and OpenVINO service availability.

    Returns:
        Service readiness status with dependency checks
    """
    checks: dict[str, str] = {}

    # Check database connectivity
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error("Readiness check: database unavailable: %s", e)
        checks["database"] = "unavailable"

    # Check OpenVINO client (best-effort, don't fail readiness if unavailable)
    try:
        openvino_client = request.app.state.openvino_client
        response = await openvino_client.client.get(
            f"{openvino_client.base_url}/health", timeout=5.0
        )
        checks["openvino"] = "ok" if response.status_code == 200 else "degraded"
    except Exception:
        checks["openvino"] = "unavailable"

    all_ok = checks.get("database") == "ok"
    return {
        "status": "ready" if all_ok else "not_ready",
        "service": "rag-service",
        "checks": checks,
    }
