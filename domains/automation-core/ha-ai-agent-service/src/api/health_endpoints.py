"""Health check endpoint for HA AI Agent Service.

Rich GroupHealthCheck enriched with database and OpenAI status.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from .dependencies import chat_dependencies_ready

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict:
    """Group-aware health check endpoint.

    Probes cross-group dependencies (data-api, device-intelligence,
    ai-automation-service) and reports group status, dependency latencies,
    and degraded features.  Also checks database and OpenAI config.
    """
    from ..main import group_health, settings

    if not group_health:
        raise HTTPException(status_code=503, detail="Service not ready")

    try:
        result = await group_health.to_dict()

        # Enrich with local checks (not remote HTTP deps)
        from sqlalchemy import text

        from ..database import get_session

        try:
            async for session in get_session():
                await session.execute(text("SELECT 1"))
            result["dependencies"]["database"] = {"status": "healthy"}
        except Exception:
            result["dependencies"]["database"] = {"status": "unhealthy"}
            if result["status"] == "healthy":
                result["status"] = "degraded"

        # OpenAI config check
        openai_key = getattr(settings, "openai_api_key", None)
        if openai_key and openai_key.get_secret_value():
            result["dependencies"]["openai"] = {"status": "configured"}
        else:
            result["dependencies"]["openai"] = {"status": "not-configured"}

        # Chat/conversation APIs require full startup (set_services), not only group_health
        if not chat_dependencies_ready():
            result["dependencies"]["chat_api"] = {
                "status": "not-initialized",
                "hint": (
                    "Startup did not finish wiring chat services. "
                    "Set OPENAI_API_KEY (and other LLM env vars) or check container logs for errors."
                ),
            }
            result["status"] = "unhealthy"
            return JSONResponse(content=result, status_code=503)

        status_code = 503 if result["status"] == "unhealthy" else 200
        return JSONResponse(content=result, status_code=status_code)
    except Exception as e:
        logger.exception("Error during health check")
        raise HTTPException(status_code=503, detail="Health check failed") from e
