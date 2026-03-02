"""
Device Database Client Service
Phase 3.1: Client for external Device Database API

Queries external Device Database API (when available), caches device information locally,
and falls back to local intelligence if Device Database unavailable.
"""

import contextlib
import logging
import os
from typing import Any

import uvicorn
from fastapi import Query
from pydantic import BaseModel

from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app
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


# --- Shared state ---

_db_client: DeviceDatabaseClient | None = None
_cache: DeviceCache | None = None
_sync_service: DeviceSyncService | None = None


# --- Lifespan ---

async def _startup() -> None:
    global _db_client, _cache, _sync_service
    _db_client = DeviceDatabaseClient()
    cache_dir = os.getenv("DEVICE_CACHE_DIR", "data/device_cache")
    _cache = DeviceCache(cache_dir=cache_dir)
    _sync_service = DeviceSyncService(db_client=_db_client, cache=_cache)
    await _sync_service.start()
    logger.info("Device Database Client components initialized")


async def _shutdown() -> None:
    if _sync_service:
        await _sync_service.stop()
    if _db_client:
        await _db_client.close()
    logger.info("Device Database Client shut down")


lifespan = ServiceLifespan("Device Database Client Service")
lifespan.on_startup(_startup, name="init-components")
lifespan.on_shutdown(_shutdown, name="cleanup")


# --- Health check ---

async def _check_cache() -> bool:
    if _cache is None:
        return False
    try:
        return os.access(str(_cache.cache_dir), os.W_OK)
    except OSError:
        return False


health = StandardHealthCheck(service_name="device-database-client", version="1.0.0")
health.register_check("cache", _check_cache)


# --- App ---

app = create_app(
    title="Device Database Client Service",
    version="1.0.0",
    description="Client for external Device Database API with local caching",
    lifespan=lifespan.handler,
    health_check=health,
)


# --- Endpoints ---

@app.get("/api/v1/devices/lookup", response_model=DeviceInfoResponse)
async def lookup_device(
    manufacturer: str = Query(..., description="Device manufacturer"),
    model: str = Query(..., description="Device model"),
) -> DeviceInfoResponse:
    """Look up device info, checking cache first, then API."""
    # Check cache first
    cached = _cache.get(manufacturer, model)
    if cached is not None:
        return DeviceInfoResponse(
            manufacturer=manufacturer,
            model=model,
            device_info=cached,
        )

    # Query API
    device_info = await _db_client.get_device_info(manufacturer, model)
    if device_info is not None:
        _cache.set(manufacturer, model, device_info)
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
    return await _db_client.search_devices(device_type=device_type)


@app.get("/api/v1/cache/status", response_model=CacheStatusResponse)
async def cache_status() -> CacheStatusResponse:
    """Return cache statistics."""
    entries_count = 0
    if _cache.cache_dir.exists():
        entries_count = len(list(_cache.cache_dir.glob("*.json")))

    ttl_hours = int(_cache.ttl.total_seconds() / 3600)

    return CacheStatusResponse(
        cache_dir=str(_cache.cache_dir),
        ttl_hours=ttl_hours,
        entries_count=entries_count,
    )


@app.post("/api/v1/sync/trigger", response_model=SyncStatusResponse)
async def trigger_sync() -> SyncStatusResponse:
    """Manually trigger a device sync."""
    await _sync_service._sync_devices()

    last_sync = None
    if _sync_service.last_sync is not None:
        last_sync = _sync_service.last_sync.isoformat()

    return SyncStatusResponse(
        running=_sync_service._running,
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
