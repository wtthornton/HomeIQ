"""
YAML Validation Strategy using YAML Validation Service.

This strategy uses the dedicated YAML Validation Service (Epic 51) for
comprehensive validation including normalization, entity validation, and fixes.
"""

import logging
from typing import Optional

from ...clients.yaml_validation_client import YAMLValidationClient
from ...models.automation_models import ValidationResult
from .validation_strategy import ValidationStrategy

logger = logging.getLogger(__name__)


class YAMLValidationStrategy(ValidationStrategy):
    """Validation strategy using YAML Validation Service."""

    def __init__(self, yaml_validation_client: Optional[YAMLValidationClient]):
        """
        Initialize YAML validation strategy.

        Args:
            yaml_validation_client: YAML Validation Service client (optional)
        """
        self.yaml_validation_client = yaml_validation_client

    @property
    def name(self) -> str:
        """Return the name of this validation strategy."""
        return "YAML Validation Service"

    async def validate(self, automation_yaml: str) -> ValidationResult:
        """
        Validate automation YAML using YAML Validation Service.

        Args:
            automation_yaml: YAML string to validate

        Returns:
            ValidationResult with validation status

        Raises:
            Exception: If validation service is unavailable or request fails
        """
        if not self.yaml_validation_client:
            raise ValueError("YAML Validation Service client not available")

        logger.debug("Using YAML Validation Service for comprehensive validation")
        result = await self.yaml_validation_client.validate_yaml(
            yaml_content=automation_yaml,
            normalize=True,
            validate_entities=True,
            validate_services=False,
        )

        return ValidationResult(
            valid=result.get("valid", False),
            errors=result.get("errors", []),
            warnings=result.get("warnings", []),
            score=result.get("score", 0.0),
            fixed_yaml=result.get("fixed_yaml"),
            fixes_applied=result.get("fixes_applied"),
        )
