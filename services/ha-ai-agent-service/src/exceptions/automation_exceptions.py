"""
Exception hierarchy for automation errors.

Provides specific exception types for different error scenarios.
"""


class AutomationError(Exception):
    """Base exception for automation-related errors."""

    def __init__(self, message: str, error_code: str | None = None):
        """
        Initialize automation error.

        Args:
            message: Error message
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ValidationError(AutomationError):
    """Exception for validation errors."""

    def __init__(self, message: str, errors: list[str] | None = None, error_code: str | None = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            errors: List of validation errors
            error_code: Optional error code
        """
        super().__init__(message, error_code)
        self.errors = errors or []


class EntityResolutionError(AutomationError):
    """Exception for entity resolution errors."""

    def __init__(self, message: str, entity_id: str | None = None, error_code: str | None = None):
        """
        Initialize entity resolution error.

        Args:
            message: Error message
            entity_id: Optional entity ID that failed to resolve
            error_code: Optional error code
        """
        super().__init__(message, error_code)
        self.entity_id = entity_id


class SafetyViolationError(AutomationError):
    """Exception for safety rule violations."""

    def __init__(self, message: str, warnings: list[str] | None = None, error_code: str | None = None):
        """
        Initialize safety violation error.

        Args:
            message: Error message
            warnings: List of safety warnings
            error_code: Optional error code
        """
        super().__init__(message, error_code)
        self.warnings = warnings or []
