"""
Correlation ID Middleware with Trace Context Integration

Provides correlation ID middleware that integrates with OpenTelemetry trace context.
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from ..logging_config import generate_correlation_id, get_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)

# OpenTelemetry imports (optional)
try:
    from opentelemetry import trace
    OPENTELEMETRY_AVAILABLE = True
except ImportError:
    OPENTELEMETRY_AVAILABLE = False


class CorrelationMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for correlation ID handling with trace context integration.

    Automatically:
    - Extracts correlation ID from request headers (X-Correlation-ID)
    - Generates new correlation ID if not present
    - Sets correlation ID in context
    - Adds correlation ID to response headers
    - Integrates with OpenTelemetry trace context
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID"):
        """
        Initialize correlation middleware.

        Args:
            app: ASGI application
            header_name: Header name for correlation ID (default: X-Correlation-ID)
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        """
        Process request with correlation ID.

        Args:
            request: FastAPI request
            call_next: Next middleware/route handler

        Returns:
            Response with correlation ID header
        """
        # Get correlation ID from header or generate new one
        corr_id = request.headers.get(self.header_name.lower()) or request.headers.get(self.header_name)

        if not corr_id:
            corr_id = generate_correlation_id()

        # Set in context
        set_correlation_id(corr_id)

        # Store in request state for access in routes
        request.state.correlation_id = corr_id

        # Integrate with OpenTelemetry trace context if available
        if OPENTELEMETRY_AVAILABLE:
            try:
                span = trace.get_current_span()
                if span and span.is_recording():
                    # Add correlation ID as span attribute
                    span.set_attribute("correlation_id", corr_id)
            except Exception:
                # Silently fail if trace context unavailable
                pass

        # Process request
        response = await call_next(request)

        # Add correlation ID to response headers
        response.headers[self.header_name] = corr_id

        return response


def get_correlation_id_from_request(request: Request) -> str | None:
    """
    Get correlation ID from FastAPI request.

    Args:
        request: FastAPI request object

    Returns:
        Correlation ID or None
    """
    return getattr(request.state, "correlation_id", None) or get_correlation_id()


def set_correlation_id_in_request(request: Request, corr_id: str):
    """
    Set correlation ID in FastAPI request state.

    Args:
        request: FastAPI request object
        corr_id: Correlation ID to set
    """
    request.state.correlation_id = corr_id
    set_correlation_id(corr_id)

