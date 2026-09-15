"""REST + WebSocket endpoints for real-time house status.

GET  /api/status/house  — full JSON snapshot (requires `Authorization: Bearer <API_KEY>`)
WS   /ws/status         — real-time delta push (requires the same bearer token)
"""

from __future__ import annotations

import logging
import secrets
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ...config import settings
from ...house_status.models import HouseStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["status"])

_bearer_scheme = HTTPBearer(auto_error=False)


def _configured_api_key() -> str | None:
    """Return the shared status API key, or None if unset."""
    if settings.api_key is None:
        return None
    return settings.api_key.get_secret_value() or None


async def require_status_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
) -> None:
    """REST auth dependency for /api/status/house.

    Missing/invalid bearer token -> 401. Unconfigured key -> 503, since an
    unset API_KEY must fail closed rather than silently accept every request.
    """
    expected = _configured_api_key()
    if expected is None:
        raise HTTPException(status_code=503, detail="Status API key not configured on server")
    if credentials is None or not secrets.compare_digest(credentials.credentials, expected):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _extract_ws_bearer_token(websocket: WebSocket) -> str | None:
    """Pull a bearer token out of the WebSocket upgrade request's Authorization header.

    A browser WebSocket object cannot set custom headers, but nginx (a real,
    non-browser client from the backend's perspective) injects this header on
    every proxied /ws request, so the dashboard never has to hold the token
    itself — see health-dashboard/nginx.conf's `location /ws` block.
    """
    auth_header = websocket.headers.get("authorization")
    if not auth_header:
        return None
    scheme, _, value = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not value:
        return None
    return value


async def require_status_ws_token(websocket: WebSocket) -> str:
    """WebSocket auth dependency for /ws/status.

    Raises before `websocket.accept()` so an unauthenticated client sees the
    connection rejected (WebSocketDisconnect on the client side) rather than
    an accepted-then-closed socket.
    """
    expected = _configured_api_key()
    token = _extract_ws_bearer_token(websocket)
    if expected is None or token is None or not secrets.compare_digest(token, expected):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return token


@router.get(
    "/api/status/house",
    response_model=HouseStatusResponse,
    dependencies=[Depends(require_status_api_key)],
)
async def get_house_status(request: Request) -> HouseStatusResponse:
    """Return a full snapshot of the current house status.

    Returns 503 if the aggregator is not yet ready (no events processed).
    """
    service = getattr(request.app.state, "service", None)
    aggregator = getattr(service, "house_status_aggregator", None) if service else None

    if aggregator is None:
        raise HTTPException(
            status_code=503,
            detail="House status aggregator not available",
        )
    if not aggregator.ready:
        raise HTTPException(
            status_code=503,
            detail="House status aggregator not ready — no events processed yet",
        )

    return await aggregator.get_snapshot()


@router.websocket("/ws/status")
async def ws_status(
    websocket: WebSocket,
    _token: Annotated[str, Depends(require_status_ws_token)],
) -> None:
    """WebSocket endpoint for real-time house status push.

    On connect the client receives a full snapshot followed by delta
    updates as state changes occur.  A keepalive ping is sent every
    15 seconds by the publisher.
    """
    service = getattr(websocket.app.state, "service", None)
    aggregator = getattr(service, "house_status_aggregator", None) if service else None
    publisher = getattr(service, "house_status_publisher", None) if service else None

    if aggregator is None or publisher is None:
        await websocket.close(code=1013, reason="Status aggregator not available")
        return

    await websocket.accept()
    await publisher.add_client(websocket)

    # Send initial snapshot if aggregator is ready.
    if aggregator.ready:
        snapshot = await aggregator.get_snapshot()
        await publisher.send_full_snapshot(websocket, snapshot.model_dump())

    try:
        # Keep connection alive — client messages are ignored.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.debug("WS status client error", exc_info=True)
    finally:
        await publisher.remove_client(websocket)
