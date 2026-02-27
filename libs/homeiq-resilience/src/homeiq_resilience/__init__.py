"""HomeIQ cross-group resilience utilities.

Provides circuit breaker, retry, health check, and authentication patterns
for services that make HTTP calls across group boundaries.
"""

from .auth import ServiceAuthValidator, require_service_auth
from .circuit_breaker import CircuitBreaker, CircuitOpenError
from .cross_group_client import CrossGroupClient
from .health import DependencyStatus, GroupHealthCheck
from .startup import wait_for_dependency

__all__ = [
    "CircuitBreaker",
    "CircuitOpenError",
    "CrossGroupClient",
    "DependencyStatus",
    "GroupHealthCheck",
    "ServiceAuthValidator",
    "require_service_auth",
    "wait_for_dependency",
]
