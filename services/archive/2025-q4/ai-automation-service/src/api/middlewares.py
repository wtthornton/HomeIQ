"""
API Middlewares - Authentication, Idempotency and Rate Limiting
"""

import asyncio
import logging
import time
from collections import OrderedDict, defaultdict
from collections.abc import Callable

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..config import settings
from .dependencies.auth import AuthContext

logger = logging.getLogger(__name__)

# Configuration constants
MAX_IDEMPOTENCY_ENTRIES = 5000  # Max entries before LRU eviction
MAX_RATE_LIMIT_BUCKETS = 10000  # Max buckets before cleanup
CLEANUP_INTERVAL_SECONDS = 60  # Background cleanup every 60 seconds
IDEMPOTENCY_TTL_SECONDS = 3600  # 1 hour TTL
RATE_LIMIT_TTL_SECONDS = 7200  # 2 hours TTL for inactive buckets

# Simple in-memory store for idempotency with LRU support
# OrderedDict maintains insertion order for LRU eviction
_idempotency_store: OrderedDict[str, tuple] = OrderedDict()  # key -> (response, timestamp)

# Simple token bucket for rate limiting (can be replaced with Redis)
_rate_limit_buckets: dict[str, dict] = defaultdict(lambda: {
    "tokens": 100,  # Default: 100 requests (10x increase)
    "last_refill": time.time(),
    "last_access": time.time(),  # Track last access for TTL cleanup
    "capacity": 100,  # 10x increase: 100 tokens capacity
    "refill_rate": 10.0  # 10 tokens per second (supports 600/min = 10/sec)
})

# Background cleanup task reference
_cleanup_task: asyncio.Task | None = None


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

                        # Store in cache with LRU tracking
                        # Move to end if exists (LRU: most recently used)
                        if cache_key in _idempotency_store:
                            # Update timestamp and move to end (mark as recently used)
                            _idempotency_store[cache_key] = (cached_data, time.time())
                            _idempotency_store.move_to_end(cache_key)
                        else:
                            # Check max size before adding
                            if len(_idempotency_store) >= MAX_IDEMPOTENCY_ENTRIES:
                                # Remove oldest entry (LRU eviction)
                                oldest_key = next(iter(_idempotency_store))
                                del _idempotency_store[oldest_key]
                                logger.debug(f"LRU eviction: Removed oldest idempotency key: {oldest_key[:50]}...")
                            
                            # Add new entry (automatically at end in OrderedDict)
                            _idempotency_store[cache_key] = (cached_data, time.time())
                    else:
                        logger.debug(f"Skipping idempotency cache for non-JSON response: {content_type}")
                except Exception as e:
                    logger.warning(f"Failed to cache idempotent response: {e}")

            return response
        else:
            # No idempotency key, process normally
            return await call_next(request)

    def _cleanup_old_entries(self):
        """Clean up expired entries (legacy method, kept for compatibility)"""
        # Background task now handles cleanup, but we can still do immediate cleanup if needed
        current_time = time.time()
        expired_keys = [
            k for k, (_, ts) in list(_idempotency_store.items())
            if current_time - ts > self.ttl_seconds
        ]
        for k in expired_keys:
            del _idempotency_store[k]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired idempotency entries")


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

        # Update last access time for TTL cleanup
        bucket = _rate_limit_buckets[identifier]
        bucket["last_access"] = time.time()

        # Process request
        response = await call_next(request)

        # Add rate limit headers
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
        # CRITICAL: Authentication is mandatory - always enabled if API key is set
        # If no API key is configured, service will fail to start (security requirement)
        self.api_key = settings.ai_automation_api_key
        self.admin_key = settings.ai_automation_admin_api_key or self.api_key
        
        # Require API key to be set (cannot be empty or default value)
        if not self.api_key or self.api_key == "change-me":
            raise ValueError(
                "CRITICAL: AI_AUTOMATION_API_KEY must be set. "
                "Authentication cannot be disabled. Set AI_AUTOMATION_API_KEY environment variable."
            )
        
        self.enabled = True  # Always enabled when API key is set
        self.header_name = header_name
        self.public_paths = public_paths or [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/metrics",
        ]
        
        logger.info("✅ Authentication middleware enabled (mandatory)")

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


# Background cleanup task
async def _cleanup_expired_entries():
    """
    Background task to periodically clean up expired entries from in-memory stores.
    Runs every CLEANUP_INTERVAL_SECONDS to prevent memory leaks.
    """
    global _idempotency_store, _rate_limit_buckets
    
    while True:
        try:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            current_time = time.time()
            
            # Cleanup idempotency store (expired entries)
            expired_idempotency = [
                k for k, (_, ts) in list(_idempotency_store.items())
                if current_time - ts > IDEMPOTENCY_TTL_SECONDS
            ]
            for k in expired_idempotency:
                del _idempotency_store[k]
            
            if expired_idempotency:
                logger.info(f"Background cleanup: Removed {len(expired_idempotency)} expired idempotency entries")
            
            # Cleanup rate limit buckets (inactive entries)
            # Only cleanup if we have too many buckets
            if len(_rate_limit_buckets) > MAX_RATE_LIMIT_BUCKETS:
                inactive_buckets = [
                    identifier for identifier, bucket in list(_rate_limit_buckets.items())
                    if current_time - bucket.get("last_access", 0) > RATE_LIMIT_TTL_SECONDS
                ]
                for identifier in inactive_buckets:
                    del _rate_limit_buckets[identifier]
                
                if inactive_buckets:
                    logger.info(f"Background cleanup: Removed {len(inactive_buckets)} inactive rate limit buckets")
            
            # Additional LRU eviction if still over limit after TTL cleanup
            while len(_idempotency_store) > MAX_IDEMPOTENCY_ENTRIES:
                oldest_key = next(iter(_idempotency_store))
                del _idempotency_store[oldest_key]
                logger.debug(f"LRU eviction: Removed {oldest_key[:50]}... (store size: {len(_idempotency_store)})")
            
        except asyncio.CancelledError:
            logger.info("Background cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in background cleanup task: {e}", exc_info=True)
            # Continue running even if cleanup fails
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)


def start_background_cleanup():
    """Start the background cleanup task. Call this from application startup."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_expired_entries())
        logger.info("Background cleanup task started")
    return _cleanup_task


def stop_background_cleanup():
    """Stop the background cleanup task. Call this from application shutdown."""
    global _cleanup_task
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        logger.info("Background cleanup task stopped")

