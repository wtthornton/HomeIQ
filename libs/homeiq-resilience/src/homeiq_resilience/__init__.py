"""HomeIQ cross-group resilience utilities.

Provides circuit breaker, retry, health check, authentication, app factory,
lifespan management, HTTP client, task manager, and scheduler patterns
for services that make HTTP calls across group boundaries.
"""

from .app_factory import create_app
from .auth import ServiceAuthValidator, require_service_auth
from .circuit_breaker import CircuitBreaker, CircuitOpenError
from .cross_group_client import CrossGroupClient
from .health import DependencyStatus, GroupHealthCheck
from .health_check import StandardHealthCheck
from .http_client import ManagedHTTPClient
from .lifespan import ServiceLifespan
from .scheduler import ServiceScheduler
from .startup import wait_for_dependency
from .task_manager import TaskManager

__all__ = [
    "CircuitBreaker",
    "CircuitOpenError",
    "CrossGroupClient",
    "DependencyStatus",
    "GroupHealthCheck",
    "ManagedHTTPClient",
    "ServiceAuthValidator",
    "ServiceLifespan",
    "ServiceScheduler",
    "StandardHealthCheck",
    "TaskManager",
    "create_app",
    "require_service_auth",
    "wait_for_dependency",
]
