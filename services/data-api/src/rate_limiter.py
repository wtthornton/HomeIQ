"""
Simple rate limiter middleware for API protection
"""

import logging
from typing import Dict
from datetime import datetime, timedelta
from collections import defaultdict
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse
import asyncio

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter

    Features:
    - Per-IP rate limiting
    - Configurable rate and burst size
    - Automatic cleanup of old entries
    """

    def __init__(self, rate: int = 100, per: int = 60, burst: int = 20):
        """
        Initialize rate limiter

        Args:
            rate: Maximum requests per time period
            per: Time period in seconds
            burst: Maximum burst size (tokens available immediately)
        """
        self.rate = rate  # requests per period
        self.per = per    # period in seconds
        self.burst = burst

        # Token buckets: {ip: {"tokens": float, "last_update": datetime}}
        self._buckets: Dict[str, Dict] = defaultdict(
            lambda: {"tokens": float(burst), "last_update": datetime.now()}
        )
        self._lock = asyncio.Lock()

        # Stats
        self.total_requests = 0
        self.rate_limited_requests = 0

        logger.info(f"Rate limiter initialized: {rate} req/{per}s, burst={burst}")

    async def check_rate_limit(self, ip: str) -> bool:
        """
        Check if request is within rate limit

        Args:
            ip: Client IP address

        Returns:
            True if allowed, False if rate limited
        """
        async with self._lock:
            self.total_requests += 1
            now = datetime.now()
            bucket = self._buckets[ip]

            # Calculate tokens to add based on time elapsed
            time_passed = (now - bucket["last_update"]).total_seconds()
            tokens_to_add = time_passed * (self.rate / self.per)

            # Add tokens (capped at burst size)
            bucket["tokens"] = min(self.burst, bucket["tokens"] + tokens_to_add)
            bucket["last_update"] = now

            # Check if we have tokens available
            if bucket["tokens"] >= 1.0:
                bucket["tokens"] -= 1.0
                return True
            else:
                self.rate_limited_requests += 1
                return False

    async def cleanup_old_entries(self):
        """Remove IP entries older than 1 hour"""
        async with self._lock:
            now = datetime.now()
            cutoff = now - timedelta(hours=1)

            old_ips = [
                ip for ip, bucket in self._buckets.items()
                if bucket["last_update"] < cutoff
            ]

            for ip in old_ips:
                del self._buckets[ip]

            if old_ips:
                logger.debug(f"Cleaned up {len(old_ips)} old rate limiter entries")

    def get_stats(self) -> Dict:
        """Get rate limiter statistics"""
        rate_limit_percentage = 0.0
        if self.total_requests > 0:
            rate_limit_percentage = (
                self.rate_limited_requests / self.total_requests * 100
            )

        return {
            "total_requests": self.total_requests,
            "rate_limited_requests": self.rate_limited_requests,
            "rate_limit_percentage": round(rate_limit_percentage, 2),
            "active_ips": len(self._buckets),
            "rate_per_minute": self.rate if self.per == 60 else int(self.rate * (60 / self.per)),
            "burst_size": self.burst
        }


# Global rate limiter instance (100 req/min, burst of 20)
rate_limiter = RateLimiter(rate=100, per=60, burst=20)


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate limiting middleware

    Limits requests per IP address
    """
    # Skip rate limiting for health check
    if request.url.path == "/health":
        return await call_next(request)

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"

    # Check rate limit
    allowed = await rate_limiter.check_rate_limit(client_ip)

    if not allowed:
        logger.warning(f"Rate limit exceeded for IP: {client_ip}")
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error": "Rate limit exceeded. Please try again later.",
                "error_code": "RATE_LIMIT_EXCEEDED"
            }
        )

    # Process request
    response = await call_next(request)
    return response
