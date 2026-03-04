"""REST + WebSocket endpoints for real-time house status.

GET  /api/status/house  — full JSON snapshot
WS   /ws/status         — real-time delta push
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from ...house_status.models import HouseStatusResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["status"])


@router.get("/api/status/house", response_model=HouseStatusResponse)
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
async def ws_status(websocket: WebSocket) -> None:
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
