"""API package"""

from .admin_router import router as admin_router
from .analysis_router import router as analysis_router
from .ask_ai_router import router as ask_ai_router  # Ask AI Tab
from .conversational_router import router as conversational_router  # Story AI1.23
from .data_router import router as data_router
from .deployment_router import router as deployment_router
from .devices_router import router as devices_router
from .devices_router import set_device_intelligence_client
from .health import router as health_router
from .nl_generation_router import router as nl_generation_router
from .pattern_router import router as pattern_router
from .settings_router import router as settings_router
from .suggestion_management_router import router as suggestion_management_router
from .suggestion_router import router as suggestion_router

__all__ = [
    "admin_router",
    "analysis_router",
    "ask_ai_router",  # Ask AI Tab: Natural Language Query Interface
    "conversational_router",  # Story AI1.23: Conversational Refinement
    "data_router",
    "deployment_router",
    "devices_router",
    "health_router",
    "nl_generation_router",
    "pattern_router",
    "set_device_intelligence_client",
    "settings_router",
    "suggestion_management_router",
    "suggestion_router",
]

