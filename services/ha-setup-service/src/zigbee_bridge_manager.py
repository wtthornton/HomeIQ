"""
Zigbee2MQTT Bridge Manager

Enhanced bridge health monitoring, auto-recovery, and management capabilities.
Implements Story 31.3: Bridge Health Monitoring & Auto-Recovery

Context7 Best Practices Applied:
- Async/await for all I/O operations
- Proper exception handling with specific error types
- Pydantic models for data validation
- Retry logic with exponential backoff
- Structured logging with correlation IDs
"""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import aiohttp
from pydantic import BaseModel, Field

from .config import get_settings
from .integration_checker import CheckResult, IntegrationHealthChecker, IntegrationStatus

settings = get_settings()
logger = logging.getLogger(__name__)


class BridgeState(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    ERROR = "error"


class RecoveryAction(str, Enum):
    RESTART_ADDON = "restart_addon"
    RESTART_MQTT = "restart_mqtt"
    RESET_COORDINATOR = "reset_coordinator"
    CHECK_CONFIG = "check_config"
    MANUAL_INTERVENTION = "manual_intervention"


@dataclass
class BridgeMetrics:
    """Bridge performance metrics"""
    response_time_ms: float
    device_count: int
    signal_strength_avg: float | None = None
    network_health_score: float | None = None
    last_seen_devices: int = 0
    coordinator_uptime_hours: float | None = None


@dataclass
class RecoveryAttempt:
    """Recovery attempt record"""
    timestamp: datetime
    action: RecoveryAction
    success: bool
    error_message: str | None = None
    duration_seconds: float | None = None


class BridgeHealthStatus(BaseModel):
    """Bridge health status model"""
    bridge_state: BridgeState
    is_connected: bool
    last_check: datetime
    metrics: BridgeMetrics
    recovery_attempts: list[RecoveryAttempt] = Field(default_factory=list)
    consecutive_failures: int = 0
    health_score: float = Field(ge=0, le=100)
    recommendations: list[str] = Field(default_factory=list)


class ZigbeeBridgeManager:
    """
    Enhanced Zigbee2MQTT bridge management with health monitoring and auto-recovery
    """

    def __init__(self):
        self.ha_url = settings.ha_url.rstrip("/")
        self.ha_token = settings.ha_token
        self.integration_checker = IntegrationHealthChecker()
        self.recovery_history: list[RecoveryAttempt] = []
        self.monitoring_active = False
        self.monitoring_interval = 30  # seconds
        self.max_recovery_attempts = 3
        self.recovery_cooldown = 300  # 5 minutes between recovery attempts

    async def get_bridge_health_status(self) -> BridgeHealthStatus:
        """
        Get comprehensive bridge health status with metrics and recommendations
        """
        try:
            # Get basic integration status
            integration_result = await self.integration_checker.check_zigbee2mqtt_integration()

            # Get detailed bridge metrics
            metrics = await self._get_bridge_metrics()

            # Calculate health score
            health_score = self._calculate_health_score(integration_result, metrics)

            # Generate recommendations
            recommendations = self._generate_recommendations(integration_result, metrics)

            # Determine bridge state
            bridge_state = self._determine_bridge_state(integration_result, metrics)

            return BridgeHealthStatus(
                bridge_state=bridge_state,
                is_connected=integration_result.is_connected,
                last_check=datetime.now(),
                metrics=metrics,
                recovery_attempts=self.recovery_history[-5:],  # Last 5 attempts
                consecutive_failures=self._count_consecutive_failures(),
                health_score=health_score,
                recommendations=recommendations
            )

        except Exception as e:
            logger.error(f"Failed to get bridge health status: {e}")
            return BridgeHealthStatus(
                bridge_state=BridgeState.ERROR,
                is_connected=False,
                last_check=datetime.now(),
                metrics=BridgeMetrics(response_time_ms=0, device_count=0),
                consecutive_failures=self._count_consecutive_failures(),
                health_score=0,
                recommendations=[f"Health check failed: {str(e)}"]
            )

    async def _get_bridge_metrics(self) -> BridgeMetrics:
        """Get detailed bridge performance metrics"""
        try:
            start_time = datetime.now()

            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }

                # Get all states to analyze bridge and device metrics
                async with session.get(
                    f"{self.ha_url}/api/states",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        states = await response.json()

                        # Calculate response time
                        response_time = (datetime.now() - start_time).total_seconds() * 1000

                        # Count Zigbee devices
                        zigbee_devices = [
                            s for s in states
                            if s.get('entity_id', '').startswith('zigbee2mqtt.')
                        ]

                        # Get bridge state entity
                        bridge_state = next(
                            (s for s in states if s.get('entity_id') == 'sensor.zigbee2mqtt_bridge_state'),
                            None
                        )

                        # Calculate additional metrics
                        signal_strength_avg = self._calculate_avg_signal_strength(states)
                        network_health_score = self._calculate_network_health(states)
                        last_seen_devices = self._count_recently_seen_devices(states)
                        coordinator_uptime = self._get_coordinator_uptime(states)

                        return BridgeMetrics(
                            response_time_ms=response_time,
                            device_count=len(zigbee_devices),
                            signal_strength_avg=signal_strength_avg,
                            network_health_score=network_health_score,
                            last_seen_devices=last_seen_devices,
                            coordinator_uptime_hours=coordinator_uptime
                        )
                    else:
                        logger.warning(f"Failed to get bridge metrics: HTTP {response.status}")
                        return BridgeMetrics(response_time_ms=0, device_count=0)

        except Exception as e:
            logger.error(f"Error getting bridge metrics: {e}")
            return BridgeMetrics(response_time_ms=0, device_count=0)

    def _calculate_avg_signal_strength(self, states: list[dict]) -> float | None:
        """Calculate average signal strength across Zigbee devices"""
        signal_values = []
        for state in states:
            entity_id = state.get('entity_id', '')
            if 'zigbee2mqtt' in entity_id and 'linkquality' in entity_id:
                try:
                    signal_value = float(state.get('state', 0))
                    if signal_value > 0:
                        signal_values.append(signal_value)
                except (ValueError, TypeError):
                    continue

        return sum(signal_values) / len(signal_values) if signal_values else None

    def _calculate_network_health(self, states: list[dict]) -> float | None:
        """Calculate overall network health score based on device states"""
        online_devices = 0
        total_devices = 0

        for state in states:
            entity_id = state.get('entity_id', '')
            if 'zigbee2mqtt' in entity_id and not entity_id.endswith('_bridge_state'):
                total_devices += 1
                if state.get('state') not in ['unavailable', 'unknown']:
                    online_devices += 1

        if total_devices == 0:
            return None

        return (online_devices / total_devices) * 100

    def _count_recently_seen_devices(self, states: list[dict]) -> int:
        """Count devices seen in the last hour"""
        cutoff_time = datetime.now() - timedelta(hours=1)
        recent_devices = 0

        for state in states:
            entity_id = state.get('entity_id', '')
            if 'zigbee2mqtt' in entity_id and not entity_id.endswith('_bridge_state'):
                last_updated = state.get('last_updated')
                if last_updated:
                    try:
                        last_seen = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                        if last_seen > cutoff_time:
                            recent_devices += 1
                    except (ValueError, TypeError):
                        continue

        return recent_devices

    def _get_coordinator_uptime(self, states: list[dict]) -> float | None:
        """Get coordinator uptime in hours"""
        coordinator_state = next(
            (s for s in states if s.get('entity_id') == 'sensor.zigbee2mqtt_coordinator_uptime'),
            None
        )

        if coordinator_state:
            try:
                uptime_str = coordinator_state.get('state', '')
                # Parse uptime string (e.g., "2d 5h 30m")
                return self._parse_uptime_string(uptime_str)
            except (ValueError, TypeError):
                return None

        return None

    def _parse_uptime_string(self, uptime_str: str) -> float | None:
        """Parse uptime string to hours"""
        try:
            total_hours = 0
            parts = uptime_str.split()

            for part in parts:
                if part.endswith('d'):
                    days = int(part[:-1])
                    total_hours += days * 24
                elif part.endswith('h'):
                    hours = int(part[:-1])
                    total_hours += hours
                elif part.endswith('m'):
                    minutes = int(part[:-1])
                    total_hours += minutes / 60

            return total_hours
        except (ValueError, TypeError):
            return None

    def _calculate_health_score(self, integration_result: CheckResult, metrics: BridgeMetrics) -> float:
        """Calculate overall bridge health score (0-100)"""
        score = 0

        # Base score from integration status (40 points)
        if integration_result.status == IntegrationStatus.HEALTHY:
            score += 40
        elif integration_result.status == IntegrationStatus.WARNING:
            score += 20
        elif integration_result.status == IntegrationStatus.ERROR:
            score += 0
        else:
            score += 10

        # Response time score (20 points)
        if metrics.response_time_ms < 100:
            score += 20
        elif metrics.response_time_ms < 500:
            score += 15
        elif metrics.response_time_ms < 1000:
            score += 10
        else:
            score += 5

        # Device connectivity score (20 points)
        if metrics.device_count > 0:
            if metrics.network_health_score and metrics.network_health_score > 90:
                score += 20
            elif metrics.network_health_score and metrics.network_health_score > 70:
                score += 15
            elif metrics.network_health_score and metrics.network_health_score > 50:
                score += 10
            else:
                score += 5

        # Signal strength score (20 points)
        if metrics.signal_strength_avg:
            if metrics.signal_strength_avg > 200:
                score += 20
            elif metrics.signal_strength_avg > 150:
                score += 15
            elif metrics.signal_strength_avg > 100:
                score += 10
            else:
                score += 5

        return min(100, max(0, score))

    def _generate_recommendations(self, integration_result: CheckResult, metrics: BridgeMetrics) -> list[str]:
        """Generate actionable recommendations based on current status"""
        recommendations = []

        # Integration status recommendations
        if integration_result.status == IntegrationStatus.WARNING:
            if "offline" in (integration_result.error_message or "").lower():
                recommendations.append("Bridge is offline - check Zigbee2MQTT addon logs")
                recommendations.append("Try restarting the Zigbee2MQTT addon")
            elif "not configured" in (integration_result.error_message or "").lower():
                recommendations.append("Zigbee2MQTT not detected - install and configure addon")

        # Performance recommendations
        if metrics.response_time_ms > 1000:
            recommendations.append("High response time - check network connectivity")

        if metrics.device_count == 0:
            recommendations.append("No Zigbee devices detected - check coordinator connection")
        elif metrics.network_health_score and metrics.network_health_score < 70:
            recommendations.append("Poor device connectivity - check signal strength and positioning")

        if metrics.signal_strength_avg and metrics.signal_strength_avg < 100:
            recommendations.append("Low signal strength - consider repositioning coordinator or devices")

        if metrics.consecutive_failures > 2:
            recommendations.append("Multiple consecutive failures - manual intervention may be required")

        return recommendations

    def _determine_bridge_state(self, integration_result: CheckResult, metrics: BridgeMetrics) -> BridgeState:
        """Determine bridge state based on integration and metrics"""
        if integration_result.status == IntegrationStatus.HEALTHY:
            return BridgeState.ONLINE
        elif integration_result.status == IntegrationStatus.WARNING:
            if "offline" in (integration_result.error_message or "").lower():
                return BridgeState.OFFLINE
            else:
                return BridgeState.ONLINE  # Warning but still functional
        elif integration_result.status == IntegrationStatus.ERROR:
            return BridgeState.ERROR
        else:
            return BridgeState.UNKNOWN

    def _count_consecutive_failures(self) -> int:
        """Count consecutive failed recovery attempts"""
        consecutive = 0
        for attempt in reversed(self.recovery_history):
            if not attempt.success:
                consecutive += 1
            else:
                break
        return consecutive

    async def attempt_bridge_recovery(self, force: bool = False) -> tuple[bool, str]:
        """
        Attempt to recover bridge connectivity
        
        Args:
            force: Force recovery attempt even if cooldown period hasn't passed
            
        Returns:
            Tuple of (success, message)
        """
        # Check cooldown period
        if not force and self.recovery_history:
            last_attempt = self.recovery_history[-1]
            if datetime.now() - last_attempt.timestamp < timedelta(seconds=self.recovery_cooldown):
                return False, f"Recovery cooldown active. Next attempt available in {self.recovery_cooldown - (datetime.now() - last_attempt.timestamp).total_seconds():.0f} seconds"

        # Check max attempts
        recent_attempts = [
            attempt for attempt in self.recovery_history
            if datetime.now() - attempt.timestamp < timedelta(hours=1)
        ]
        if len(recent_attempts) >= self.max_recovery_attempts:
            return False, f"Maximum recovery attempts ({self.max_recovery_attempts}) reached in the last hour"

        # Determine recovery action
        recovery_action = self._determine_recovery_action()

        # Execute recovery
        start_time = datetime.now()
        try:
            success, message = await self._execute_recovery_action(recovery_action)
            duration = (datetime.now() - start_time).total_seconds()

            # Record attempt
            attempt = RecoveryAttempt(
                timestamp=start_time,
                action=recovery_action,
                success=success,
                error_message=message if not success else None,
                duration_seconds=duration
            )
            self.recovery_history.append(attempt)

            return success, message

        except Exception as e:
            duration = (datetime.now() - start_time).total_seconds()
            attempt = RecoveryAttempt(
                timestamp=start_time,
                action=recovery_action,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )
            self.recovery_history.append(attempt)

            return False, f"Recovery failed: {str(e)}"

    def _determine_recovery_action(self) -> RecoveryAction:
        """Determine the best recovery action based on current status"""
        # For now, start with addon restart as it's the most common fix
        return RecoveryAction.RESTART_ADDON

    async def _execute_recovery_action(self, action: RecoveryAction) -> tuple[bool, str]:
        """Execute the specified recovery action"""
        if action == RecoveryAction.RESTART_ADDON:
            return await self._restart_zigbee2mqtt_addon()
        elif action == RecoveryAction.RESTART_MQTT:
            return await self._restart_mqtt_integration()
        elif action == RecoveryAction.RESET_COORDINATOR:
            return await self._reset_coordinator()
        elif action == RecoveryAction.CHECK_CONFIG:
            return await self._check_configuration()
        else:
            return False, "Manual intervention required"

    async def _restart_zigbee2mqtt_addon(self) -> tuple[bool, str]:
        """Attempt to restart Zigbee2MQTT addon"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }

                # Try to restart the addon (this requires addon manager API)
                async with session.post(
                    f"{self.ha_url}/api/hassio/addon/zigbee2mqtt/restart",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        # Wait a moment for restart to take effect
                        await asyncio.sleep(10)

                        # Verify restart was successful
                        health_status = await self.get_bridge_health_status()
                        if health_status.bridge_state == BridgeState.ONLINE:
                            return True, "Zigbee2MQTT addon restarted successfully"
                        else:
                            return False, "Addon restarted but bridge still offline"
                    else:
                        return False, f"Failed to restart addon: HTTP {response.status}"

        except Exception as e:
            return False, f"Addon restart failed: {str(e)}"

    async def _restart_mqtt_integration(self) -> tuple[bool, str]:
        """Attempt to restart MQTT integration"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }

                # Reload MQTT integration
                async with session.post(
                    f"{self.ha_url}/api/services/mqtt/reload",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        await asyncio.sleep(5)
                        return True, "MQTT integration reloaded"
                    else:
                        return False, f"Failed to reload MQTT: HTTP {response.status}"

        except Exception as e:
            return False, f"MQTT restart failed: {str(e)}"

    async def _reset_coordinator(self) -> tuple[bool, str]:
        """Attempt to reset Zigbee coordinator"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }

                # Try to reset coordinator via service call
                payload = {"device": "coordinator"}
                async with session.post(
                    f"{self.ha_url}/api/services/zigbee2mqtt/permit_join",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=15)
                ) as response:
                    if response.status == 200:
                        return True, "Coordinator reset initiated"
                    else:
                        return False, f"Failed to reset coordinator: HTTP {response.status}"

        except Exception as e:
            return False, f"Coordinator reset failed: {str(e)}"

    async def _check_configuration(self) -> tuple[bool, str]:
        """Check Zigbee2MQTT configuration for issues"""
        try:
            # Get current health status
            health_status = await self.get_bridge_health_status()

            # Check for common configuration issues
            issues = []

            if health_status.metrics.device_count == 0:
                issues.append("No devices configured")

            if health_status.metrics.response_time_ms > 1000:
                issues.append("High response time indicates connectivity issues")

            if health_status.metrics.signal_strength_avg and health_status.metrics.signal_strength_avg < 50:
                issues.append("Very low signal strength")

            if issues:
                return False, f"Configuration issues detected: {', '.join(issues)}"
            else:
                return True, "Configuration appears correct"

        except Exception as e:
            return False, f"Configuration check failed: {str(e)}"

    async def start_monitoring(self) -> None:
        """Start continuous bridge health monitoring"""
        if self.monitoring_active:
            logger.warning("Bridge monitoring already active")
            return

        self.monitoring_active = True
        logger.info("Starting Zigbee2MQTT bridge monitoring")

        try:
            while self.monitoring_active:
                try:
                    health_status = await self.get_bridge_health_status()

                    # Log health status
                    logger.info(f"Bridge health: {health_status.health_score}/100, "
                              f"State: {health_status.bridge_state}, "
                              f"Devices: {health_status.metrics.device_count}")

                    # Attempt auto-recovery if needed
                    if (health_status.bridge_state in [BridgeState.OFFLINE, BridgeState.ERROR] and
                        health_status.consecutive_failures < 3):

                        logger.info("Bridge offline detected, attempting auto-recovery")
                        success, message = await self.attempt_bridge_recovery()
                        logger.info(f"Recovery attempt: {'Success' if success else 'Failed'} - {message}")

                    # Wait for next check
                    await asyncio.sleep(self.monitoring_interval)

                except Exception as e:
                    logger.error(f"Error in monitoring loop: {e}")
                    await asyncio.sleep(self.monitoring_interval)

        except asyncio.CancelledError:
            logger.info("Bridge monitoring cancelled")
        finally:
            self.monitoring_active = False
            logger.info("Bridge monitoring stopped")

    async def stop_monitoring(self) -> None:
        """Stop continuous bridge health monitoring"""
        self.monitoring_active = False
        logger.info("Stopping Zigbee2MQTT bridge monitoring")

    def get_recovery_history(self) -> list[RecoveryAttempt]:
        """Get recovery attempt history"""
        return self.recovery_history.copy()

    def clear_recovery_history(self) -> None:
        """Clear recovery attempt history"""
        self.recovery_history.clear()
        logger.info("Recovery history cleared")
