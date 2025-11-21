"""
Standardized Error Handler for HomeIQ Services

Provides consistent error handling and response formatting for FastAPI applications.
"""

import logging
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .exceptions import (
    AuthenticationError,
    ConfigurationError,
    ConflictError,
    DatabaseError,
    HomeIQError,
    NetworkError,
    NotFoundError,
    ServiceError,
    StateMachineError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def get_correlation_id(request: Request) -> str | None:
    """
    Get correlation ID from request headers or generate one.

    Args:
        request: FastAPI request object

    Returns:
        Correlation ID string or None
    """
    # Try to get correlation ID from headers
    correlation_id = request.headers.get("X-Correlation-ID") or request.headers.get("x-correlation-id")

    # If not found, try to get from request state (set by middleware)
    if not correlation_id:
        correlation_id = getattr(request.state, "correlation_id", None)

    return correlation_id


def handle_error(error: Exception, request: Request | None = None, context: dict[str, Any] | None = None) -> HTTPException:
    """
    Convert exception to HTTPException with standardized format.

    Args:
        error: The exception to handle
        request: Optional FastAPI request object (for correlation ID)
        context: Additional context for error logging

    Returns:
        HTTPException with standardized error format
    """
    context = context or {}

    # Add correlation ID if available
    if request:
        correlation_id = get_correlation_id(request)
        if correlation_id:
            context["correlation_id"] = correlation_id

    if isinstance(error, HomeIQError):
        logger.error(
            f"{error.error_code}: {error.message}",
            extra={
                **context,
                **error.context,
                "error_code": error.error_code,
            },
        )

        # Map error types to HTTP status codes
        status_code_map = {
            "ValidationError": status.HTTP_400_BAD_REQUEST,
            "AuthenticationError": status.HTTP_401_UNAUTHORIZED,
            "NotFoundError": status.HTTP_404_NOT_FOUND,
            "ConflictError": status.HTTP_409_CONFLICT,
            "StateMachineError": status.HTTP_409_CONFLICT,
            "NetworkError": status.HTTP_503_SERVICE_UNAVAILABLE,
            "ServiceError": status.HTTP_503_SERVICE_UNAVAILABLE,
            "DatabaseError": status.HTTP_500_INTERNAL_SERVER_ERROR,
            "ConfigurationError": status.HTTP_500_INTERNAL_SERVER_ERROR,
        }

        status_code = status_code_map.get(error.error_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        error_response = {
            "error": {
                "code": error.error_code,
                "message": error.message,
                "context": error.context,
            },
        }

        # Add correlation ID to response if available
        if request:
            correlation_id = get_correlation_id(request)
            if correlation_id:
                error_response["error"]["correlation_id"] = correlation_id

        return HTTPException(
            status_code=status_code,
            detail=error_response,
        )
    # Generic error
    error_msg = str(error)
    logger.error(
        f"Unhandled error: {error_msg}",
        extra=context,
        exc_info=True,
    )

    error_response = {
        "error": {
            "code": "InternalServerError",
            "message": "An internal error occurred",
        },
    }

    # Add correlation ID to response if available
    if request:
        correlation_id = get_correlation_id(request)
        if correlation_id:
            error_response["error"]["correlation_id"] = correlation_id

    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_response,
    )


async def homeiq_exception_handler(request: Request, exc: HomeIQError) -> JSONResponse:
    """
    FastAPI exception handler for HomeIQError exceptions.

    Args:
        request: FastAPI request object
        exc: HomeIQError exception

    Returns:
        JSONResponse with standardized error format
    """
    http_exc = handle_error(exc, request=request)

    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    FastAPI exception handler for request validation errors.

    Args:
        request: FastAPI request object
        exc: RequestValidationError exception

    Returns:
        JSONResponse with standardized error format
    """
    correlation_id = get_correlation_id(request)

    logger.error(
        f"Validation error on {request.method} {request.url.path}",
        extra={
            "correlation_id": correlation_id,
            "errors": exc.errors(),
            "path": str(request.url.path),
            "method": request.method,
        },
    )

    error_response = {
        "error": {
            "code": "ValidationError",
            "message": "Request validation failed",
            "detail": exc.errors(),
            "path": str(request.url.path),
            "method": request.method,
        },
    }

    if correlation_id:
        error_response["error"]["correlation_id"] = correlation_id

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response,
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    FastAPI exception handler for general exceptions.

    Args:
        request: FastAPI request object
        exc: Exception

    Returns:
        JSONResponse with standardized error format
    """
    correlation_id = get_correlation_id(request)

    logger.error(
        f"Unhandled error on {request.method} {request.url.path}: {exc}",
        extra={
            "correlation_id": correlation_id,
            "path": str(request.url.path),
            "method": request.method,
        },
        exc_info=True,
    )

    error_response = {
        "error": {
            "code": "InternalServerError",
            "message": "An internal error occurred",
            "path": str(request.url.path),
            "method": request.method,
        },
    }

    if correlation_id:
        error_response["error"]["correlation_id"] = correlation_id

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response,
    )


def register_error_handlers(app):
    """
    Register all error handlers with a FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Register HomeIQ error handlers (order matters - most specific first)
    app.add_exception_handler(HomeIQError, homeiq_exception_handler)
    app.add_exception_handler(ValidationError, homeiq_exception_handler)
    app.add_exception_handler(AuthenticationError, homeiq_exception_handler)
    app.add_exception_handler(NotFoundError, homeiq_exception_handler)
    app.add_exception_handler(ConflictError, homeiq_exception_handler)
    app.add_exception_handler(StateMachineError, homeiq_exception_handler)
    app.add_exception_handler(NetworkError, homeiq_exception_handler)
    app.add_exception_handler(ServiceError, homeiq_exception_handler)
    app.add_exception_handler(DatabaseError, homeiq_exception_handler)
    app.add_exception_handler(ConfigurationError, homeiq_exception_handler)

    # Register validation error handler
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Register general exception handler (should be last)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("Error handlers registered")

