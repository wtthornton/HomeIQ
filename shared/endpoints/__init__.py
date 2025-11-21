"""
Shared endpoints module for admin-api and data-api services.
"""

from .integration_endpoints import create_integration_router
from .service_controller import ServiceController, service_controller
from .simple_health import SimpleHealthService, simple_health_service
from .simple_health import router as simple_health_router

__all__ = [
    "ServiceController",
    "SimpleHealthService",
    "create_integration_router",
    "service_controller",
    "simple_health_router",
    "simple_health_service",
]

