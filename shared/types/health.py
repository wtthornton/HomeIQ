"""
Standardized Health Check Types and Response Schema
Epic 17.2: Enhanced Service Health Monitoring
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class HealthStatus(str, Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class DependencyType(str, Enum):
    """Types of service dependencies"""
    DATABASE = "database"
    CACHE = "cache"
    API = "api"
    WEBSOCKET = "websocket"
    MESSAGE_QUEUE = "message_queue"
    FILE_SYSTEM = "file_system"
    EXTERNAL_SERVICE = "external_service"


@dataclass
class DependencyHealth:
    """Health information for a single dependency"""
    name: str
    type: DependencyType
    status: HealthStatus
    response_time_ms: float | None = None
    message: str | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = asdict(self)
        result["type"] = self.type.value
        result["status"] = self.status.value
        return result


@dataclass
class ServiceHealthResponse:
    """Standardized health check response"""
    service: str
    status: HealthStatus
    timestamp: str
    uptime_seconds: float | None = None
    version: str | None = None
    dependencies: list[DependencyHealth] | None = None
    metrics: dict[str, Any] | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            "service": self.service,
            "status": self.status.value,
            "timestamp": self.timestamp,
        }

        if self.uptime_seconds is not None:
            result["uptime_seconds"] = self.uptime_seconds

        if self.version is not None:
            result["version"] = self.version

        if self.dependencies:
            result["dependencies"] = [dep.to_dict() for dep in self.dependencies]

        if self.metrics:
            result["metrics"] = self.metrics

        if self.message:
            result["message"] = self.message

        return result


def create_health_response(
    service: str,
    status: HealthStatus,
    dependencies: list[DependencyHealth] | None = None,
    metrics: dict[str, Any] | None = None,
    message: str | None = None,
    uptime_seconds: float | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    """
    Helper function to create a standardized health response

    Args:
        service: Service name
        status: Overall health status
        dependencies: List of dependency health checks
        metrics: Optional metrics dictionary
        message: Optional message
        uptime_seconds: Service uptime in seconds
        version: Service version

    Returns:
        Dictionary containing the health response
    """
    response = ServiceHealthResponse(
        service=service,
        status=status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        uptime_seconds=uptime_seconds,
        version=version,
        dependencies=dependencies,
        metrics=metrics,
        message=message,
    )

    return response.to_dict()


def determine_overall_status(dependencies: list[DependencyHealth]) -> HealthStatus:
    """
    Determine overall service status based on dependency statuses

    Args:
        dependencies: List of dependency health checks

    Returns:
        Overall health status
    """
    if not dependencies:
        return HealthStatus.HEALTHY

    # If any dependency is critical, overall is critical
    if any(dep.status == HealthStatus.CRITICAL for dep in dependencies):
        return HealthStatus.CRITICAL

    # If any dependency is warning, overall is warning
    if any(dep.status == HealthStatus.WARNING for dep in dependencies):
        return HealthStatus.WARNING

    # If any dependency is unknown, overall is warning
    if any(dep.status == HealthStatus.UNKNOWN for dep in dependencies):
        return HealthStatus.WARNING

    return HealthStatus.HEALTHY


async def check_dependency_health(
    name: str,
    dependency_type: DependencyType,
    check_func,
    timeout: float = 5.0,
) -> DependencyHealth:
    """
    Check health of a dependency with timeout

    Args:
        name: Dependency name
        dependency_type: Type of dependency
        check_func: Async function to check dependency health
        timeout: Timeout in seconds

    Returns:
        DependencyHealth object
    """
    import asyncio
    import time

    start_time = time.time()

    try:
        # Run check with timeout
        result = await asyncio.wait_for(check_func(), timeout=timeout)
        response_time = (time.time() - start_time) * 1000  # Convert to ms

        if result:
            return DependencyHealth(
                name=name,
                type=dependency_type,
                status=HealthStatus.HEALTHY,
                response_time_ms=response_time,
                message="Connected successfully",
            )
        return DependencyHealth(
            name=name,
            type=dependency_type,
            status=HealthStatus.CRITICAL,
            response_time_ms=response_time,
            message="Connection check failed",
        )

    except asyncio.TimeoutError:
        return DependencyHealth(
            name=name,
            type=dependency_type,
            status=HealthStatus.CRITICAL,
            response_time_ms=timeout * 1000,
            message=f"Timeout after {timeout}s",
        )

    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return DependencyHealth(
            name=name,
            type=dependency_type,
            status=HealthStatus.CRITICAL,
            response_time_ms=response_time,
            message=f"Error: {e!s}",
        )

