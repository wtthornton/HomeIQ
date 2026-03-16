"""
HA Device Control Client for autonomous execution (Epic 68, Story 68.4).

Calls ha-device-control REST API for direct device manipulation.
Uses CrossGroupClient with circuit breaker for resilience.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx
from homeiq_resilience import CircuitBreaker, CircuitOpenError, CrossGroupClient

logger = logging.getLogger(__name__)

# Shared circuit breaker for ha-device-control
_device_control_breaker = CircuitBreaker(name="ha-device-control")


class DeviceControlClient:
    """Client for ha-device-control service — direct HA device manipulation."""

    def __init__(
        self,
        base_url: str = "http://ha-device-control:8040",
        timeout: int = 10,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        api_key = os.getenv("HA_AGENT_API_KEY") or os.getenv("SERVICE_AUTH_TOKEN")
        self._cross_client = CrossGroupClient(
            base_url=self.base_url,
            group_name="automation-core",
            timeout=float(timeout),
            max_retries=2,
            auth_token=api_key,
            circuit_breaker=_device_control_breaker,
        )
        logger.info("DeviceControlClient initialized: %s", self.base_url)

    async def get_house_status(self) -> dict[str, Any] | None:
        """Get full house state snapshot (used by observe step)."""
        try:
            response = await self._cross_client.call("GET", "/api/control/status")
            response.raise_for_status()
            return response.json()
        except CircuitOpenError:
            logger.warning("AI FALLBACK: ha-device-control circuit open")
            return None
        except (httpx.HTTPError, Exception) as e:
            logger.error("Failed to get house status: %s", e)
            return None

    async def control_light(
        self,
        entity_id_or_name: str,
        brightness: int = 100,
        rgb: list[int] | None = None,
    ) -> dict[str, Any] | None:
        """Control a light. brightness=0 means off."""
        payload: dict[str, Any] = {
            "entity_id_or_name": entity_id_or_name,
            "brightness": brightness,
        }
        if rgb:
            payload["rgb"] = rgb
        return await self._execute("POST", "/api/control/light", payload)

    async def control_switch(
        self,
        entity_id_or_name: str,
        state: str = "off",
    ) -> dict[str, Any] | None:
        """Control a switch (on/off)."""
        return await self._execute("POST", "/api/control/switch", {
            "entity_id_or_name": entity_id_or_name,
            "state": state,
        })

    async def control_climate(
        self,
        entity_id: str,
        temperature: float | None = None,
        hvac_mode: str | None = None,
    ) -> dict[str, Any] | None:
        """Set thermostat temperature and/or HVAC mode."""
        payload: dict[str, Any] = {"entity_id": entity_id}
        if temperature is not None:
            payload["temperature"] = temperature
        if hvac_mode is not None:
            payload["hvac_mode"] = hvac_mode
        return await self._execute("POST", "/api/control/climate", payload)

    async def activate_scene(self, name: str) -> dict[str, Any] | None:
        """Activate a scene or script by name."""
        return await self._execute("POST", "/api/control/scene", {"name": name})

    async def send_notification(
        self,
        message: str,
        title: str | None = None,
    ) -> dict[str, Any] | None:
        """Send a notification to the user via HA."""
        payload: dict[str, Any] = {"message": message}
        if title:
            payload["title"] = title
        return await self._execute("POST", "/api/control/notify", payload)

    async def get_entity_state(self, entity_id: str) -> dict[str, Any] | None:
        """Get current state of a specific entity (for pre/post snapshots)."""
        try:
            response = await self._cross_client.call(
                "GET", f"/api/control/devices",
            )
            response.raise_for_status()
            devices = response.json()
            for device in devices:
                if device.get("entity_id") == entity_id:
                    return device
            return None
        except (CircuitOpenError, httpx.HTTPError, Exception) as e:
            logger.error("Failed to get entity state for %s: %s", entity_id, e)
            return None

    async def _execute(
        self,
        method: str,
        path: str,
        payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Execute a device control action with error handling."""
        try:
            response = await self._cross_client.call(method, path, json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("success"):
                logger.info(
                    "Device control success: %s %s → %s",
                    method, path, result.get("message", "ok"),
                )
            else:
                logger.warning(
                    "Device control returned success=false: %s %s → %s",
                    method, path, result.get("message", "unknown"),
                )
            return result
        except CircuitOpenError:
            logger.warning("AI FALLBACK: ha-device-control circuit open for %s", path)
            return None
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP %d from ha-device-control %s: %s",
                e.response.status_code, path, e.response.text[:200],
            )
            return None
        except (httpx.HTTPError, Exception) as e:
            logger.error("Device control error %s: %s", path, e)
            return None

    async def close(self) -> None:
        """No-op — CrossGroupClient uses per-request clients."""
