"""
Data Transfer Objects (DTOs) for automation preview feature.

These models provide clear data contracts for automation preview requests,
responses, and validation results.
"""

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ValidationResult:
    """Result of YAML validation."""

    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    score: float = 0.0
    fixed_yaml: Optional[str] = None
    fixes_applied: Optional[list[str]] = None
    strategy_name: Optional[str] = None  # Name of validation strategy that succeeded
    services_unavailable: Optional[list[str]] = None  # List of services that were unavailable

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result: dict[str, Any] = {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "score": self.score,
        }
        if self.fixed_yaml is not None:
            result["fixed_yaml"] = self.fixed_yaml
        if self.fixes_applied is not None:
            result["fixes_applied"] = self.fixes_applied
        if self.strategy_name is not None:
            result["strategy_used"] = self.strategy_name
        if self.services_unavailable is not None:
            result["services_unavailable"] = self.services_unavailable
        return result


@dataclass
class AutomationPreview:
    """Preview details for an automation."""

    alias: str
    description: Optional[str] = None
    trigger_description: Optional[str] = None
    action_description: Optional[str] = None
    mode: str = "single"
    initial_state: Optional[bool] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result: dict[str, Any] = {
            "alias": self.alias,
            "mode": self.mode,
        }
        if self.description is not None:
            result["description"] = self.description
        if self.trigger_description is not None:
            result["trigger_description"] = self.trigger_description
        if self.action_description is not None:
            result["action_description"] = self.action_description
        if self.initial_state is not None:
            result["initial_state"] = self.initial_state
        return result


@dataclass
class AutomationPreviewRequest:
    """Request to generate an automation preview."""

    user_prompt: str
    automation_yaml: str
    alias: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AutomationPreviewRequest":
        """Create from dictionary (e.g., from tool arguments)."""
        return cls(
            user_prompt=data.get("user_prompt", ""),
            automation_yaml=data.get("automation_yaml", ""),
            alias=data.get("alias", ""),
        )

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate request parameters.

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.user_prompt or not self.user_prompt.strip():
            return False, "user_prompt is required and cannot be empty"
        if len(self.user_prompt.strip()) < 3:
            return False, "user_prompt must be at least 3 characters"
        if not self.automation_yaml or not self.automation_yaml.strip():
            return False, "automation_yaml is required and cannot be empty"
        if not self.alias or not self.alias.strip():
            return False, "alias is required and cannot be empty"
        if len(self.alias.strip()) > 100:
            return False, "alias must be 100 characters or less"
        return True, None


@dataclass
class AutomationPreviewResponse:
    """Response from automation preview generation."""

    success: bool
    preview: Optional[AutomationPreview] = None
    validation: Optional[ValidationResult] = None
    entities_affected: list[str] = field(default_factory=list)
    areas_affected: list[str] = field(default_factory=list)
    services_used: list[str] = field(default_factory=list)
    safety_warnings: list[str] = field(default_factory=list)
    user_prompt: Optional[str] = None
    automation_yaml: Optional[str] = None
    alias: Optional[str] = None
    error: Optional[str] = None
    message: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result: dict[str, Any] = {
            "success": self.success,
            "preview": True,  # Flag indicating this is a preview
        }

        if self.preview:
            result["alias"] = self.preview.alias
            result["details"] = {
                "trigger_description": self.preview.trigger_description,
                "action_description": self.preview.action_description,
                "mode": self.preview.mode,
                "initial_state": self.preview.initial_state,
            }

        if self.validation:
            result["validation"] = self.validation.to_dict()

        result["entities_affected"] = self.entities_affected
        result["areas_affected"] = self.areas_affected
        result["services_used"] = self.services_used
        result["safety_warnings"] = self.safety_warnings

        if self.user_prompt:
            result["user_prompt"] = self.user_prompt
        if self.automation_yaml:
            result["automation_yaml"] = self.automation_yaml
        if self.alias:
            result["alias"] = self.alias
        if self.error:
            result["error"] = self.error
        if self.message:
            result["message"] = self.message

        return result

    @classmethod
    def error_response(
        cls,
        error: str,
        user_prompt: Optional[str] = None,
        alias: Optional[str] = None,
    ) -> "AutomationPreviewResponse":
        """Create an error response."""
        return cls(
            success=False,
            error=error,
            user_prompt=user_prompt,
            alias=alias,
        )
