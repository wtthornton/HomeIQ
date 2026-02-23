"""
Shared endpoints module for admin-api and data-api services.
"""

from .service_controller import ServiceController, service_controller
from .simple_health import SimpleHealthService, simple_health_service, router as simple_health_router
from .integration_endpoints import create_integration_router

__all__ = [
    'ServiceController',
    'service_controller',
    'SimpleHealthService',
    'simple_health_service',
    'simple_health_router',
    'create_integration_router',
]

