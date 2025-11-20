"""
Error Recovery Service

Provides actionable error recovery guidance.
Handles different error types and suggests recovery actions.

Created: Phase 5 - Error Recovery & Validation
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ErrorResponse:
    """Structured error response with recovery actions"""
    type: str
    message: str
    recovery_actions: list[str]
    error_details: dict[str, Any] | None = None


class NoEntitiesFoundError(Exception):
    """Raised when no entities are found"""
    pass


class AmbiguousQueryError(Exception):
    """Raised when query is ambiguous"""
    pass


class ValidationError(Exception):
    """Raised when validation fails"""
    pass


class ErrorRecoveryService:
    """
    Provides actionable error recovery guidance.
    
    Handles different error types and suggests recovery actions
    to help users resolve issues.
    """

    def __init__(self):
        """Initialize error recovery service"""
        logger.info("ErrorRecoveryService initialized")

    async def handle_processing_error(
        self,
        error: Exception,
        query: str,
        partial_results: dict | None = None
    ) -> ErrorResponse:
        """
        Handle processing error and provide recovery guidance.
        
        Args:
            error: The exception that occurred
            query: Original user query
            partial_results: Optional partial results before error
        
        Returns:
            ErrorResponse with recovery actions
        """
        if isinstance(error, NoEntitiesFoundError):
            return await self._handle_no_entities_error(query, partial_results)
        elif isinstance(error, AmbiguousQueryError):
            return await self._handle_ambiguous_query_error(query, partial_results)
        elif isinstance(error, ValidationError):
            return await self._handle_validation_error(error, query, partial_results)
        else:
            return self._handle_generic_error(error, query, partial_results)

    async def _handle_no_entities_error(
        self,
        query: str,
        partial_results: dict | None
    ) -> ErrorResponse:
        """Handle no entities found error"""
        # Suggest similar entities (would use entity search in full implementation)
        suggestions = [
            "Check device names in Home Assistant",
            "Try using the search feature to find devices",
            "Verify device names match exactly (case-sensitive)"
        ]

        return ErrorResponse(
            type="no_entities",
            message="Couldn't find the devices you mentioned",
            recovery_actions=suggestions,
            error_details={"query": query}
        )

    async def _handle_ambiguous_query_error(
        self,
        query: str,
        partial_results: dict | None
    ) -> ErrorResponse:
        """Handle ambiguous query error"""
        return ErrorResponse(
            type="ambiguous",
            message="Your request needs more information",
            recovery_actions=[
                "Answer the clarification questions",
                "Provide more specific device names",
                "Specify the location or area"
            ],
            error_details={"query": query}
        )

    async def _handle_validation_error(
        self,
        error: ValidationError,
        query: str,
        partial_results: dict | None
    ) -> ErrorResponse:
        """Handle validation error"""
        return ErrorResponse(
            type="validation",
            message=f"Validation failed: {str(error)}",
            recovery_actions=[
                "Check that all entities exist in Home Assistant",
                "Verify automation YAML syntax",
                "Review error details and fix issues"
            ],
            error_details={"query": query, "error": str(error)}
        )

    def _handle_generic_error(
        self,
        error: Exception,
        query: str,
        partial_results: dict | None
    ) -> ErrorResponse:
        """Handle generic error"""
        return ErrorResponse(
            type="generic",
            message=f"An error occurred: {str(error)}",
            recovery_actions=[
                "Try rephrasing your request",
                "Check that all required services are running",
                "Contact support if the issue persists"
            ],
            error_details={"query": query, "error": str(error), "error_type": type(error).__name__}
        )

