"""
API routers for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
"""

from .health_router import router as health_router
from .suggestion_router import router as suggestion_router
from .deployment_router import router as deployment_router
from . import pattern_router
from . import synergy_router
from . import analysis_router
from . import preference_router
from . import automation_yaml_validate_router
from . import blueprint_validate_router
from . import setup_validate_router
from . import scene_validate_router
from . import script_validate_router

__all__ = [
    "health_router",
    "suggestion_router",
    "deployment_router",
    "pattern_router",
    "synergy_router",
    "analysis_router",
    "preference_router",
    "automation_yaml_validate_router",
    "blueprint_validate_router",
    "setup_validate_router",
    "scene_validate_router",
    "script_validate_router",
]

