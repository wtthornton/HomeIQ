"""HTTP middleware for ML Service — request ID tracing and rate limiting."""

from __future__ import annotations

import os
import time

RATE_LIMIT_WINDOW = int(os.getenv("ML_RATE_LIMIT_WINDOW", "60"))
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("ML_RATE_LIMIT_MAX_REQUESTS", "120"))
_rate_limit_store: dict[str, list[float]] = {}


def _check_rate_limit(client_ip: str) -> bool:
    """Return True if the request is allowed, False if rate-limited."""
    now = time.monotonic()
    window = _rate_limit_store.setdefault(client_ip, [])
    cutoff = now - RATE_LIMIT_WINDOW
    _rate_limit_store[client_ip] = window = [t for t in window if t > cutoff]
    if len(window) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    window.append(now)
    return True


def _parse_allowed_origins(raw_origins: str | None) -> list[str]:
    """Parse comma-separated origins or return defaults."""
    default = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]
    if raw_origins:
        parsed = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
        if parsed:
            return parsed
    return default
