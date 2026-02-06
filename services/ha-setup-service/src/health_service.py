"""
Health monitoring service implementation

Context7 Best Practices Applied:
- Async/await for all I/O operations
- Proper exception handling
- Type hints throughout
"""
import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import aiohttp
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .integration_checker import IntegrationHealthChecker
from .models import EnvironmentHealth
from .schemas import (
    EnvironmentHealthResponse,
    HealthStatus,
    IntegrationHealthDetail,
    IntegrationStatus,
    PerformanceMetrics,
)
from .http_client import get_http_session
from .scoring_algorithm import HealthScoringAlgorithm

settings = get_settings()
logger = logging.getLogger(__name__)


class HealthMonitoringService:
    """
    Core health monitoring service
    
    Implements Context7 async patterns for Home Assistant health checks.
    Note: Zigbee2MQTT is not checked separately - it uses the same MQTT broker
    as the MQTT integration, just with a different topic prefix.
    """

    def __init__(self):
        self.ha_url = settings.ha_url.rstrip("/")
        self.ha_token = settings.ha_token
        self.data_api_url = settings.data_api_url
        self.admin_api_url = settings.admin_api_url
        self.scoring_algorithm = HealthScoringAlgorithm()  # Enhanced scoring
        logger.info(f"HealthMonitoringService initialized: URL={self.ha_url}, Token={'SET' if self.ha_token else 'NOT SET'}")

    async def check_environment_health(
        self,
        db: AsyncSession
    ) -> EnvironmentHealthResponse:
        """
        Comprehensive environment health check
        
        Args:
            db: Async database session
            
        Returns:
            EnvironmentHealthResponse with complete health status
        """
        # Run all health checks in parallel (Context7 best practice)
        ha_check, integrations_check, performance_check = await asyncio.gather(
            self._check_ha_core(),
            self._check_integrations(),
            self._check_performance(),
            return_exceptions=True
        )

        # Handle exceptions gracefully
        if isinstance(ha_check, Exception):
            logger.error(f"HA core check raised exception: {ha_check}", exc_info=ha_check)
            ha_status = {"status": "error", "version": "unknown", "error": str(ha_check)}
        else:
            ha_status = ha_check
            # Log the actual result to see what we're getting
            logger.info(f"HA core check result: status={ha_status.get('status')}, version={ha_status.get('version')}, error={ha_status.get('error', 'None')}")
        integrations = integrations_check if not isinstance(integrations_check, Exception) else []
        performance = performance_check if not isinstance(performance_check, Exception) else {
            "response_time_ms": 0,
            "cpu_usage_percent": 0,
            "memory_usage_mb": 0,
            "uptime_seconds": 0
        }

        # Calculate overall health score using enhanced algorithm
        health_score, component_scores = self.scoring_algorithm.calculate_score(
            ha_status,
            integrations,
            performance
        )

        # Log health score calculation breakdown for debugging
        logger.info(
            "Health check completed",
            extra={
                "health_score": health_score,
                "component_scores": component_scores,
                "ha_status": ha_status.get("status"),
                "ha_version": ha_status.get("version"),
                "ha_error": ha_status.get("error"),
                "integration_count": len(integrations),
                "performance": performance,
            }
        )

        # Detect issues
        issues = self._detect_issues(ha_status, integrations, performance)

        # Determine overall status
        overall_status = self._determine_overall_status(health_score, issues)
        
        logger.info(
            "Health status determined",
            extra={
                "overall_status": overall_status,
                "health_score": health_score,
                "issues_count": len(issues),
                "issues": issues
            }
        )

        # Store health metric in database
        await self._store_health_metric(
            db,
            health_score,
            overall_status,
            ha_status.get("version"),
            integrations,
            performance,
            issues
        )

        # Normalize integrations to schema shape
        normalized_integrations: list[IntegrationHealthDetail] = []
        for integration in integrations:
            status_value: Any = integration.get("status", IntegrationStatus.ERROR.value)
            if isinstance(status_value, IntegrationStatus):
                status_value = status_value.value

            detail_data: dict = {
                "name": integration.get("name", "Unknown Integration"),
                "type": integration.get("type", "unknown"),
                "status": status_value,
                "is_configured": integration.get("is_configured", False),
                "is_connected": integration.get("is_connected", False),
                "error_message": integration.get("error_message"),
                "last_check": integration.get("last_check")
            }

            if "check_details" in integration:
                detail_data["check_details"] = integration.get("check_details")

            try:
                normalized_integrations.append(IntegrationHealthDetail(**detail_data))
            except Exception as exc:  # ValidationError or unexpected issue
                logger.warning(
                    "Failed to normalize integration detail; using fallback",
                    extra={
                        "integration": integration,
                        "error": str(exc)
                    }
                )
                normalized_integrations.append(
                    IntegrationHealthDetail(
                        name=detail_data["name"],
                        type=detail_data["type"],
                        status=IntegrationStatus.ERROR,
                        is_configured=detail_data["is_configured"],
                        is_connected=detail_data["is_connected"],
                        error_message=detail_data.get("error_message") or str(exc),
                        check_details=None,
                        last_check=detail_data.get("last_check")
                    )
                )

        # Build response
        return EnvironmentHealthResponse(
            health_score=health_score,
            ha_status=HealthStatus(overall_status),
            ha_version=ha_status.get("version"),
            integrations=normalized_integrations,
            performance=PerformanceMetrics(**performance),
            issues_detected=issues,
            timestamp=datetime.now(timezone.utc)
        )

    async def _check_ha_core(self) -> dict:
        """Check Home Assistant core status"""
        # Use direct method - we know this works from container tests
        try:
            result = await self._check_ha_core_direct()
            logger.info(f"_check_ha_core returning: {result}")
            return result
        except Exception as e:
            logger.error(f"_check_ha_core exception: {e}", exc_info=True)
            return {"status": "error", "version": "unknown", "error": str(e)}

    async def _check_ha_core_direct(self) -> dict:
        """Direct HA core check - uses same approach as working container test"""
        try:
            ha_url = self.ha_url
            ha_token = self.ha_token

            logger.info("HA core check starting", extra={"ha_url": ha_url, "token_configured": bool(ha_token)})

            if not ha_token:
                logger.warning("HA core check: No token available")
                return {
                    "status": "warning",
                    "version": "unknown",
                    "error": "HA_TOKEN not configured. Set HA_TOKEN or HOME_ASSISTANT_TOKEN environment variable."
                }

            session = await get_http_session()
            headers = {
                "Authorization": f"Bearer {ha_token}",
                "Content-Type": "application/json"
            }

            url = f"{ha_url}/api/config"
            logger.info(f"HA core check: Calling {url}")

            # Check HA API availability and get config (includes version)
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                logger.info(f"HA core check: Response status={response.status}")

                if response.status == 200:
                    data = await response.json()
                    version = data.get("version", "unknown")
                    logger.info(f"HA core check: API returned version={version}, data keys={list(data.keys())[:5]}")
                    # Always return the version we got from the API
                    return {
                        "status": "healthy" if version and version != "unknown" else "warning",
                        "version": version
                    }
                elif response.status == 401:
                    logger.warning("HA core check: Authentication failed (401)")
                    # Try to extract version from error response if available
                    try:
                        error_data = await response.json()
                        version = error_data.get("version")
                        if version:
                            return {
                                "status": "warning",
                                "version": version,
                                "error": "Authentication failed - invalid token"
                            }
                    except (aiohttp.ContentTypeError, ValueError, KeyError):
                        pass
                    return {
                        "status": "warning",
                        "version": "unknown",
                        "error": "Authentication failed - check HA_TOKEN configuration"
                    }
                else:
                    logger.warning(f"HA core check: Unexpected status {response.status}")
                    # Try to extract version from error response if available
                    try:
                        error_data = await response.json()
                        version = error_data.get("version")
                        if version:
                            return {
                                "status": "warning",
                                "version": version,
                                "error": f"HTTP {response.status}"
                            }
                    except (aiohttp.ContentTypeError, ValueError, KeyError):
                        pass
                    text = await response.text()
                    logger.debug(f"Response: {text[:200]}")
                    return {
                        "status": "warning",
                        "version": "unknown",
                        "error": f"HTTP {response.status}"
                    }
        except asyncio.TimeoutError as e:
            logger.warning(f"HA core check: Timeout - {e}")
            return {"status": "warning", "version": "unknown", "error": "Timeout"}
        except Exception as e:
            logger.error(f"HA core check failed: {e}", exc_info=True)
            return {"status": "warning", "version": "unknown", "error": str(e)}

    async def _check_integrations(self) -> list[dict]:
        """
        Check all integrations status - always returns at least MQTT and Data API
        
        Note: Zigbee2MQTT uses the same MQTT broker, so if MQTT is healthy,
        Zigbee2MQTT can work (it's just a different topic prefix)
        """
        integrations = []

        # Check MQTT integration (always include, even if check fails)
        try:
            mqtt_status = await self._check_mqtt_integration()
            integrations.append(mqtt_status)
        except Exception as e:
            logger.error(f"MQTT check failed: {e}", exc_info=True)
            integrations.append({
                "name": "MQTT",
                "type": "mqtt",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": False,
                "is_connected": False,
                "error_message": str(e),
                "last_check": datetime.now(timezone.utc)
            })

        # Check HA Ingestor services (always include, even if check fails)
        try:
            data_api_status = await self._check_data_api()
            integrations.append(data_api_status)
        except Exception as e:
            logger.error(f"Data API check failed: {e}", exc_info=True)
            integrations.append({
                "name": "Data API",
                "type": "homeiq",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": True,  # Service exists, just not reachable
                "is_connected": False,
                "error_message": str(e),
                "last_check": datetime.now(timezone.utc)
            })

        return integrations

    async def _check_mqtt_integration(self) -> dict:
        """Check MQTT broker status"""
        try:
            session = await get_http_session()
            headers = {
                "Authorization": f"Bearer {self.ha_token}",
                "Content-Type": "application/json"
            }

            # Check MQTT config entry
            async with session.get(
                f"{self.ha_url}/api/config/config_entries/entry",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        entries = await response.json()
                        mqtt_entry = next((e for e in entries if e.get('domain') == 'mqtt'), None)

                        if mqtt_entry:
                            return {
                                "name": "MQTT",
                                "type": "mqtt",
                                "status": IntegrationStatus.HEALTHY.value,
                                "is_configured": True,
                                "is_connected": True,
                                "error_message": None,
                                "last_check": datetime.now(timezone.utc)
                            }
                        else:
                            return {
                                "name": "MQTT",
                                "type": "mqtt",
                                "status": IntegrationStatus.NOT_CONFIGURED.value,
                                "is_configured": False,
                                "is_connected": False,
                                "error_message": "MQTT integration not found",
                                "last_check": datetime.now(timezone.utc)
                            }

                    # Non-200 responses should produce a structured error result
                    return {
                        "name": "MQTT",
                        "type": "mqtt",
                        "status": IntegrationStatus.ERROR.value,
                        "is_configured": False,
                        "is_connected": False,
                        "error_message": f"Failed to fetch config entries: HTTP {response.status}",
                        "last_check": datetime.now(timezone.utc)
                    }
        except Exception as e:
            return {
                "name": "MQTT",
                "type": "mqtt",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": False,
                "is_connected": False,
                "error_message": str(e),
                "last_check": datetime.now(timezone.utc)
            }

    async def _check_zigbee2mqtt_integration(self) -> dict:
        """
        Check Zigbee2MQTT status using Home Assistant API.
        
        Uses HA API to check for Zigbee2MQTT entities, which is simpler
        and more reliable than MQTT subscription for health monitoring.
        """
        try:
            integration_checker = IntegrationHealthChecker()
            result = await integration_checker.check_zigbee2mqtt_integration()

            return {
                "name": result.integration_name,
                "type": result.integration_type,
                "status": result.status.value,
                "is_configured": result.is_configured,
                "is_connected": result.is_connected,
                "error_message": result.error_message,
                "check_details": {
                    **(result.check_details or {}),
                    "monitoring_method": "ha_api"
                },
                "last_check": result.last_check
            }
        except Exception as e:
            return {
                "name": "Zigbee2MQTT",
                "type": "zigbee2mqtt",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": False,
                "is_connected": False,
                "error_message": f"HA API check failed: {str(e)}",
                "check_details": {"error_type": type(e).__name__},
                "last_check": datetime.now(timezone.utc)
            }

    async def _check_data_api(self) -> dict:
        """Check HA Ingestor Data API status"""
        try:
            session = await get_http_session()
            async with session.get(
                f"{self.data_api_url}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status == 200:
                    return {
                        "name": "Data API",
                        "type": "homeiq",
                        "status": IntegrationStatus.HEALTHY.value,
                        "is_configured": True,
                        "is_connected": True,
                        "error_message": None,
                        "last_check": datetime.now(timezone.utc)
                    }
                # Surface non-200 responses as warning/error data instead of None
                return {
                    "name": "Data API",
                    "type": "homeiq",
                    "status": IntegrationStatus.WARNING.value,
                    "is_configured": True,
                    "is_connected": False,
                    "error_message": f"Health endpoint returned HTTP {response.status}",
                    "last_check": datetime.now(timezone.utc)
                }
        except Exception as e:
            return {
                "name": "Data API",
                "type": "homeiq",
                "status": IntegrationStatus.ERROR.value,
                "is_configured": True,
                "is_connected": False,
                "error_message": str(e),
                "last_check": datetime.now(timezone.utc)
            }

    async def _check_performance(self) -> dict:
        """Check system performance metrics using real system data"""
        try:
            import time
            import psutil

            process = psutil.Process()

            # Measure actual HA response time
            response_time_ms = 0.0
            try:
                session = await get_http_session()
                headers = {
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
                start = time.monotonic()
                async with session.get(
                    f"{self.ha_url}/api/",
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    response_time_ms = round((time.monotonic() - start) * 1000, 2)
            except Exception:
                response_time_ms = 0.0

            mem_info = process.memory_info()
            performance = {
                "response_time_ms": response_time_ms,
                "cpu_usage_percent": process.cpu_percent(),
                "memory_usage_mb": round(mem_info.rss / 1024 / 1024, 1),
                "uptime_seconds": int(time.time() - process.create_time())
            }
            logger.debug(f"Performance metrics: {performance}")
            return performance
        except Exception as e:
            logger.error(f"Performance check failed: {e}", exc_info=True)
            # Return minimal valid performance data
            return {
                "response_time_ms": 0.0,
                "cpu_usage_percent": None,
                "memory_usage_mb": None,
                "uptime_seconds": None
            }

    def _detect_issues(
        self,
        ha_status: dict,
        integrations: list[dict],
        performance: dict
    ) -> list[str]:
        """Detect and list issues"""
        issues = []

        if ha_status.get("status") != "healthy":
            issues.append(f"Home Assistant core status: {ha_status.get('status')}")

        for integration in integrations:
            # Skip Zigbee2MQTT - it's just MQTT with a different topic, not a separate integration
            if integration.get("type") == "zigbee2mqtt":
                continue

            if integration.get("status") != IntegrationStatus.HEALTHY.value:
                issues.append(
                    f"{integration.get('name')} integration: {integration.get('status')} "
                    f"({integration.get('error_message', 'No details')})"
                )

        response_time = performance.get("response_time_ms", 0)
        if response_time > 1000:
            issues.append(f"High response time: {response_time}ms")

        return issues

    def _determine_overall_status(self, health_score: int, issues: list[str]) -> str:
        """Determine overall health status based on score thresholds"""
        if health_score >= 80:
            return HealthStatus.HEALTHY.value
        elif health_score >= 50:
            return HealthStatus.WARNING.value
        else:
            return HealthStatus.CRITICAL.value

    async def _store_health_metric(
        self,
        db: AsyncSession,
        health_score: int,
        status: str,
        ha_version: str | None,
        integrations: list[dict],
        performance: dict,
        issues: list[str]
    ):
        """Store health metric in database"""
        try:
            health_metric = EnvironmentHealth(
                health_score=health_score,
                ha_status=status,
                ha_version=ha_version,
                integrations_status=[
                    {
                        "name": i.get("name"),
                        "status": i.get("status"),
                        "is_connected": i.get("is_connected")
                    }
                    for i in integrations
                ],
                performance_metrics=performance,
                issues_detected=issues
            )

            db.add(health_metric)
            await db.commit()
            await db.refresh(health_metric)

        except Exception as e:
            await db.rollback()
            # Log error but don't fail the health check
            logger.error("Error storing health metric", exc_info=e)

