"""
Health Monitoring Endpoints
Epic 17.2: Enhanced Service Health Monitoring
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Any

import aiohttp
from fastapi import APIRouter, HTTPException, status
from homeiq_data.types.health import (
    DependencyType,
    check_dependency_health,
    create_health_response,
    determine_overall_status,
)
from homeiq_data.types.health import HealthStatus as HealthStatusEnum
from homeiq_observability.alert_manager import get_alert_manager
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Health status model"""
    status: str
    timestamp: str  # Changed to string for JSON serialization
    uptime_seconds: float
    version: str
    services: dict[str, Any]
    dependencies: dict[str, Any]
    metrics: dict[str, Any]


class ServiceHealth(BaseModel):
    """Service health model"""
    name: str
    status: str
    last_check: str  # Changed to string for JSON serialization
    response_time_ms: float | None = None
    error_message: str | None = None


class HealthEndpoints:
    """Health monitoring endpoints"""

    def __init__(self):
        """Initialize health endpoints"""
        self.router = APIRouter()
        self.start_time = datetime.now()
        self.alert_manager = get_alert_manager("admin-api")
        # Docker Compose service names (not container_name) for DNS resolution
        self.service_urls = {
            "websocket-ingestion": os.getenv("WEBSOCKET_INGESTION_URL", "http://websocket-ingestion:8001"),
            "ai-automation-service": os.getenv("AI_AUTOMATION_URL", "http://ai-automation-service-new:8025"),
            "influxdb": os.getenv("INFLUXDB_URL", "http://influxdb:8086"),
            "weather-api": os.getenv("WEATHER_SERVICE_URL", "http://weather-api:8009"),
            "sports-api": os.getenv("SPORTS_API_URL", "http://sports-api:8005"),
            # Data source services - Docker Compose service names
            "carbon-intensity-service": os.getenv("CARBON_INTENSITY_URL", "http://carbon-intensity:8010"),
            "electricity-pricing-service": os.getenv("ELECTRICITY_PRICING_URL", "http://electricity-pricing:8011"),
            "air-quality-service": os.getenv("AIR_QUALITY_URL", "http://air-quality:8012"),
            "calendar-service": os.getenv("CALENDAR_URL", "http://calendar:8013"),
            "smart-meter-service": os.getenv("SMART_METER_URL", "http://smart-meter:8014"),
            # ML & Blueprint services
            "blueprint-index": os.getenv("BLUEPRINT_INDEX_URL", "http://blueprint-index:8031"),
            "rule-recommendation-ml": os.getenv("RULE_RECOMMENDATION_URL", "http://rule-recommendation-ml:8035"),
            # Energy Analytics
            "energy-correlator": os.getenv("ENERGY_CORRELATOR_URL", "http://energy-correlator:8015"),
            "energy-forecasting": os.getenv("ENERGY_FORECASTING_URL", "http://energy-forecasting:8016"),
            "proactive-agent-service": os.getenv("PROACTIVE_AGENT_URL", "http://proactive-agent-service:8017"),
            # Blueprint services
            "blueprint-suggestion-service": os.getenv("BLUEPRINT_SUGGESTION_URL", "http://blueprint-suggestion-service:8032"),
            # Pattern Analysis
            "ai-pattern-service": os.getenv("AI_PATTERN_URL", "http://ai-pattern-service:8033"),
            "api-automation-edge": os.getenv("AUTOMATION_EDGE_URL", "http://api-automation-edge:8034"),
            # ML Engine
            "ai-core-service": os.getenv("AI_CORE_URL", "http://ai-core-service:8019"),
            "device-intelligence-service": os.getenv("DEVICE_INTELLIGENCE_URL", "http://device-intelligence-service:8021"),
            "rag-service": os.getenv("RAG_SERVICE_URL", "http://rag-service:8027"),
            # Device Management
            "device-health-monitor": os.getenv("DEVICE_HEALTH_URL", "http://device-health-monitor:8040"),
            "device-context-classifier": os.getenv("DEVICE_CLASSIFIER_URL", "http://device-context-classifier:8041"),
            "device-setup-assistant": os.getenv("DEVICE_SETUP_URL", "http://device-setup-assistant:8042"),
        }

        # Step 4.6: Domain group mappings for aggregated health
        self.group_mappings: dict[str, list[str]] = {
            "core-platform": [
                "websocket-ingestion", "influxdb", "admin-api",
            ],
            "data-collectors": [
                "weather-api", "sports-api", "carbon-intensity-service",
                "electricity-pricing-service", "air-quality-service",
                "calendar-service", "smart-meter-service",
            ],
            "ml-engine": [
                "ai-core-service", "device-intelligence-service", "rag-service",
            ],
            "automation-intelligence": [
                "ai-automation-service",
            ],
            "energy-analytics": [
                "energy-correlator", "energy-forecasting", "proactive-agent-service",
            ],
            "blueprints": [
                "blueprint-index", "blueprint-suggestion-service", "rule-recommendation-ml",
            ],
            "pattern-analysis": [
                "ai-pattern-service", "api-automation-edge",
            ],
            "device-management": [
                "device-health-monitor", "device-context-classifier", "device-setup-assistant",
            ],
        }

        self._add_routes()

    def _add_routes(self):
        """Add health routes"""

        @self.router.get("/health")
        async def get_health():
            """Get enhanced health status with dependency checks"""
            try:
                uptime = (datetime.now() - self.start_time).total_seconds()

                # Check dependencies
                dependencies = []

                # Check InfluxDB connection
                influxdb_dep = await check_dependency_health(
                    name="InfluxDB",
                    dependency_type=DependencyType.DATABASE,
                    check_func=lambda: self._check_influxdb_health(),
                    timeout=3.0
                )
                dependencies.append(influxdb_dep)

                # Check WebSocket Ingestion service
                websocket_dep = await check_dependency_health(
                    name="WebSocket Ingestion",
                    dependency_type=DependencyType.API,
                    check_func=lambda: self._check_service_health(
                        self.service_urls["websocket-ingestion"] + "/health"
                    ),
                    timeout=2.0
                )
                dependencies.append(websocket_dep)

                # Determine overall status
                overall_status = determine_overall_status(dependencies)

                # Check for alert conditions (Epic 17.4)
                for dep in dependencies:
                    if dep.status == HealthStatusEnum.CRITICAL:
                        self.alert_manager.check_condition(
                            "service_unhealthy",
                            "critical",
                            metadata={
                                "dependency": dep.name,
                                "response_time_ms": dep.response_time_ms,
                                "message": dep.message
                            }
                        )

                # Calculate uptime percentage based on service health
                uptime_percentage = self._calculate_uptime_percentage(dependencies, uptime)

                # Create standardized health response
                return create_health_response(
                    service="admin-api",
                    status=overall_status,
                    dependencies=dependencies,
                    metrics={
                        "uptime_seconds": uptime,
                        "uptime_human": self._format_uptime(uptime),
                        "uptime_percentage": uptime_percentage,
                        "start_time": self.start_time.isoformat(),
                        "current_time": datetime.now().isoformat()
                    },
                    uptime_seconds=uptime,
                    version="1.0.0"
                )

            except Exception as e:
                logger.error("Error getting health status: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get health status"
                ) from e

        @self.router.get("/health/services", response_model=dict[str, ServiceHealth])
        async def get_services_health():
            """Get services health status"""
            try:
                services_health = await self._check_services()
                return services_health
            except Exception as e:
                logger.error("Error getting services health: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get services health"
                ) from e

        @self.router.get("/health/dependencies", response_model=dict[str, Any])
        async def get_dependencies_health():
            """Get dependencies health status"""
            try:
                dependencies_health = await self._check_dependencies()
                return dependencies_health
            except Exception as e:
                logger.error("Error getting dependencies health: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get dependencies health"
                ) from e

        @self.router.get("/health/groups", response_model=dict[str, Any])
        async def get_group_health():
            """Step 4.6: Get aggregated health status per domain group"""
            try:
                services_health = await self._check_services()
                groups = {}
                total_healthy = 0
                total_services = 0

                for group_id, service_names in self.group_mappings.items():
                    healthy = 0
                    degraded = 0
                    unhealthy = 0

                    for svc in service_names:
                        svc_health = services_health.get(svc)
                        if svc_health:
                            total_services += 1
                            svc_status = svc_health.status
                            if svc_status in ("healthy", "pass"):
                                healthy += 1
                                total_healthy += 1
                            elif svc_status == "degraded":
                                degraded += 1
                                total_healthy += 1  # degraded counts as up
                            else:
                                unhealthy += 1

                    group_total = healthy + degraded + unhealthy
                    if group_total == 0:
                        agg_status = "empty"
                    elif healthy + degraded == group_total:
                        agg_status = "healthy" if degraded == 0 else "degraded"
                    elif healthy + degraded == 0:
                        agg_status = "unhealthy"
                    else:
                        agg_status = "degraded"

                    groups[group_id] = {
                        "status": agg_status,
                        "healthy": healthy,
                        "degraded": degraded,
                        "unhealthy": unhealthy,
                        "total": group_total,
                    }

                healthy_groups = sum(
                    1 for g in groups.values() if g["status"] == "healthy"
                )
                degraded_groups = sum(
                    1 for g in groups.values() if g["status"] == "degraded"
                )
                unhealthy_groups = sum(
                    1 for g in groups.values() if g["status"] == "unhealthy"
                )

                return {
                    "groups": groups,
                    "summary": {
                        "total_groups": len(groups),
                        "healthy_groups": healthy_groups,
                        "degraded_groups": degraded_groups,
                        "unhealthy_groups": unhealthy_groups,
                        "total_services": total_services,
                        "healthy_services": total_healthy,
                        "timestamp": datetime.now().isoformat(),
                    },
                }
            except Exception as e:
                logger.error("Error getting group health: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get group health",
                ) from e

        @self.router.get("/health/metrics", response_model=dict[str, Any])
        async def get_health_metrics():
            """Get health metrics"""
            try:
                metrics = await self._get_metrics()
                return metrics
            except Exception as e:
                logger.error("Error getting health metrics: %s", e)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to get health metrics"
                ) from e

    async def _check_services(self) -> dict[str, ServiceHealth]:
        """Check health of all services"""
        services_health = {}

        # Custom health paths for services that don't use /health
        custom_health_paths = {
            "rule-recommendation-ml": "/api/v1/health",
        }

        logger.debug("Checking %d services: %s", len(self.service_urls), list(self.service_urls.keys()))

        for service_name, service_url in self.service_urls.items():
            logger.debug("Checking service: %s at %s", service_name, service_url)
            try:
                start_time = datetime.now()

                # Get custom health path or use default /health
                health_path = custom_health_paths.get(service_name, "/health")

                # Standard health check for internal services
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:  # noqa: SIM117
                    async with session.get(f"{service_url}{health_path}") as response:
                        response_time = (datetime.now() - start_time).total_seconds() * 1000

                        if response.status == 200:
                            data = await response.json()
                            services_health[service_name] = ServiceHealth(
                                name=service_name,
                                status=data.get("status", "unknown"),
                                last_check=datetime.now().isoformat(),  # Convert to ISO string
                                response_time_ms=response_time
                            )
                        else:
                            services_health[service_name] = ServiceHealth(
                                name=service_name,
                                status="unhealthy",
                                last_check=datetime.now().isoformat(),  # Convert to ISO string
                                response_time_ms=response_time,
                                error_message=f"HTTP {response.status}"
                            )

            except TimeoutError:
                services_health[service_name] = ServiceHealth(
                    name=service_name,
                    status="unhealthy",
                    last_check=datetime.now().isoformat(),  # Convert to ISO string
                    error_message="Timeout"
                )
            except Exception as e:
                logger.error("Error checking %s: %s", service_name, e, exc_info=True)
                services_health[service_name] = ServiceHealth(
                    name=service_name,
                    status="unhealthy",
                    last_check=datetime.now().isoformat(),  # Convert to ISO string
                    error_message=str(e)
                )

        logger.debug("Returning %d service health results: %s", len(services_health), list(services_health.keys()))
        return services_health

    async def _check_dependencies(self) -> dict[str, Any]:
        """Check health of external dependencies"""
        dependencies_health = {}

        # Check InfluxDB
        try:
            influxdb_url = self.service_urls["influxdb"]
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:  # noqa: SIM117
                async with session.get(f"{influxdb_url}/health") as response:
                    dependencies_health["influxdb"] = {
                        "status": "healthy" if response.status == 200 else "unhealthy",
                        "last_check": datetime.now().isoformat(),
                        "response_time_ms": response.headers.get("X-Response-Time", "N/A")
                    }
        except Exception as e:
            dependencies_health["influxdb"] = {
                "status": "unhealthy",
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }

        # Check Weather API
        try:
            weather_api_key = os.getenv("WEATHER_API_KEY")
            if weather_api_key:
                weather_url = self.service_urls["weather-api"]
                async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:  # noqa: SIM117
                    async with session.get(
                        f"{weather_url}/weather",
                        params={"q": "London", "appid": weather_api_key},
                    ) as response:
                        dependencies_health["weather_api"] = {
                            "status": "healthy" if response.status == 200 else "unhealthy",
                            "last_check": datetime.now().isoformat(),
                            "response_time_ms": response.headers.get("X-Response-Time", "N/A")
                        }
            else:
                dependencies_health["weather_api"] = {
                    "status": "disabled",
                    "last_check": datetime.now().isoformat(),
                    "message": "No API key configured"
                }
        except Exception as e:
            dependencies_health["weather_api"] = {
                "status": "unhealthy",
                "last_check": datetime.now().isoformat(),
                "error": str(e)
            }

        return dependencies_health

    async def _get_metrics(self) -> dict[str, Any]:
        """Get health metrics"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "uptime_seconds": uptime,
            "uptime_human": self._format_uptime(uptime),
            "start_time": self.start_time.isoformat(),
            "current_time": datetime.now().isoformat(),
            "memory_usage": self._get_memory_usage(),
            "cpu_usage": await self._get_cpu_usage(),
            "disk_usage": self._get_disk_usage()
        }

    async def _check_influxdb_health(self) -> bool:
        """Check InfluxDB health"""
        try:
            influxdb_url = self.service_urls["influxdb"]
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:  # noqa: SIM117
                async with session.get(f"{influxdb_url}/health") as response:
                    return response.status == 200
        except Exception as e:
            logger.error("InfluxDB health check failed: %s", e)
            return False

    async def _check_service_health(self, service_url: str) -> bool:
        """Check service health via HTTP"""
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:  # noqa: SIM117
                async with session.get(service_url) as response:
                    return response.status == 200
        except Exception as e:
            logger.error("Service health check failed for %s: %s", service_url, e)
            return False

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if days > 0:
            return f"{days}d {hours}h {minutes}m {secs}s"
        elif hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def _calculate_uptime_percentage(self, dependencies: list, uptime_seconds: float) -> float:
        """
        Calculate realistic uptime percentage based on dependency health and service uptime.

        Context7 Best Practice: Calculate from actual data, not hardcoded values
        Source: /blueswen/fastapi-observability

        Formula: (healthy_dependencies / total_dependencies) * current_uptime_ratio
        - If all dependencies healthy: ~99.x% based on uptime
        - If dependencies failing: proportionally lower
        """
        if not dependencies or uptime_seconds == 0:
            return 0.0

        # Count healthy dependencies
        healthy_count = sum(
            1 for dep in dependencies if getattr(dep, "status", None) == HealthStatusEnum.HEALTHY
        )
        total_count = len(dependencies)

        # Calculate base health ratio (what % of dependencies are healthy)
        health_ratio = (healthy_count / total_count) if total_count > 0 else 0.0

        # Calculate uptime ratio (realistic based on service age)
        # Assumption: 0.1% downtime per day is realistic (99.9% uptime after 24h)
        # Formula: 100 - (0.1% * days_running) but capped at minimum 95%
        days_running = uptime_seconds / 86400
        expected_downtime = 0.1 * days_running  # 0.1% per day
        uptime_ratio = max(95.0, 100.0 - expected_downtime) / 100.0

        # Combined percentage (health × uptime)
        uptime_percentage = health_ratio * uptime_ratio * 100

        # Round to 2 decimal places
        return round(uptime_percentage, 2)

    def _get_memory_usage(self) -> dict[str, Any]:
        """Get memory usage information"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            return {
                "total_mb": round(memory.total / 1024 / 1024, 2),
                "available_mb": round(memory.available / 1024 / 1024, 2),
                "used_mb": round(memory.used / 1024 / 1024, 2),
                "percentage": memory.percent
            }
        except ImportError:
            return {"error": "psutil not available"}

    async def _get_cpu_usage(self) -> dict[str, Any]:
        """Get CPU usage information"""
        try:
            import psutil
            cpu_percent = await asyncio.to_thread(psutil.cpu_percent, interval=1)
            cpu_count = psutil.cpu_count()
            return {
                "usage_percent": cpu_percent,
                "core_count": cpu_count,
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except ImportError:
            return {"error": "psutil not available"}

    def _get_disk_usage(self) -> dict[str, Any]:
        """Get disk usage information"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            return {
                "total_gb": round(disk.total / 1024 / 1024 / 1024, 2),
                "used_gb": round(disk.used / 1024 / 1024 / 1024, 2),
                "free_gb": round(disk.free / 1024 / 1024 / 1024, 2),
                "percentage": round((disk.used / disk.total) * 100, 2)
            }
        except ImportError:
            return {"error": "psutil not available"}
