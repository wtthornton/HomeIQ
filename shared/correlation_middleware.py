"""
Correlation ID Middleware for Request Tracking Across Services
"""

import logging
import time
from collections.abc import Callable
from functools import wraps

from aiohttp.web import middleware

from .logging_config import correlation_id, generate_correlation_id, get_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)


class CorrelationMiddleware:
    """Middleware for handling correlation IDs in web frameworks"""

    def __init__(self, app=None, header_name: str = "X-Correlation-ID"):
        self.app = app
        self.header_name = header_name
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        """Initialize the middleware with the app"""
        app.before_request(self.before_request)
        app.after_request(self.after_request)

    def before_request(self):
        """Set up correlation ID before request processing"""
        from flask import request

        # Get correlation ID from header or generate new one
        corr_id = request.headers.get(self.header_name)
        if not corr_id:
            corr_id = generate_correlation_id()

        # Set in context
        set_correlation_id(corr_id)

        # Add to request context for later use
        request.correlation_id = corr_id

    def after_request(self, response):
        """Add correlation ID to response headers"""
        corr_id = get_correlation_id()
        if corr_id:
            response.headers[self.header_name] = corr_id
        return response


def correlation_context(corr_id: str | None = None):
    """Context manager for correlation ID handling"""
    class CorrelationContext:
        def __init__(self, correlation_id: str | None = None):
            self.correlation_id = correlation_id or generate_correlation_id()
            self.old_correlation_id = None

        def __enter__(self):
            self.old_correlation_id = get_correlation_id()
            set_correlation_id(self.correlation_id)
            return self.correlation_id

        def __exit__(self, exc_type, exc_val, exc_tb):
            if self.old_correlation_id:
                set_correlation_id(self.old_correlation_id)
            else:
                correlation_id.set(None)

    return CorrelationContext(corr_id)


def with_correlation_id(corr_id: str | None = None):
    """Decorator to add correlation ID to function execution"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            with correlation_context(corr_id):
                return func(*args, **kwargs)
        return wrapper
    return decorator


def propagate_correlation_id(headers: dict, header_name: str = "X-Correlation-ID") -> dict:
    """Add correlation ID to headers for service-to-service communication"""
    corr_id = get_correlation_id()
    if corr_id:
        headers[header_name] = corr_id
    return headers


def extract_correlation_id(headers: dict, header_name: str = "X-Correlation-ID") -> str | None:
    """Extract correlation ID from headers"""
    return headers.get(header_name)


class FastAPICorrelationMiddleware:
    """Correlation ID middleware for FastAPI"""

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        self.app = app
        self.header_name = header_name

    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Get correlation ID from headers
        headers = dict(scope.get("headers", []))
        corr_id = headers.get(self.header_name.encode(), b"").decode()

        if not corr_id:
            corr_id = generate_correlation_id()

        # Set in context
        set_correlation_id(corr_id)

        # Add to scope for later use
        scope["correlation_id"] = corr_id

        # Create new send function to add correlation ID to response headers
        async def send_with_correlation(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((self.header_name.encode(), corr_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_correlation)


class AioHTTPCorrelationMiddleware:
    """Correlation ID middleware for aiohttp"""

    def __init__(self, header_name: str = "X-Correlation-ID"):
        self.header_name = header_name

    async def __call__(self, request, handler):
        """Process request with correlation ID"""
        # Check if this is actually a request object
        if not hasattr(request, "headers"):
            # This is not a request, pass through
            return await handler(request)

        # Get correlation ID from header or generate new one
        corr_id = request.headers.get(self.header_name)
        if not corr_id:
            corr_id = generate_correlation_id()

        # Set in context
        set_correlation_id(corr_id)

        try:
            # Process request
            response = await handler(request)

            # Add correlation ID to response headers
            if hasattr(response, "headers"):
                response.headers[self.header_name] = corr_id

            return response
        except Exception as e:
            # If handler fails, still return the error response
            logger.exception(f"Handler failed: {e}")
            raise


def create_correlation_context(corr_id: str | None = None) -> dict:
    """Create a context dictionary with correlation ID for async operations"""
    correlation_id_value = corr_id or generate_correlation_id()
    return {
        "correlation_id": correlation_id_value,
        "start_time": time.time(),
    }


def update_correlation_context(context: dict, **updates) -> dict:
    """Update correlation context with additional information"""
    context.update(updates)
    return context


def get_correlation_context() -> dict:
    """Get current correlation context"""
    return {
        "correlation_id": get_correlation_id(),
        "timestamp": time.time(),
    }


def create_correlation_middleware(header_name: str = "X-Correlation-ID"):
    """
    Create a correlation ID middleware factory for aiohttp.

    This follows the proper aiohttp middleware pattern where middleware
    functions are created by factory functions.

    Usage:
        app = web.Application(middlewares=[create_correlation_middleware()])
    """
    @middleware
    async def correlation_middleware(request, handler):
        """Process request with correlation ID"""
        # Get correlation ID from header or generate new one
        corr_id = request.headers.get(header_name)
        if not corr_id:
            corr_id = generate_correlation_id()

        # Set in context
        set_correlation_id(corr_id)

        # Process request
        response = await handler(request)

        # Add correlation ID to response headers
        response.headers[header_name] = corr_id

        return response

    return correlation_middleware
