"""
Shared rate limiter utilities for HomeIQ services.

Provides a lightweight token-bucket implementation that can be reused
across services (admin-api, data-api, etc.) to enforce per-IP throttling.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict

from fastapi import Request, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Features:
    - Per-IP rate limiting
    - Configurable rate and burst size
    - Automatic cleanup of stale entries
    """

    def __init__(self, rate: int = 100, per: int = 60, burst: int = 20):
        """
        Initialize rate limiter.

        Args:
            rate: Maximum requests per time period.
            per: Time period in seconds.
            burst: Maximum burst size (tokens available immediately).
        """

        self.rate = rate
        self.per = per
        self.burst = burst

        self._buckets: Dict[str, Dict] = defaultdict(
            lambda: {"tokens": float(burst), "last_update": datetime.now()}
        )
        self._lock = asyncio.Lock()

        self.total_requests = 0
        self.rate_limited_requests = 0

        logger.info(
            "Rate limiter initialized: %s req/%ss (burst=%s)",
            rate,
            per,
            burst,
        )

    async def check_rate_limit(self, ip: str) -> bool:
        """Return True if the client is within the rate limit."""
        async with self._lock:
            self.total_requests += 1
            now = datetime.now()
            bucket = self._buckets[ip]

            elapsed = (now - bucket["last_update"]).total_seconds()
            tokens_to_add = elapsed * (self.rate / self.per)

            bucket["tokens"] = min(self.burst, bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = now

            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                return True

            self.rate_limited_requests += 1
            return False

    async def cleanup_old_entries(self) -> None:
        """Remove entries that have not been used for more than an hour."""
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=1)
            old_ips = [
                ip for ip, bucket in self._buckets.items() if bucket["last_update"] < cutoff
            ]
            for ip in old_ips:
                del self._buckets[ip]
            if old_ips:
                logger.debug("Cleaned up %s expired rate limiter entries", len(old_ips))

    def get_client_info(self, ip: str) -> tuple[int, float]:
        """Return (remaining_tokens, seconds_until_full_refill) for a client."""
        if ip not in self._buckets:
            return self.burst, 0.0
        bucket = self._buckets[ip]
        now = datetime.now()
        elapsed = (now - bucket["last_update"]).total_seconds()
        tokens_to_add = elapsed * (self.rate / self.per)
        current = min(self.burst, bucket["tokens"] + tokens_to_add)
        remaining = max(0, int(current))
        reset_seconds = (self.burst - current) * (self.per / self.rate) if current < self.burst else 0.0
        return remaining, reset_seconds

    def get_stats(self) -> Dict[str, float | int]:
        """Return statistics for observability endpoints."""
        percentage = 0.0
        if self.total_requests:
            percentage = (self.rate_limited_requests / self.total_requests) * 100
        rate_per_minute = self.rate if self.per == 60 else int(self.rate * (60 / self.per))

        return {
            "total_requests": self.total_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "rate_limit_percentage": round(percentage, 2),
            "active_ips": len(self._buckets),
            "rate_per_minute": rate_per_minute,
            "burst_size": self.burst,
        }


async def rate_limit_middleware(request: Request, call_next, limiter: RateLimiter):
    """
    FastAPI middleware-compatible wrapper around RateLimiter.

    Args:
        request: Incoming request.
        call_next: Next handler in the chain.
        limiter: RateLimiter instance to enforce.
    """

    if request.url.path in ("/health", "/api/health", "/api/v1/health"):
        return await call_next(request)

    client_ip = request.client.host if request.client else "unknown"
    allowed = await limiter.check_rate_limit(client_ip)
    remaining, reset_seconds = limiter.get_client_info(client_ip)

    if not allowed:
        logger.warning("Rate limit exceeded for IP: %s", client_ip)
        response = JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": "Rate limit exceeded. Please try again later.",
                "error_code": "RATE_LIMIT_EXCEEDED",
            },
        )
        response.headers["Retry-After"] = str(int(reset_seconds) + 1)
    else:
        response = await call_next(request)

    response.headers["X-RateLimit-Limit"] = str(limiter.rate)
    response.headers["X-RateLimit-Remaining"] = str(remaining)
    response.headers["X-RateLimit-Reset"] = str(int(reset_seconds))
    return response


def create_write_rate_limiter() -> RateLimiter:
    """Create a rate limiter configured for write endpoints (20 req/min)."""
    return RateLimiter(rate=20, per=60, burst=5)

