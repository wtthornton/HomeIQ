"""
API Middlewares - Authentication, Rate Limiting (2025 Patterns)

Epic 39, Story 39.10: Automation Service Foundation
Following 2025 FastAPI best practices with async/await and proper dependency injection.
"""

import asyncio
import logging
import time
from collections import OrderedDict, defaultdict, deque
from typing import Annotated

from fastapi import Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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
_rate_limit_buckets: dict[str, dict] = defaultdict(lambda: {
    "tokens": DEFAULT_RATE_LIMIT_TOKENS,
    "last_refill": time.time(),
    "last_access": time.time(),
    "capacity": DEFAULT_RATE_LIMIT_TOKENS,
    "refill_rate": DEFAULT_REFILL_RATE
})

# Background cleanup task reference
_cleanup_task: asyncio.Task | None = None

# HTTP Bearer token security
security = HTTPBearer(auto_error=False)

# Performance metrics (simple in-memory storage for single-user)
_performance_metrics: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))  # Store last 1000 requests per endpoint
_error_counts: dict[str, int] = defaultdict(int)  # Error counts by endpoint


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm (2025 pattern).
    
    Features:
    - Token bucket algorithm for smooth rate limiting
    - Per-API-key rate limiting
    - Automatic token refill
    - Background cleanup of inactive buckets
    - Configurable limits per endpoint
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for health checks
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get("X-HomeIQ-API-Key") or request.headers.get("Authorization", "").replace("Bearer ", "")
        
        if not api_key:
            # No API key - use IP address as identifier
            client_ip = request.client.host if request.client else "unknown"
            identifier = f"ip:{client_ip}"
        else:
            identifier = f"key:{api_key}"
        
        # Check rate limit
        bucket = _rate_limit_buckets[identifier]
        current_time = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = current_time - bucket["last_refill"]
        tokens_to_add = elapsed * bucket["refill_rate"]
        bucket["tokens"] = min(bucket["capacity"], bucket["tokens"] + tokens_to_add)
        bucket["last_refill"] = current_time
        bucket["last_access"] = current_time
        
        # Check if request is allowed
        if bucket["tokens"] < 1:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "rate_limit_exceeded",
                    "message": "Rate limit exceeded. Please try again later.",
                    "retry_after": int(1 / bucket["refill_rate"])  # seconds until next token
                },
                headers={"Retry-After": str(int(1 / bucket["refill_rate"]))}
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
        response.headers["X-RateLimit-Reset"] = str(int(current_time + (1 / bucket["refill_rate"])))
        
        # Add performance header
        response.headers["X-Response-Time"] = f"{elapsed_time:.3f}s"
        
        return response


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware (2025 pattern).
    
    Validates API keys from X-HomeIQ-API-Key header or Authorization Bearer token.
    """
    
    async def dispatch(self, request: Request, call_next):
        """Process request with authentication."""
        # Skip authentication for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json", "/"]:
            return await call_next(request)
        
        # Get API key from header
        api_key = request.headers.get("X-HomeIQ-API-Key")
        if not api_key:
            # Try Authorization header
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                api_key = auth_header.replace("Bearer ", "")
        
        # Validate API key (simple check - can be enhanced with database lookup)
        if not api_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "authentication_required",
                    "message": "API key required. Provide X-HomeIQ-API-Key header or Authorization Bearer token."
                }
            )
        
        # Store API key in request state for use in endpoints
        request.state.api_key = api_key
        request.state.authenticated = True
        
        # Process request
        return await call_next(request)


async def start_rate_limit_cleanup():
    """Background task to clean up inactive rate limit buckets."""
    global _cleanup_task
    
    async def cleanup_loop():
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                current_time = time.time()
                
                # Remove buckets that haven't been accessed recently
                inactive_keys = [
                    key for key, bucket in _rate_limit_buckets.items()
                    if current_time - bucket["last_access"] > RATE_LIMIT_TTL_SECONDS
                ]
                
                for key in inactive_keys:
                    del _rate_limit_buckets[key]
                
                if inactive_keys:
                    logger.debug(f"Cleaned up {len(inactive_keys)} inactive rate limit buckets")
                
                # Limit total buckets to prevent memory issues
                if len(_rate_limit_buckets) > MAX_RATE_LIMIT_BUCKETS:
                    # Remove oldest buckets (LRU)
                    sorted_buckets = sorted(
                        _rate_limit_buckets.items(),
                        key=lambda x: x[1]["last_access"]
                    )
                    to_remove = len(_rate_limit_buckets) - MAX_RATE_LIMIT_BUCKETS
                    for key, _ in sorted_buckets[:to_remove]:
                        del _rate_limit_buckets[key]
                    logger.warning(f"Rate limit bucket limit reached, removed {to_remove} oldest buckets")
            
            except Exception as e:
                logger.error(f"Error in rate limit cleanup: {e}", exc_info=True)
    
    _cleanup_task = asyncio.create_task(cleanup_loop())
    logger.info("✅ Rate limit cleanup task started")


async def stop_rate_limit_cleanup():
    """Stop background cleanup task."""
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
        _cleanup_task = None
        logger.info("✅ Rate limit cleanup task stopped")


def get_performance_metrics() -> dict[str, dict]:
    """
    Get performance metrics for all endpoints.
    
    Returns:
        Dictionary with endpoint metrics (avg, p95, p99 response times)
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
            "max": sorted_times[-1] if count > 0 else 0
        }
    
    return metrics


def get_error_counts() -> dict[str, int]:
    """Get error counts by endpoint."""
    return dict(_error_counts)


def reset_metrics():
    """Reset all performance metrics (useful for testing)."""
    global _performance_metrics, _error_counts
    _performance_metrics.clear()
    _error_counts.clear()

