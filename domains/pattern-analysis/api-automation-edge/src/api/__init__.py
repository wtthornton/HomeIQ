"""
API Routers

FastAPI endpoints for the automation edge service
"""

from .execution_router import router as execution_router
from .health_router import router as health_router
from .observability_router import router as observability_router
from .spec_router import router as spec_router

__all__ = [
    "health_router",
    "spec_router",
    "execution_router",
    "observability_router",
]
