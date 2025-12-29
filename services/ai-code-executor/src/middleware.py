"""
Middleware for request/response logging and metrics collection.
"""

import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Simple in-memory metrics (for single-instance deployment)
_metrics = {
    "total_requests": 0,
    "total_executions": 0,
    "successful_executions": 0,
    "failed_executions": 0,
    "total_execution_time": 0.0,
    "total_memory_used": 0.0,
}


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()
        
        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {request.client.host if request.client else 'unknown'}"
        )
        
        # Process request
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"status={response.status_code} duration={duration:.3f}s"
        )
        
        return response


def get_metrics() -> dict[str, float | int]:
    """Get current metrics."""
    return {
        "total_requests": _metrics["total_requests"],
        "total_executions": _metrics["total_executions"],
        "successful_executions": _metrics["successful_executions"],
        "failed_executions": _metrics["failed_executions"],
        "average_execution_time": (
            _metrics["total_execution_time"] / _metrics["total_executions"]
            if _metrics["total_executions"] > 0
            else 0.0
        ),
        "average_memory_used_mb": (
            _metrics["total_memory_used"] / _metrics["total_executions"]
            if _metrics["total_executions"] > 0
            else 0.0
        ),
    }


def record_execution(success: bool, execution_time: float, memory_used_mb: float) -> None:
    """Record execution metrics."""
    _metrics["total_executions"] += 1
    if success:
        _metrics["successful_executions"] += 1
    else:
        _metrics["failed_executions"] += 1
    _metrics["total_execution_time"] += execution_time
    _metrics["total_memory_used"] += memory_used_mb


def record_request() -> None:
    """Record a request."""
    _metrics["total_requests"] += 1

