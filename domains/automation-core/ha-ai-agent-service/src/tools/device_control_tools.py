"""Device Control Tool Handler.

Epic 25 Story 25.7: Routes device control tool calls from the AI agent
to the ha-device-control service (port 8040) via HTTP.

This handler is a thin proxy — all logic lives in ha-device-control.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class DeviceControlToolHandler:
    """Handles device control tool calls by proxying to ha-device-control service."""

    def __init__(self, base_url: str, timeout: int = 15) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def startup(self) -> None:
        """Create the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
        )
        logger.info("DeviceControlToolHandler connected to %s", self._base_url)

    async def shutdown(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Tool implementations — each proxies to ha-device-control endpoint
    # ------------------------------------------------------------------

    async def control_light(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Control a specific light."""
        return await self._post("/api/control/light", arguments)

    async def control_light_area(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Control all lights in an area."""
        return await self._post("/api/control/light/area", arguments)

    async def control_switch(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Control a switch."""
        return await self._post("/api/control/switch", arguments)

    async def get_climate(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Get climate/thermostat status."""
        return await self._get("/api/control/climate")

    async def set_climate(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Set climate/thermostat temperature."""
        return await self._post("/api/control/climate", arguments)

    async def activate_scene(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Activate a scene or script."""
        return await self._post("/api/control/scene", arguments)

    async def house_status(self, _arguments: dict[str, Any]) -> dict[str, Any]:
        """Get house status snapshot."""
        return await self._get("/api/control/status")

    async def send_notification(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Send a phone notification."""
        return await self._post("/api/control/notify", arguments)

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    async def _post(self, path: str, data: dict[str, Any]) -> dict[str, Any]:
        """POST to ha-device-control and return result."""
        if not self._client:
            return {"success": False, "error": "Device control service not initialized"}
        try:
            resp = await self._client.post(path, json=data)
            result = resp.json()
            if resp.status_code >= 400:
                return {
                    "success": False,
                    "error": result.get("detail", f"HTTP {resp.status_code}"),
                }
            return result
        except httpx.ConnectError:
            logger.warning("ha-device-control unreachable at %s", self._base_url)
            return {"success": False, "error": "Device control service unavailable"}
        except httpx.TimeoutException:
            return {"success": False, "error": "Device control service timed out"}
        except Exception as exc:
            logger.error("Device control call failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def _get(self, path: str) -> dict[str, Any]:
        """GET from ha-device-control and return result."""
        if not self._client:
            return {"success": False, "error": "Device control service not initialized"}
        try:
            resp = await self._client.get(path)
            result = resp.json()
            if resp.status_code >= 400:
                return {
                    "success": False,
                    "error": result.get("detail", f"HTTP {resp.status_code}"),
                }
            return result
        except httpx.ConnectError:
            logger.warning("ha-device-control unreachable at %s", self._base_url)
            return {"success": False, "error": "Device control service unavailable"}
        except httpx.TimeoutException:
            return {"success": False, "error": "Device control service timed out"}
        except Exception as exc:
            logger.error("Device control call failed: %s", exc)
            return {"success": False, "error": str(exc)}
