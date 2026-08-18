"""`/health` — readiness with per-backing status (TAP-5293 acceptance).

The route is deliberately unauthenticated: the container healthcheck and any
external monitor need it, and unlike `/mcp` it does not sit behind the
transport's DNS-rebinding guard. Now that the port is published on the LAN for
the Home Assistant integration (TAP-5305..5309), only liveness is public. The
registered tool names and the per-backing topology describe what sits behind
this server, so they are returned only to a caller presenting a valid token.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from starlette.responses import JSONResponse

from .auth import bearer_credential, resolve_scopes

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


#: Everything a liveness probe legitimately needs, and nothing that describes
#: what sits behind the server.
LIVENESS_FIELDS = ("status", "service", "version")


def liveness_view(body: dict[str, Any]) -> dict[str, Any]:
    """Project the full health body down to its unauthenticated subset."""
    return {key: body[key] for key in LIVENESS_FIELDS}


def make_health_endpoint(
    registry: ToolRegistry,
    backings: Backings,
    *,
    version: str,
    read_tokens: list[str],
    write_tokens: list[str],
):
    async def endpoint(request: Request) -> JSONResponse:
        body, status = await health_payload(registry, backings, version=version)
        credential = bearer_credential(request.headers.get("authorization", ""))
        authorized = credential is not None and (
            resolve_scopes(credential, read_tokens, write_tokens) is not None
        )
        return JSONResponse(body if authorized else liveness_view(body), status_code=status)

    return endpoint
