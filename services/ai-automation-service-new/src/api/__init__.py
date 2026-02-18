"""
API routers for AI Automation Service

Epic 39, Story 39.10: Automation Service Foundation
"""

from . import (
    analysis_router,
    automation_yaml_validate_router,
    blueprint_validate_router,
    pattern_router,
    preference_router,
    scene_validate_router,
    script_validate_router,
    setup_validate_router,
    synergy_router,
)
from .deployment_router import router as deployment_router
from .health_router import router as health_router
from .suggestion_router import router as suggestion_router

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
