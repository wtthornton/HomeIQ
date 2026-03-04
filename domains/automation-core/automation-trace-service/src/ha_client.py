"""
Home Assistant WebSocket client for automation trace commands.

Simplified client that handles auth + request/response commands only
(no event subscriptions). Used for trace/list, trace/get, and
config/automation/list.
"""

import asyncio
import json
import logging
from typing import Any

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType

from . import config

logger = logging.getLogger(__name__)


class HATraceClient:
    """WebSocket client for HA trace and automation config commands."""

    def __init__(self):
        self.base_url = config.HA_WS_URL.rstrip("/")
        self.token = config.HA_TOKEN
        self.session: ClientSession | None = None
        self.ws: ClientWebSocketResponse | None = None
        self.is_connected = False
        self._msg_id = 0
        self._pending: dict[int, asyncio.Future] = {}

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> bool:
        """Establish WebSocket connection and authenticate."""
        try:
            if not self.token:
                logger.error("HA_TOKEN not set — cannot connect")
                return False

            if self.session and not self.session.closed:
                await self.session.close()

            self.session = ClientSession()

            # Build WS URL
            ws_url = self.base_url
            if ws_url.startswith(("http://", "https://")):
                ws_url = ws_url.replace("https://", "wss://").replace("http://", "ws://")
            if "/api/websocket" not in ws_url:
                ws_url = f"{ws_url}/api/websocket"

            logger.info("Connecting to Home Assistant at %s", ws_url)
            self.ws = await self.session.ws_connect(ws_url)

            # Auth flow: receive auth_required → send auth → receive auth_ok
            msg = await self.ws.receive()
            if msg.type != WSMsgType.TEXT:
                logger.error("Expected TEXT, got %s", msg.type)
                return False

            data = json.loads(msg.data)
            if data.get("type") != "auth_required":
                logger.error("Expected auth_required, got %s", data.get("type"))
                return False

            await self.ws.send_str(json.dumps({
                "type": "auth",
                "access_token": self.token,
            }))

            msg = await self.ws.receive()
            if msg.type != WSMsgType.TEXT:
                logger.error("Auth response not TEXT: %s", msg.type)
                return False

            result = json.loads(msg.data)
            if result.get("type") != "auth_ok":
                logger.error("Auth failed: %s", result)
                return False

            self.is_connected = True
            logger.info("Authenticated with Home Assistant (version %s)", result.get("ha_version"))

            # Start background listener for routing responses
            asyncio.create_task(self._listen_loop(), name="ha-trace-listener")
            return True

        except Exception:
            logger.exception("Failed to connect to Home Assistant")
            await self.disconnect()
            return False

    async def disconnect(self):
        """Close WebSocket and session."""
        self.is_connected = False
        if self.ws and not self.ws.closed:
            await self.ws.close()
        if self.session and not self.session.closed:
            await self.session.close()
        self.ws = None
        self.session = None
        # Cancel pending futures
        for fut in self._pending.values():
            if not fut.done():
                fut.cancel()
        self._pending.clear()
        logger.info("Disconnected from Home Assistant")

    # ------------------------------------------------------------------
    # Internal message routing
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    async def _send_command(self, payload: dict[str, Any], timeout: float = 30.0) -> Any:
        """Send a WS command and wait for its response."""
        if not self.is_connected or not self.ws or self.ws.closed:
            raise ConnectionError("Not connected to Home Assistant")

        msg_id = self._next_id()
        payload["id"] = msg_id

        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[msg_id] = fut

        await self.ws.send_str(json.dumps(payload))

        try:
            result = await asyncio.wait_for(fut, timeout=timeout)
        except TimeoutError:
            self._pending.pop(msg_id, None)
            raise TimeoutError(f"HA command timed out after {timeout}s: {payload.get('type')}")
        finally:
            self._pending.pop(msg_id, None)

        return result

    async def _listen_loop(self):
        """Route incoming WS messages to pending futures."""
        try:
            async for msg in self.ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    msg_id = data.get("id")
                    if msg_id and msg_id in self._pending:
                        fut = self._pending[msg_id]
                        if not fut.done():
                            if data.get("success"):
                                fut.set_result(data.get("result"))
                            else:
                                fut.set_exception(
                                    RuntimeError(f"HA error: {data.get('error', {}).get('message', 'unknown')}")
                                )
                elif msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE, WSMsgType.CLOSED):
                    logger.warning("WS connection lost (type=%s)", msg.type)
                    break
        except Exception:
            logger.exception("Listen loop error")
        finally:
            self.is_connected = False
            # Cancel any still-pending futures
            for fut in self._pending.values():
                if not fut.done():
                    fut.cancel()

    # ------------------------------------------------------------------
    # HA API commands
    # ------------------------------------------------------------------

    async def list_automations(self) -> list[dict[str, Any]]:
        """Get all automations via config/automation/config."""
        # HA returns a dict keyed by automation id
        result = await self._send_command({"type": "automation/config"})
        # Fallback: try listing entities in automation domain
        if result is None:
            result = []
        if isinstance(result, dict):
            # Convert {id: config} dict to list with id included
            return [{"id": aid, **cfg} for aid, cfg in result.items()]
        return result

    async def list_traces(self, automation_id: str | None = None) -> list[dict[str, Any]]:
        """List trace summaries for one or all automations.

        Args:
            automation_id: Optional specific automation ID (e.g. "1671062698879").
                          If None, lists traces for ALL automations.
        """
        payload: dict[str, Any] = {"type": "trace/list", "domain": "automation"}
        if automation_id:
            payload["item_id"] = automation_id
        result = await self._send_command(payload)
        return result if isinstance(result, list) else []

    async def get_trace(self, automation_id: str, run_id: str) -> dict[str, Any]:
        """Get full trace detail for a specific run."""
        result = await self._send_command({
            "type": "trace/get",
            "domain": "automation",
            "item_id": automation_id,
            "run_id": run_id,
        })
        return result if isinstance(result, dict) else {}

    async def get_automation_entities(self) -> list[dict[str, Any]]:
        """Get automation entities via entity registry filtered to automation domain."""
        try:
            all_entities = await self._send_command({"type": "config/entity_registry/list"})
            if not isinstance(all_entities, list):
                return []
            return [e for e in all_entities if e.get("entity_id", "").startswith("automation.")]
        except Exception:
            logger.exception("Failed to list automation entities")
            return []
