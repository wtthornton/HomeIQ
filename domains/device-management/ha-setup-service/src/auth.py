"""API key authentication for destructive endpoints."""

from __future__ import annotations

import os
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)
_api_key = os.getenv("HA_SETUP_API_KEY", "")


async def verify_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """Verify API key for destructive endpoints using timing-safe comparison."""
    if not _api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured on server",
        )
    if not secrets.compare_digest(api_key, _api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )
    return api_key
