"""
Device Health Analysis Service
Phase 1.2: Health analysis for devices
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class DeviceHealthService:
    """Service for analyzing device health"""

    def __init__(self):
        """Initialize health service"""
        self.ha_url = os.getenv("HA_URL") or os.getenv("HA_HTTP_URL")
        self.ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HA API session"""
        if self._session is None or self._session.closed:
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=10)
            self._session = aiohttp.ClientSession(
                headers=headers,
                timeout=timeout,
                raise_for_status=False
            )
        return self._session

    async def get_device_health(
        self,
        device_id: str,
        device_name: str,
        entity_ids: list[str],
        power_spec_w: float | None = None
    ) -> dict[str, Any]:
        """
        Get health report for a device.
        
        Args:
            device_id: Device identifier
            device_name: Device name
            entity_ids: List of entity IDs for this device
            power_spec_w: Expected power consumption
            
        Returns:
            Health report dictionary
        """
        if not self.ha_url or not self.ha_token:
            logger.warning("HA_URL or HA_TOKEN not configured, returning basic health report")
            return {
                "device_id": device_id,
                "device_name": device_name,
                "timestamp": datetime.now().isoformat(),
                "overall_status": "unknown",
                "issues": [],
                "maintenance_recommendations": []
            }

        issues = []
        recommendations = []

        try:
            session = await self._get_session()

            # Check battery levels
            battery_level = await self._get_battery_level(session, entity_ids)
            if battery_level is not None and battery_level < 20:
                issues.append({
                    "type": "low_battery",
                    "severity": "error" if battery_level < 10 else "warning",
                    "message": f"Battery level at {battery_level:.0f}%"
                })
                recommendations.append({
                    "title": "Replace or recharge battery",
                    "description": f"Device battery is at {battery_level:.0f}%",
                    "priority": "high" if battery_level < 10 else "medium"
                })

            # Check last seen
            last_seen = await self._get_last_seen(session, entity_ids)
            if last_seen:
                hours_ago = (datetime.now() - last_seen).total_seconds() / 3600
                if hours_ago > 24:
                    issues.append({
                        "type": "device_not_responding",
                        "severity": "error" if hours_ago > 48 else "warning",
                        "message": f"Device not seen in {hours_ago:.1f} hours"
                    })
                    recommendations.append({
                        "title": "Check device status",
                        "description": f"Device has not sent events in {hours_ago:.1f} hours",
                        "priority": "high" if hours_ago > 48 else "medium"
                    })

            # Determine overall status
            if any(issue["severity"] in ("error", "critical") for issue in issues):
                overall_status = "error"
            elif any(issue["severity"] == "warning" for issue in issues):
                overall_status = "warning"
            else:
                overall_status = "healthy"

            return {
                "device_id": device_id,
                "device_name": device_name,
                "timestamp": datetime.now().isoformat(),
                "overall_status": overall_status,
                "battery_level": battery_level,
                "last_seen": last_seen.isoformat() if last_seen else None,
                "issues": issues,
                "maintenance_recommendations": recommendations
            }

        except Exception as e:
            logger.error(f"Error analyzing device health: {e}")
            return {
                "device_id": device_id,
                "device_name": device_name,
                "timestamp": datetime.now().isoformat(),
                "overall_status": "error",
                "issues": [{
                    "type": "health_check_failed",
                    "severity": "error",
                    "message": f"Failed to analyze health: {str(e)}"
                }],
                "maintenance_recommendations": []
            }

    async def _get_battery_level(self, session: aiohttp.ClientSession, entity_ids: list[str]) -> float | None:
        """Get battery level from device entities"""
        for entity_id in entity_ids[:5]:  # Limit to first 5
            try:
                url = f"{self.ha_url}/api/states/{entity_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        state = await response.json()
                        attributes = state.get("attributes", {})
                        battery = attributes.get("battery_level") or attributes.get("battery")
                        if battery is not None:
                            return float(battery)
            except Exception:
                continue
        return None

    async def _get_last_seen(self, session: aiohttp.ClientSession, entity_ids: list[str]) -> datetime | None:
        """Get last seen timestamp from device entities"""
        latest = None
        for entity_id in entity_ids[:5]:  # Limit to first 5
            try:
                url = f"{self.ha_url}/api/states/{entity_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        state = await response.json()
                        last_changed = state.get("last_changed")
                        if last_changed:
                            try:
                                dt = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
                                if latest is None or dt > latest:
                                    latest = dt
                            except Exception:
                                pass
            except Exception:
                continue
        return latest


# Singleton instance
_health_service: DeviceHealthService | None = None


def get_health_service() -> DeviceHealthService:
    """Get singleton health service instance"""
    global _health_service
    if _health_service is None:
        _health_service = DeviceHealthService()
    return _health_service

