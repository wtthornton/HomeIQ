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
from .learning_router import router as learning_router

__all__ = [
    'health_router',
    'data_router',
    'pattern_router',
    'suggestion_router',
    'analysis_router',
    'suggestion_management_router',
    'deployment_router',
    'nl_generation_router',
    'conversational_router',  # Story AI1.23: Conversational Refinement
    'ask_ai_router',  # Ask AI Tab: Natural Language Query Interface
    'devices_router',
    'settings_router',
    'admin_router',
    'learning_router',  # Q&A Learning Enhancement Plan
    'set_device_intelligence_client'
]

