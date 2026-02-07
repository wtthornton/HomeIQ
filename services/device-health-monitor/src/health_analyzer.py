"""
Device Health Analyzer
Phase 1.2: Core health analysis logic
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from .ha_client import HAClient
from .models import HealthIssue, HealthSeverity, MaintenanceRecommendation

logger = logging.getLogger("device-health-monitor")


class HealthAnalyzer:
    """Analyzes device health from HA API data"""

    def __init__(self, ha_client: HAClient):
        """
        Initialize health analyzer.
        
        Args:
            ha_client: Home Assistant API client
        """
        self.ha_client = ha_client

    async def analyze_device_health(
        self,
        device_id: str,
        device_name: str,
        device_entities: list[str],
        power_spec_w: float | None = None,
        actual_power_w: float | None = None
    ) -> dict[str, Any]:
        """
        Analyze health for a single device.
        
        Args:
            device_id: Device identifier
            device_name: Device name
            device_entities: List of entity IDs for this device
            power_spec_w: Expected power consumption (from device spec)
            actual_power_w: Actual power consumption (from energy correlator)
            
        Returns:
            Health report dictionary
        """
        issues = []
        recommendations = []
        
        # Analyze response time
        response_time = await self._calculate_response_time(device_entities)
        if response_time and response_time > 5000.0:  # 5 seconds
            issues.append(HealthIssue(
                type="slow_response",
                severity=HealthSeverity.WARNING,
                message=f"Device responding slowly ({response_time:.0f}ms)",
                details={"response_time_ms": response_time}
            ))
            recommendations.append(MaintenanceRecommendation(
                title="Check device connectivity",
                description="Device is responding slowly. Check network connection and device status.",
                priority="medium",
                action="Check device network connection and restart if needed"
            ))
        
        # Check battery levels
        battery_level = await self._get_battery_level(device_entities)
        if battery_level is not None:
            if battery_level < 20:
                issues.append(HealthIssue(
                    type="low_battery",
                    severity=HealthSeverity.WARNING if battery_level > 10 else HealthSeverity.ERROR,
                    message=f"Battery level at {battery_level:.0f}%",
                    details={"battery_level": battery_level}
                ))
                recommendations.append(MaintenanceRecommendation(
                    title="Replace or recharge battery",
                    description=f"Device battery is at {battery_level:.0f}%. Consider replacing or recharging soon.",
                    priority="high" if battery_level < 10 else "medium",
                    action="Replace or recharge device battery"
                ))
        
        # Check last seen
        last_seen = await self._get_last_seen(device_entities)
        if last_seen:
            hours_ago = (datetime.now(timezone.utc) - last_seen).total_seconds() / 3600
            if hours_ago > 24:
                issues.append(HealthIssue(
                    type="device_not_responding",
                    severity=HealthSeverity.ERROR if hours_ago > 48 else HealthSeverity.WARNING,
                    message=f"Device not seen in {hours_ago:.1f} hours",
                    details={"hours_ago": hours_ago, "last_seen": last_seen.isoformat()}
                ))
                recommendations.append(MaintenanceRecommendation(
                    title="Check device status",
                    description=f"Device has not sent any events in {hours_ago:.1f} hours. Check power and network connection.",
                    priority="high" if hours_ago > 48 else "medium",
                    action="Check device power and network connection"
                ))
        
        # Check power consumption
        power_anomaly = False
        if power_spec_w and actual_power_w:
            if actual_power_w > power_spec_w * 1.5:
                power_anomaly = True
                issues.append(HealthIssue(
                    type="high_power_consumption",
                    severity=HealthSeverity.WARNING,
                    message=f"Device consuming {actual_power_w:.1f}W, expected {power_spec_w:.1f}W",
                    details={"actual_w": actual_power_w, "expected_w": power_spec_w}
                ))
                recommendations.append(MaintenanceRecommendation(
                    title="Investigate power consumption",
                    description=f"Device is consuming {actual_power_w:.1f}W, which is {((actual_power_w / power_spec_w - 1) * 100):.0f}% more than expected. May need maintenance.",
                    priority="medium",
                    action="Check device for issues or consider maintenance"
                ))
        
        # Determine overall status
        if any(issue.severity in (HealthSeverity.ERROR, HealthSeverity.CRITICAL) for issue in issues):
            overall_status = "error"
        elif any(issue.severity == HealthSeverity.WARNING for issue in issues):
            overall_status = "warning"
        else:
            overall_status = "healthy"
        
        return {
            "device_id": device_id,
            "device_name": device_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": overall_status,
            "response_time_ms": response_time,
            "battery_level": battery_level,
            "last_seen": last_seen.isoformat() if last_seen else None,
            "power_consumption_w": actual_power_w,
            "power_anomaly": power_anomaly,
            "issues": [issue.model_dump() for issue in issues],
            "maintenance_recommendations": [rec.model_dump() for rec in recommendations]
        }

    async def _calculate_response_time(self, entity_ids: list[str]) -> float | None:
        """Calculate average response time from recent state changes"""
        if not entity_ids:
            return None
        
        try:
            # Get history for last hour
            start_time = datetime.now(timezone.utc) - timedelta(hours=1)
            total_time = 0.0
            count = 0
            
            for entity_id in entity_ids[:5]:  # Limit to first 5 entities
                history = await self.ha_client.get_history(entity_id, start_time)
                if history:
                    # Calculate time between state changes
                    for i in range(1, len(history)):
                        prev_time = datetime.fromisoformat(history[i-1]["last_changed"].replace("Z", "+00:00"))
                        curr_time = datetime.fromisoformat(history[i]["last_changed"].replace("Z", "+00:00"))
                        delta = (curr_time - prev_time).total_seconds() * 1000  # Convert to ms
                        if delta < 10000:  # Ignore very long gaps
                            total_time += delta
                            count += 1
            
            if count > 0:
                return total_time / count
            return None
        except Exception as e:
            logger.error(f"Error calculating response time: {e}")
            return None

    async def _get_battery_level(self, entity_ids: list[str]) -> float | None:
        """Get battery level from device entities"""
        for entity_id in entity_ids:
            state = await self.ha_client.get_state(entity_id)
            if state:
                attributes = state.get("attributes", {})
                battery = attributes.get("battery_level") or attributes.get("battery")
                if battery is not None:
                    return float(battery)
        return None

    async def _get_last_seen(self, entity_ids: list[str]) -> datetime | None:
        """Get last seen timestamp from device entities"""
        latest = None
        for entity_id in entity_ids:
            state = await self.ha_client.get_state(entity_id)
            if state:
                last_changed = state.get("last_changed")
                if last_changed:
                    try:
                        dt = datetime.fromisoformat(last_changed.replace("Z", "+00:00"))
                        if latest is None or dt > latest:
                            latest = dt
                    except Exception:
                        pass
        return latest

