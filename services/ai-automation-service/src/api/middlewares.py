"""
API Middlewares - Authentication, Idempotency and Rate Limiting
"""

import logging
import time
from collections import defaultdict
from collections.abc import Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import settings
from .dependencies.auth import AuthContext

logger = logging.getLogger(__name__)


# Simple in-memory store for idempotency (can be replaced with Redis)
_idempotency_store: dict[str, tuple] = {}  # key -> (response, timestamp)

# Simple token bucket for rate limiting (can be replaced with Redis)
_rate_limit_buckets: dict[str, dict] = defaultdict(lambda: {
    "tokens": 100,  # Default: 100 requests (10x increase)
    "last_refill": time.time(),
    "capacity": 100,  # 10x increase: 100 tokens capacity
    "refill_rate": 10.0  # 10 tokens per second (supports 600/min = 10/sec)
})


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """
    Idempotency middleware for POST endpoints.
    
    Requires Idempotency-Key header on POST requests.
    Returns cached response for duplicate keys.
    """

    def __init__(self, app, key_header: str = "Idempotency-Key"):
        super().__init__(app)
        self.key_header = key_header
        self.ttl_seconds = 3600  # 1 hour TTL for idempotency keys

    async def dispatch(self, request: Request, call_next: Callable):
        # Only apply to POST requests
        if request.method != "POST":
            return await call_next(request)

        # Check for idempotency key
        idempotency_key = request.headers.get(self.key_header)

        if idempotency_key:
            # Generate cache key from method + path + key
            cache_key = f"{request.method}:{request.url.path}:{idempotency_key}"

            # Check cache
            if cache_key in _idempotency_store:
                cached_response, timestamp = _idempotency_store[cache_key]

                # Check TTL
                if time.time() - timestamp < self.ttl_seconds:
                    logger.info(f"Idempotent request: {idempotency_key}")
                    return JSONResponse(
                        content=cached_response,
                        status_code=status.HTTP_200_OK
                    )
                else:
                    # Expired, remove from cache
                    del _idempotency_store[cache_key]

            # Process request
            response = await call_next(request)

            # Cache successful responses (only JSON responses)
            if response.status_code < 400:
                try:
                    # Check if response is JSON
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        # Read response body
                        response_body = await response.body()
                        import json
                        cached_data = json.loads(response_body)

                        # Store in cache
                        _idempotency_store[cache_key] = (cached_data, time.time())

                        # Cleanup old entries (simple cleanup)
                        self._cleanup_old_entries()
                    else:
                        logger.debug(f"Skipping idempotency cache for non-JSON response: {content_type}")
                except Exception as e:
                    logger.warning(f"Failed to cache idempotent response: {e}")

            return response
        else:
            # No idempotency key, process normally
            return await call_next(request)

    def _cleanup_old_entries(self):
        """Clean up expired entries (simple cleanup every 100 requests)"""
        if len(_idempotency_store) > 1000:
            current_time = time.time()
            expired_keys = [
                k for k, (_, ts) in _idempotency_store.items()
                if current_time - ts > self.ttl_seconds
            ]
            for k in expired_keys:
                del _idempotency_store[k]


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware using token bucket algorithm.
    
    Per-user/IP rate limiting with configurable limits.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 600,  # External API consumers
        requests_per_hour: int = 10000,
        internal_requests_per_minute: int = 2000,  # Internal traffic (Docker network)
        key_header: str = "X-User-ID"
    ):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.internal_requests_per_minute = internal_requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.key_header = key_header
        # Internal network prefixes (Docker, private networks)
        # Context7 Best Practice: Clear configuration for maintainability
        self.internal_network_prefixes = ['172.', '10.', '192.168.', '127.0.0.1']
        # Calculate refill rates: requests_per_minute / 60 = tokens per second
        self.refill_rate = requests_per_minute / 60.0
        self.internal_refill_rate = internal_requests_per_minute / 60.0
        # Set capacity to allow 1 minute of burst
        self.bucket_capacity = requests_per_minute
        self.internal_bucket_capacity = internal_requests_per_minute

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip rate limiting entirely if disabled (for internal single-home projects)
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Exempt health checks, status endpoints, and read-only GET endpoints from rate limiting
        # Context7 Best Practice: Early return for exempt paths (performance)
        exempt_paths = [
            '/health',
            '/api/health',
            '/api/analysis/status',
            '/api/analysis/schedule'
        ]

        # Exempt read-only GET endpoints (they're just reading data, not causing load)
        read_only_get_paths = [
            '/api/patterns/list',
            '/api/patterns/stats',
            '/api/patterns/',  # Pattern detail endpoints (GET)
            '/api/synergies',  # Synergies list (GET)
            '/api/synergies/stats',
            '/api/suggestions',  # Suggestions list (GET)
            '/api/devices/names',  # Device name lookup (GET)
        ]

        # Check if this is a read-only GET request
        is_read_only_get = (
            request.method == "GET" and
            any(request.url.path.startswith(path) for path in read_only_get_paths)
        )

        if any(request.url.path.startswith(path) for path in exempt_paths) or is_read_only_get:
            # Process request without rate limiting
            return await call_next(request)

        # Get identifier (user ID or IP)
        identifier = request.headers.get(self.key_header)
        client_ip = request.client.host if request.client else "unknown"

        if not identifier:
            # Fallback to IP
            identifier = client_ip

        # Detect internal traffic using actual IP address (not just identifier)
        # Context7: Clear separation of concerns - check both identifier and IP
        is_internal = (
            any(identifier.startswith(prefix) for prefix in self.internal_network_prefixes) or
            any(client_ip.startswith(prefix) for prefix in self.internal_network_prefixes)
        )

        # Use appropriate limits based on traffic type
        if is_internal:
            effective_limit = self.internal_requests_per_minute
            effective_refill = self.internal_refill_rate
            effective_capacity = self.internal_bucket_capacity
        else:
            effective_limit = self.requests_per_minute
            effective_refill = self.refill_rate
            effective_capacity = self.bucket_capacity

        # Check rate limit with appropriate bucket
        if not self._check_rate_limit(identifier, effective_refill, effective_capacity):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {effective_limit}/min, {self.requests_per_hour}/hour"
                },
                headers={
                    "Retry-After": "60"
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        bucket = _rate_limit_buckets[identifier]
        response.headers["X-RateLimit-Limit"] = str(effective_limit)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket["tokens"]))

        return response

    def _check_rate_limit(
        self,
        identifier: str,
        refill_rate: float | None = None,
        capacity: int | None = None
    ) -> bool:
        """
        Check if request is within rate limit.
        
        Context7 Best Practice: Flexible parameters for different rate limit configurations.
        
        Args:
            identifier: Client identifier (IP or user ID)
            refill_rate: Tokens per second (uses instance default if None)
            capacity: Maximum bucket capacity (uses instance default if None)
        
        Returns:
            True if request allowed, False if rate limit exceeded
        """
        bucket = _rate_limit_buckets[identifier]
        current_time = time.time()

        # Use provided refill_rate and capacity, or defaults
        effective_refill_rate = refill_rate if refill_rate is not None else self.refill_rate
        effective_capacity = capacity if capacity is not None else self.bucket_capacity

        # Initialize bucket with correct capacity and refill rate if not set
        if "capacity" not in bucket or bucket.get("capacity") != effective_capacity:
            bucket["capacity"] = effective_capacity
            bucket["tokens"] = min(bucket.get("tokens", effective_capacity), effective_capacity)

        if "refill_rate" not in bucket or bucket.get("refill_rate") != effective_refill_rate:
            bucket["refill_rate"] = effective_refill_rate

        # Refill tokens
        time_since_refill = current_time - bucket["last_refill"]
        tokens_to_add = time_since_refill * bucket["refill_rate"]
        bucket["tokens"] = min(
            bucket["capacity"],
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_refill"] = current_time

        # Reset hourly counters if needed
        hour_start = bucket.get("hour_start", current_time)
        if current_time - hour_start >= 3600:
            bucket["hour_start"] = current_time
            bucket["requests_this_hour"] = 0

        bucket.setdefault("requests_this_hour", 0)

        # Check both token bucket (per-minute) and hourly allowance
        if bucket["tokens"] >= 1.0 and bucket["requests_this_hour"] < self.requests_per_hour:
            bucket["tokens"] -= 1.0
            bucket["requests_this_hour"] += 1
            return True

        logger.warning(f"Rate limit exceeded for {identifier}")
        return False


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Simple API key authentication with optional admin key."""

    def __init__(
        self,
        app,
        enabled: bool = True,
        public_paths: list[str] | None = None,
        header_name: str = "X-HomeIQ-API-Key",
    ):
        super().__init__(app)
        self.enabled = enabled and bool(settings.ai_automation_api_key)
        self.header_name = header_name
        self.public_paths = public_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
        ]
        self.api_key = settings.ai_automation_api_key
        self.admin_key = settings.ai_automation_admin_api_key or self.api_key

        if not self.enabled:
            logger.warning("Authentication middleware disabled. Set ENABLE_AUTHENTICATION=true to enable.")
        elif self.api_key == "change-me":
            logger.warning(
                "Authentication middleware enabled but default API key is still 'change-me'. "
                "Update infrastructure/env.ai-automation."
            )

    async def dispatch(self, request: Request, call_next: Callable):
        if not self.enabled or self._is_public_path(request.url.path):
            return await call_next(request)

        provided_key = self._extract_api_key(request)
        if not provided_key:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "detail": f"Missing {self.header_name} or Authorization header",
                },
            )

        role = self._determine_role(provided_key)
        if role is None:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error": "Unauthorized",
                    "detail": "Invalid API key",
                },
            )

        request.state.auth_context = AuthContext(role=role, token=provided_key)
        return await call_next(request)

    def _is_public_path(self, path: str) -> bool:
        return any(path == public or path.startswith(f"{public}/") for public in self.public_paths)

    def _extract_api_key(self, request: Request) -> str | None:
        api_key = request.headers.get(self.header_name)
        if api_key:
            return api_key.strip()

        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            return auth_header.split(" ", 1)[1].strip()

        return None

    def _determine_role(self, key: str) -> str | None:
        if key == self.admin_key:
            return "admin"
        if key == self.api_key:
            return "user"
        return None

