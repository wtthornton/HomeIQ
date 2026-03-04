"""WebSocket publisher for real-time house status push.

Manages client connections, broadcasts delta updates from the
aggregator, and handles keepalive pings plus auto-cleanup of
disconnected clients.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect, WebSocketState

logger = logging.getLogger(__name__)

_KEEPALIVE_INTERVAL = 15  # seconds


class StatusWebSocketPublisher:
    """Manages WebSocket subscribers for real-time status push."""

    def __init__(self) -> None:
        self._clients: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        self._keepalive_task: asyncio.Task[None] | None = None

    # -- lifecycle ------------------------------------------------------------

    async def start(self) -> None:
        """Start the keepalive background loop."""
        if self._keepalive_task is None or self._keepalive_task.done():
            self._keepalive_task = asyncio.create_task(self._keepalive_loop())
            logger.info("StatusWebSocketPublisher started")

    async def stop(self) -> None:
        """Cancel keepalive and close all client connections."""
        if self._keepalive_task and not self._keepalive_task.done():
            self._keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._keepalive_task
        async with self._lock:
            for ws in list(self._clients):
                await self._safe_close(ws)
            self._clients.clear()
        logger.info("StatusWebSocketPublisher stopped")

    # -- client management ----------------------------------------------------

    async def add_client(self, ws: WebSocket) -> None:
        """Register a new WebSocket client."""
        async with self._lock:
            self._clients.add(ws)
        logger.info(
            "Status WS client connected (total: %d)", len(self._clients)
        )

    async def remove_client(self, ws: WebSocket) -> None:
        """Unregister a WebSocket client."""
        async with self._lock:
            self._clients.discard(ws)
        logger.info(
            "Status WS client disconnected (total: %d)", len(self._clients)
        )

    # -- broadcasting ---------------------------------------------------------

    async def broadcast(self, delta: dict[str, Any]) -> None:
        """Send a delta update to all connected clients.

        Failed sends trigger automatic client removal.
        """
        payload = json.dumps({"type": "delta", **delta})
        dead: list[WebSocket] = []
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
            except (WebSocketDisconnect, RuntimeError, Exception):
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
            logger.debug("Cleaned up %d dead WS clients", len(dead))

    async def send_full_snapshot(
        self, ws: WebSocket, snapshot_dict: dict[str, Any]
    ) -> None:
        """Send the full status snapshot to a single client on connect."""
        payload = json.dumps({"type": "snapshot", **snapshot_dict})
        try:
            await ws.send_text(payload)
        except (WebSocketDisconnect, RuntimeError):
            logger.debug("Failed to send snapshot to client")

    # -- keepalive ------------------------------------------------------------

    async def _keepalive_loop(self) -> None:
        """Periodically ping connected clients to detect stale connections."""
        while True:
            try:
                await asyncio.sleep(_KEEPALIVE_INTERVAL)
                await self._ping_all()
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in keepalive loop")

    async def _ping_all(self) -> None:
        """Send a keepalive ping to every connected client."""
        payload = json.dumps({"type": "ping"})
        dead: list[WebSocket] = []
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                if ws.client_state == WebSocketState.CONNECTED:
                    await ws.send_text(payload)
            except (WebSocketDisconnect, RuntimeError, Exception):
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._clients.discard(ws)
            logger.debug("Keepalive cleaned up %d dead clients", len(dead))

    # -- helpers --------------------------------------------------------------

    @staticmethod
    async def _safe_close(ws: WebSocket) -> None:
        """Close a WebSocket ignoring errors."""
        with contextlib.suppress(Exception):
            if ws.client_state == WebSocketState.CONNECTED:
                await ws.close()
