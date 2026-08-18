"""`/health` — readiness with per-backing status (TAP-5293 acceptance)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import JSONResponse

if TYPE_CHECKING:
    from starlette.requests import Request

    from .backends import Backings
    from .registry import ToolRegistry


async def health_payload(
    registry: ToolRegistry, backings: Backings, *, version: str
) -> tuple[dict[str, Any], int]:
    statuses = await backings.probe_all()
    required_ok = next(s.ok for s in statuses if s.name == "data-api")
    body = {
        "status": "ok" if required_ok else "degraded",
        "service": "homeiq-mcp",
        "version": version,
        "catalogue_version": registry.catalogue.version,
        "tools_registered": registry.names(),
        "tools_pending": registry.unregistered_active(),
        "backings": [
            {"name": s.name, "ok": s.ok, "latency_ms": s.latency_ms, "detail": s.detail}
            for s in statuses
        ],
    }
    return body, (200 if required_ok else 503)


def make_health_endpoint(registry: ToolRegistry, backings: Backings, *, version: str):
    async def endpoint(_: Request) -> JSONResponse:
        body, status = await health_payload(registry, backings, version=version)
        return JSONResponse(body, status_code=status)

    return endpoint
