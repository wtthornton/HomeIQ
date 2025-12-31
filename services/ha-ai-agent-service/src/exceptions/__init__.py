"""Exception hierarchy for automation errors."""

from .automation_exceptions import (
    AutomationError,
    EntityResolutionError,
    SafetyViolationError,
    ValidationError,
)

__all__ = [
    "AutomationError",
    "ValidationError",
    "EntityResolutionError",
    "SafetyViolationError",
]
