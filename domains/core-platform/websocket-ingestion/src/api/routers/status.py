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
from ...house_status.known_areas import (
    KnownAreaCache,
    KnownAreasUnavailable,
    fetch_known_area_ids,
)
from ...house_status.models import HouseStatusResponse, RoomsResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["status"])

_bearer_scheme = HTTPBearer(auto_error=False)

# Warmed by GET /api/status/rooms; read (never fetched) by the WS rooms
# section so a data-api outage degrades the live push instead of blocking
# or failing the WebSocket handshake (TAP-7587).
_known_area_cache = KnownAreaCache()


def _configured_api_key() -> str | None:
    """Return the shared status API key, or None if unset."""
    if settings.api_key is None:
        return None
    return settings.api_key.get_secret_value() or None


def _configured_data_api_key() -> str | None:
    """Return the bearer token used to call data-api's internal routes."""
    if settings.data_api_key is None:
        return None
    return settings.data_api_key.get_secret_value() or None


async def _known_area_ids_or_503() -> list[str]:
    """Return the known-area set, refreshing from data-api on a stale cache.

    Fails closed (503) only when data-api cannot be reached *and* nothing
    has ever been cached — an area set is never returned incomplete.
    """
    if _known_area_cache.is_stale():
        try:
            area_ids = await fetch_known_area_ids(settings.data_api_url, _configured_data_api_key())
            _known_area_cache.update(area_ids)
        except KnownAreasUnavailable as exc:
            if not _known_area_cache.get_cached():
                raise HTTPException(
                    status_code=503,
                    detail=f"Known area set unavailable from data-api: {exc}",
                ) from exc
            logger.warning("Serving stale known-area cache; data-api fetch failed: %s", exc)
    return _known_area_cache.get_cached()


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


@router.get(
    "/api/status/rooms",
    response_model=RoomsResponse,
    dependencies=[Depends(require_status_api_key)],
)
async def get_status_rooms(request: Request) -> RoomsResponse:
    """Return the presence roll-up for every area known to data-api (TAP-7587).

    Unlike ``/api/status/house``, this does not require the aggregator to be
    ``ready`` — an area with zero presence sensors (or zero events processed
    at all) must still be reported with state ``"unknown"``, never omitted.
    Returns 503 only if the aggregator component itself isn't wired, or the
    known-area set can't be fetched from data-api and no cached value exists.
    """
    service = getattr(request.app.state, "service", None)
    aggregator = getattr(service, "house_status_aggregator", None) if service else None

    if aggregator is None:
        raise HTTPException(
            status_code=503,
            detail="House status aggregator not available",
        )

    known_area_ids = await _known_area_ids_or_503()
    rooms = await aggregator.get_rooms(known_area_ids)
    return RoomsResponse(rooms=rooms)


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
        payload = snapshot.model_dump()

        # Upgrade "rooms" from sensor-only to the full known-area union, but
        # only from the cache GET /api/status/rooms warms — never a live
        # data-api call here, so a data-api outage can never block or fail
        # this handshake (TAP-7587).
        cached_area_ids = _known_area_cache.get_cached()
        if cached_area_ids:
            rooms = await aggregator.get_rooms(cached_area_ids)
            payload["rooms"] = [r.model_dump() for r in rooms]

        await publisher.send_full_snapshot(websocket, payload)

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
