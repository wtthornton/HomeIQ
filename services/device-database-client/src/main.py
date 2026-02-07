"""
Device Database Client Service
Phase 3.1: Client for external Device Database API

Queries external Device Database API (when available), caches device information locally,
and falls back to local intelligence if Device Database unavailable.
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

import uvicorn
from fastapi import FastAPI, Query
from pydantic import BaseModel

from src.cache import DeviceCache
from src.db_client import DeviceDatabaseClient
from src.sync_service import DeviceSyncService

logger = logging.getLogger("device-database-client")


# --- Pydantic request/response models ---

class DeviceLookupRequest(BaseModel):
    manufacturer: str
    model: str


class DeviceSearchRequest(BaseModel):
    device_type: str | None = None
    filters: dict[str, Any] | None = None

    # Whitelist allowed filter keys
    ALLOWED_FILTER_KEYS: set[str] = {"price_range", "manufacturer", "features", "rating_min"}

    def safe_filters(self) -> dict[str, Any] | None:
        if not self.filters:
            return None
        return {k: v for k, v in self.filters.items() if k in self.ALLOWED_FILTER_KEYS}


class DeviceInfoResponse(BaseModel):
    manufacturer: str
    model: str
    device_info: dict[str, Any]


class CacheStatusResponse(BaseModel):
    cache_dir: str
    ttl_hours: int
    entries_count: int


class SyncStatusResponse(BaseModel):
    running: bool
    last_sync: str | None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifecycle"""
    logger.info("Device Database Client Service starting up...")

    # Create DeviceDatabaseClient
    db_client = DeviceDatabaseClient()
    app.state.db_client = db_client

    # Create DeviceCache
    cache_dir = os.getenv("DEVICE_CACHE_DIR", "data/device_cache")
    cache = DeviceCache(cache_dir=cache_dir)
    app.state.cache = cache

    # Create and start DeviceSyncService
    sync_service = DeviceSyncService(db_client=db_client, cache=cache)
    app.state.sync_service = sync_service
    await sync_service.start()

    yield

    # Shutdown
    await sync_service.stop()
    await db_client.close()
    logger.info("Device Database Client Service shutting down...")


app = FastAPI(
    title="Device Database Client Service",
    version="1.0.0",
    description="Client for external Device Database API with local caching",
    lifespan=lifespan
)


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint"""
    cache: DeviceCache = app.state.cache
    db_client: DeviceDatabaseClient = app.state.db_client

    # Check if cache directory is writable
    cache_writable = False
    try:
        cache_writable = os.access(str(cache.cache_dir), os.W_OK)
    except Exception:
        pass

    # Check if API is configured
    api_configured = db_client.is_configured()

    status = "healthy" if cache_writable else "degraded"

    return {
        "status": status,
        "service": "device-database-client",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "cache_writable": cache_writable,
        "api_configured": api_configured,
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint"""
    return {
        "service": "device-database-client",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/v1/devices/lookup", response_model=DeviceInfoResponse)
async def lookup_device(
    manufacturer: str = Query(..., description="Device manufacturer"),
    model: str = Query(..., description="Device model"),
) -> DeviceInfoResponse:
    """Look up device info, checking cache first, then API."""
    cache: DeviceCache = app.state.cache
    db_client: DeviceDatabaseClient = app.state.db_client

    # Check cache first
    cached = cache.get(manufacturer, model)
    if cached is not None:
        return DeviceInfoResponse(
            manufacturer=manufacturer,
            model=model,
            device_info=cached,
        )

    # Query API
    device_info = await db_client.get_device_info(manufacturer, model)
    if device_info is not None:
        cache.set(manufacturer, model, device_info)
        return DeviceInfoResponse(
            manufacturer=manufacturer,
            model=model,
            device_info=device_info,
        )

    # Not found
    return DeviceInfoResponse(
        manufacturer=manufacturer,
        model=model,
        device_info={},
    )


@app.get("/api/v1/devices/search")
async def search_devices(
    device_type: str | None = Query(None, description="Device type filter"),
) -> list[dict[str, Any]]:
    """Search the device database."""
    db_client: DeviceDatabaseClient = app.state.db_client
    results = await db_client.search_devices(device_type=device_type)
    return results


@app.get("/api/v1/cache/status", response_model=CacheStatusResponse)
async def cache_status() -> CacheStatusResponse:
    """Return cache statistics."""
    cache: DeviceCache = app.state.cache

    entries_count = 0
    if cache.cache_dir.exists():
        entries_count = len(list(cache.cache_dir.glob("*.json")))

    ttl_hours = int(cache.ttl.total_seconds() / 3600)

    return CacheStatusResponse(
        cache_dir=str(cache.cache_dir),
        ttl_hours=ttl_hours,
        entries_count=entries_count,
    )


@app.post("/api/v1/sync/trigger", response_model=SyncStatusResponse)
async def trigger_sync() -> SyncStatusResponse:
    """Manually trigger a device sync."""
    sync_service: DeviceSyncService = app.state.sync_service

    await sync_service._sync_devices()

    last_sync = None
    if sync_service.last_sync is not None:
        last_sync = sync_service.last_sync.isoformat()

    return SyncStatusResponse(
        running=sync_service._running,
        last_sync=last_sync,
    )


if __name__ == "__main__":
    port = int(os.getenv("DEVICE_DATABASE_CLIENT_PORT", "8022"))
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=port,
        reload=os.getenv("RELOAD", "false").lower() == "true",
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
