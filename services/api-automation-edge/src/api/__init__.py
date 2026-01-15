"""
API Routers

FastAPI endpoints for the automation edge service
"""

from .health_router import router as health_router
from .spec_router import router as spec_router
from .execution_router import router as execution_router
from .observability_router import router as observability_router

__all__ = [
    "health_router",
    "spec_router",
    "execution_router",
    "observability_router",
]
