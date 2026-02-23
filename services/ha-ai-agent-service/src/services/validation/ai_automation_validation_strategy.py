"""
AI Automation Service Validation Strategy.

This strategy uses the AI Automation Service validation endpoint as a fallback
when YAML Validation Service is unavailable.
"""

import logging

from ...clients.ai_automation_client import AIAutomationClient
from ...models.automation_models import ValidationResult
from .validation_strategy import ValidationStrategy

logger = logging.getLogger(__name__)


class AIAutomationValidationStrategy(ValidationStrategy):
    """Validation strategy using AI Automation Service."""

    def __init__(self, ai_automation_client: AIAutomationClient | None):
        """
        Initialize AI Automation validation strategy.

        Args:
            ai_automation_client: AI Automation Service client (optional)
        """
        self.ai_automation_client = ai_automation_client

    @property
    def name(self) -> str:
        """Return the name of this validation strategy."""
        return "AI Automation Service"

    async def validate(self, automation_yaml: str) -> ValidationResult:
        """
        Validate automation YAML using AI Automation Service.

        Args:
            automation_yaml: YAML string to validate

        Returns:
            ValidationResult with validation status

        Raises:
            Exception: If validation service is unavailable or request fails
        """
        if not self.ai_automation_client:
            raise ValueError("AI Automation Service client not available")

        logger.debug("Using AI Automation Service validation endpoint")
        result = await self.ai_automation_client.validate_yaml(
            yaml_content=automation_yaml,
            validate_entities=True,
            validate_safety=True,
        )

        # Unified endpoint returns errors/warnings as list[str]; support legacy dict format
        raw_errors = result.get("errors", [])
        raw_warnings = result.get("warnings", [])
        errors = [
            err.get("message", str(err)) if isinstance(err, dict) else str(err)
            for err in raw_errors
        ]
        warnings = [
            w.get("message", str(w)) if isinstance(w, dict) else str(w)
            for w in raw_warnings
        ]

        return ValidationResult(
            valid=result.get("valid", False),
            errors=errors,
            warnings=warnings,
            score=result.get("score", 0.0),
            fixed_yaml=result.get("fixed_yaml"),
            fixes_applied=result.get("fixes_applied"),
        )
