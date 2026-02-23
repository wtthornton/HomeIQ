"""
Shared Exception Hierarchy for HomeIQ

Standardized exception classes for consistent error handling across all services.
"""

from typing import Optional, Dict, Any


class HomeIQError(Exception):
    """
    Base exception for all HomeIQ errors.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize HomeIQ error.
        
        Args:
            message: Error message
            context: Optional context dictionary with additional error details
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.error_code = self.__class__.__name__
    
    def __str__(self) -> str:
        """String representation of error"""
        if self.context:
            return f"{self.error_code}: {self.message} (context: {self.context})"
        return f"{self.error_code}: {self.message}"


class ServiceError(HomeIQError):
    """Service-level errors (e.g., service unavailable, service configuration issues)"""
    pass


class ValidationError(HomeIQError):
    """Validation errors (e.g., invalid input, missing required fields)"""
    pass


class NetworkError(HomeIQError):
    """Network/connection errors (e.g., connection timeout, network unreachable)"""
    pass


class AuthenticationError(HomeIQError):
    """Authentication errors (e.g., invalid token, unauthorized access)"""
    pass


class ConfigurationError(HomeIQError):
    """Configuration errors (e.g., missing environment variables, invalid config)"""
    pass


class StateMachineError(HomeIQError):
    """State machine errors (e.g., invalid state transition)"""
    pass


class DatabaseError(HomeIQError):
    """Database errors (e.g., connection failure, query error)"""
    pass


class NotFoundError(HomeIQError):
    """Resource not found errors (e.g., entity not found, device not found)"""
    pass


class ConflictError(HomeIQError):
    """Conflict errors (e.g., duplicate entry, resource already exists)"""
    pass

