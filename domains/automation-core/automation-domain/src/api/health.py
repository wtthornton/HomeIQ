"""One health endpoint for the merged process (TAP-7275).

Each folded service used to answer its own ``GET /health``. In one process only
the first registration would ever be reached, so the three were replaced by
this one, which reports a per-slice breakdown instead of whichever slice
happened to be mounted first.

The status rule follows the strictest of the three predecessors: the agent
slice returned 503 when its chat dependencies were not wired, because a
container reporting healthy with a broken ``/api/v1/chat`` is the failure this
program keeps rediscovering. That behaviour is preserved -- a slice that did
not finish startup makes the whole endpoint 503, and the payload names which.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


async def _probe_schema(get_session: Any, slice_name: str) -> dict[str, Any]:
    """Run ``SELECT 1`` on one slice's session factory."""
    try:
        async for session in get_session():
            await session.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        logger.warning("health: %s database probe failed: %s", slice_name, exc)
        return {"status": "unhealthy", "error": str(exc)[:200]}


@router.get("/health")
async def health_check() -> JSONResponse:
    """Report the health of all three slices and the AgentForge dependency."""
    from ..agent.api.dependencies import chat_dependencies_ready
    from ..agent.database import get_session as agent_session
    from ..main import agentforge_reachable, settings
    from ..proactive.database import get_session as proactive_session

    slices: dict[str, Any] = {}
    unhealthy: list[str] = []

    slices["agent"] = {
        "database": await _probe_schema(agent_session, "agent"),
        "chat_api": "ready" if chat_dependencies_ready() else "not-initialized",
    }
    if not chat_dependencies_ready():
        unhealthy.append("agent.chat_api")

    from ..authoring.database import db as authoring_db

    try:
        async with authoring_db.engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        slices["authoring"] = {"database": {"status": "healthy"}}
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        logger.warning("health: authoring database probe failed: %s", exc)
        slices["authoring"] = {"database": {"status": "unhealthy", "error": str(exc)[:200]}}

    slices["proactive"] = {"database": await _probe_schema(proactive_session, "proactive")}

    for name, body in slices.items():
        db_status = (body.get("database") or {}).get("status")
        if db_status == "unhealthy":
            unhealthy.append(f"{name}.database")

    # AgentForge is where every LLM call went (TAP-7275). "configured" is a
    # local fact -- a key is present. "reachable" is what startup actually
    # observed. They are reported separately because a configured-but-
    # unreachable AgentForge is exactly the shape of failure that a
    # config-only check would call healthy.
    agentforge = {
        "url": settings.agentforge_url,
        "configured": bool(settings.agentforge_api_key),
        "reachable": agentforge_reachable(),
    }

    status = "unhealthy" if unhealthy else "healthy"
    if status == "healthy" and not agentforge["reachable"]:
        status = "degraded"

    payload = {
        "status": status,
        "service": "automation-domain",
        "version": "1.0.0",
        "slices": slices,
        "agentforge": agentforge,
        "degraded": unhealthy,
    }
    return JSONResponse(content=payload, status_code=503 if unhealthy else 200)
