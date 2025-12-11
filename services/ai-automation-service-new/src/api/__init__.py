"""
API routers for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
"""

from .health_router import router as health_router
from .suggestion_router import router as suggestion_router
from .deployment_router import router as deployment_router

__all__ = [
    "health_router",
    "suggestion_router",
    "deployment_router",
]

