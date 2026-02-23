"""Entity resolution service for matching user prompts to Home Assistant entities."""

from .entity_resolution_result import EntityResolutionResult
from .entity_resolution_service import EntityResolutionService

__all__ = [
    "EntityResolutionService",
    "EntityResolutionResult",
]
