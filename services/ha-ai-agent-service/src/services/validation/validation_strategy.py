"""
Abstract base class for validation strategies.

This module defines the ValidationStrategy interface that all validation
strategies must implement.
"""

from abc import ABC, abstractmethod

from ...models.automation_models import ValidationResult


class ValidationStrategy(ABC):
    """Abstract base class for validation strategies."""

    @abstractmethod
    async def validate(self, automation_yaml: str) -> ValidationResult:
        """
        Validate automation YAML.

        Args:
            automation_yaml: YAML string to validate

        Returns:
            ValidationResult with validation status, errors, warnings, etc.

        Raises:
            Exception: If validation fails unexpectedly (will trigger fallback)
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this validation strategy."""
        pass
