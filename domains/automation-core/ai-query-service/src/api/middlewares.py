"""
API Middlewares - Authentication, Rate Limiting

Epic 39, Story 39.10: Query Service Implementation
Adapted from ai-automation-service middlewares for the query service.
"""

import asyncio
import contextlib
import logging
import time
from collections import defaultdict, deque

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import settings

logger = logging.getLogger(__name__)

# Configuration constants
MAX_RATE_LIMIT_BUCKETS = 10000
CLEANUP_INTERVAL_SECONDS = 60
RATE_LIMIT_TTL_SECONDS = 7200
DEFAULT_RATE_LIMIT_TOKENS = 100
DEFAULT_REFILL_RATE = 10.0  # tokens per second

# Simple token bucket for rate limiting (can be replaced with Redis in production)
_rate_limit_buckets: dict[str, dict] = {}
_rate_limit_locks: dict[str, asyncio.Lock] = {}

# Background cleanup task reference
_cleanup_task: asyncio.Task | None = None

# Performance metrics (simple in-memory storage)
_performance_metrics: dict[str, deque] = defaultdict(
    lambda: deque(maxlen=1000)
)
_error_counts: dict[str, int] = defaultdict(int)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.

    Features:
    - Token bucket algorithm for smooth rate limiting
    - Per-API-key rate limiting
    - Automatic token refill
    - Background cleanup of inactive buckets
    - Configurable limits per endpoint
    """

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip if rate limiting is disabled
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        # Get API key from header
        api_key = request.headers.get("X-HomeIQ-API-Key") or request.headers.get(
            "Authorization", ""
        ).replace("Bearer ", "")

        if not api_key:
            # No API key - use IP address as identifier
            client_ip = request.client.host if request.client else "unknown"
            identifier = f"ip:{client_ip}"
        else:
            identifier = f"key:{api_key}"

        # Get or create bucket with lock for thread safety
        if identifier not in _rate_limit_buckets:
            _rate_limit_buckets[identifier] = {
                "tokens": DEFAULT_RATE_LIMIT_TOKENS,
                "last_refill": time.time(),
                "last_access": time.time(),
                "capacity": DEFAULT_RATE_LIMIT_TOKENS,
                "refill_rate": DEFAULT_REFILL_RATE,
            }
        if identifier not in _rate_limit_locks:
            _rate_limit_locks[identifier] = asyncio.Lock()

        bucket = _rate_limit_buckets[identifier]
        current_time = time.time()

        async with _rate_limit_locks[identifier]:
            # Refill tokens based on elapsed time
            elapsed = current_time - bucket["last_refill"]
            tokens_to_add = elapsed * bucket["refill_rate"]
            bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = current_time
            bucket["last_access"] = current_time

            # Check if request is allowed
            if bucket["tokens"] < 1:
                retry_after = int(1 / bucket["refill_rate"]) if bucket["refill_rate"] > 0 else 1
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": "Rate limit exceeded. Please try again later.",
                        "retry_after": retry_after,
                    },
                    headers={"Retry-After": str(retry_after)},
                )

            # Consume token
            bucket["tokens"] -= 1

        # Process request with timing
        start_time = time.time()
        response = await call_next(request)
        elapsed_time = time.time() - start_time

        # Track performance metrics (skip health checks to avoid noise)
        if request.url.path not in ["/health", "/docs", "/redoc", "/openapi.json"]:
            endpoint = f"{request.method} {request.url.path}"
            _performance_metrics[endpoint].append(elapsed_time)

            # Track errors (4xx, 5xx)
            if response.status_code >= 400:
                _error_counts[endpoint] += 1

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(bucket["capacity"])
        response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))
        reset_delta = (1 / bucket["refill_rate"]) if bucket["refill_rate"] > 0 else 1
        response.headers["X-RateLimit-Reset"] = str(int(current_time + reset_delta))

        # Add performance header
        response.headers["X-Response-Time"] = f"{elapsed_time:.3f}s"

        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware.

    Validates API keys from X-HomeIQ-API-Key header or Authorization Bearer token.
    Skips authentication for internal service-to-service communication.
    """

    # Internal network prefixes (Docker, private networks)
    INTERNAL_NETWORK_PREFIXES = [
        "172.", "10.", "192.168.", "127.0.0.1", "::1", "localhost",
    ]

    def _is_internal_request(self, request: Request) -> bool:
        """
        Check if request is from an internal service.

        Internal requests are identified by source IP in internal network
        ranges (Docker networks, localhost).
        """
        client_ip = request.client.host if request.client else None
        if client_ip:
            if any(client_ip.startswith(prefix) for prefix in self.INTERNAL_NETWORK_PREFIXES):
                return True
            if client_ip in ["localhost", "127.0.0.1", "::1"]:
                return True

        return False

    async def dispatch(self, request: Request, call_next):
        """Process request with authentication."""
        # Skip authentication for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)

        # Skip authentication for internal service-to-service requests
        if self._is_internal_request(request):
            request.state.authenticated = True
            request.state.internal_service = True
            return await call_next(request)

        # Get API key from header for external requests
        api_key = request.headers.get("X-HomeIQ-API-Key")
        if not api_key:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header.replace("Bearer ", "")

        # Validate API key for external requests
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "authentication_required",
                    "message": (
                        "API key required. Provide X-HomeIQ-API-Key header "
                        "or Authorization Bearer token."
                    ),
                },
            )

        # Validate API key against configured keys
        valid_api_keys = settings.api_keys if settings.api_keys else set()
        if valid_api_keys and api_key not in valid_api_keys:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"error": "invalid_api_key", "message": "Invalid API key."},
            )

        # Store API key in request state for use in endpoints
        request.state.api_key = api_key
        request.state.authenticated = True
        request.state.internal_service = False

        return await call_next(request)


async def start_rate_limit_cleanup():
    """Background task to clean up inactive rate limit buckets."""
    global _cleanup_task  # noqa: PLW0603

    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                current_time = time.time()

                # Remove buckets that haven't been accessed recently
                inactive_keys = [
                    key
                    for key, bucket in _rate_limit_buckets.items()
                    if current_time - bucket["last_access"] > RATE_LIMIT_TTL_SECONDS
                ]

                for key in inactive_keys:
                    del _rate_limit_buckets[key]

                if inactive_keys:
                    logger.debug(
                        "Cleaned up %d inactive rate limit buckets", len(inactive_keys)
                    )

                # Limit total buckets to prevent memory issues
                if len(_rate_limit_buckets) > MAX_RATE_LIMIT_BUCKETS:
                    sorted_buckets = sorted(
                        _rate_limit_buckets.items(), key=lambda x: x[1]["last_access"]
                    )
                    to_remove = len(_rate_limit_buckets) - MAX_RATE_LIMIT_BUCKETS
                    for key, _ in sorted_buckets[:to_remove]:
                        del _rate_limit_buckets[key]
                    logger.warning(
                        "Rate limit bucket limit reached, removed %d oldest buckets",
                        to_remove,
                    )

            except Exception:
                logger.exception("Error in rate limit cleanup")

    _cleanup_task = asyncio.create_task(cleanup_loop())
    logger.info("Rate limit cleanup task started")


async def stop_rate_limit_cleanup():
    """Stop background cleanup task."""
    global _cleanup_task  # noqa: PLW0603
    if _cleanup_task:
        _cleanup_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _cleanup_task
        _cleanup_task = None
        logger.info("Rate limit cleanup task stopped")


def get_performance_metrics() -> dict[str, dict]:
    """
    Get performance metrics for all endpoints.

    Returns:
        Dictionary with endpoint metrics (avg, p95, p99 response times).
    """
    metrics = {}
    for endpoint, times in _performance_metrics.items():
        if not times:
            continue

        sorted_times = sorted(times)
        count = len(sorted_times)

        metrics[endpoint] = {
            "count": count,
            "avg": sum(sorted_times) / count,
            "p95": sorted_times[int(count * 0.95)] if count > 0 else 0,
            "p99": sorted_times[int(count * 0.99)] if count > 0 else 0,
            "min": sorted_times[0] if count > 0 else 0,
            "max": sorted_times[-1] if count > 0 else 0,
        }

    return metrics


def get_error_counts() -> dict[str, int]:
    """Get error counts by endpoint."""
    return dict(_error_counts)


def reset_metrics():
    """Reset all performance metrics (useful for testing)."""
    _performance_metrics.clear()
    _error_counts.clear()
