"""Log Aggregation Service — FastAPI entry point.

Exposes REST endpoints for querying, searching, and collecting logs from Docker
containers. Background periodic collection runs via ServiceLifespan.

Converted from aiohttp to FastAPI with homeiq-resilience shared library pattern.
"""

import asyncio
import contextlib
import time
from datetime import UTC, datetime
from typing import Any

import uvicorn
from aggregator import LogAggregator
from config import settings
from fastapi import HTTPException, Query, Request
from homeiq_observability.logging_config import setup_logging
from homeiq_resilience import ServiceLifespan, StandardHealthCheck, create_app

logger = setup_logging("log-aggregator")


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _count_recent_logs(logs: list[dict], hours: int = 1) -> int:
    """Count log entries from the last N hours based on their timestamp."""
    cutoff = datetime.now(UTC).timestamp() - (hours * 3600)
    count = 0
    for log in logs:
        try:
            timestamp_str = log.get('timestamp', '1970-01-01T00:00:00Z').replace('Z', '+00:00')
            log_time = datetime.fromisoformat(timestamp_str).timestamp()
            if log_time > cutoff:
                count += 1
        except (ValueError, AttributeError):
            continue
    return count


def _count_by_field(logs: list[dict], field: str) -> dict[str, int]:
    """Count log entries grouped by a specific field value."""
    counts: dict[str, int] = {}
    for log in logs:
        value = str(log.get(field, 'unknown'))
        counts[value] = counts.get(value, 0) + 1
    return counts


# ---------------------------------------------------------------------------
# Shared state
# ---------------------------------------------------------------------------

_aggregator: LogAggregator | None = None
_bg_task: asyncio.Task | None = None


# ---------------------------------------------------------------------------
# Background collection
# ---------------------------------------------------------------------------


async def _background_log_collection() -> None:
    """Background task that periodically collects logs from Docker containers."""
    interval = _aggregator.collection_interval if _aggregator else 30
    while True:
        try:
            if _aggregator:
                await _aggregator.collect_logs()
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            logger.info("Background log collection cancelled")
            return
        except Exception as e:
            logger.error("Error in background log collection: %s", e)
            await asyncio.sleep(interval * 2)


# ---------------------------------------------------------------------------
# Lifespan hooks
# ---------------------------------------------------------------------------


async def _startup() -> None:
    global _aggregator, _bg_task
    _aggregator = LogAggregator()
    _bg_task = asyncio.create_task(_background_log_collection())
    logger.info("Log Aggregator started with background collection")


async def _shutdown() -> None:
    global _bg_task
    if _bg_task:
        _bg_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _bg_task
    logger.info("Log Aggregator shut down")


lifespan = ServiceLifespan("log-aggregator")
lifespan.on_startup(_startup, name="log-aggregator-init")
lifespan.on_shutdown(_shutdown, name="log-aggregator-cleanup")


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------


async def _check_docker() -> bool:
    if _aggregator is None:
        return False
    return _aggregator.docker_client is not None


health = StandardHealthCheck(service_name="log-aggregator", version="1.0.0")
health.register_check("docker", _check_docker)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = create_app(
    title="Log Aggregator Service",
    version="1.0.0",
    description="Centralized log collection from Docker containers",
    lifespan=lifespan.handler,
    health_check=health,
    cors_origins=settings.get_cors_origins_list(),
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


def _validate_limit(limit: int) -> None:
    """Validate limit parameter range."""
    if limit < 1 or limit > 10000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 10000")


@app.get("/api/v1/logs")
async def get_logs(
    service: str | None = Query(default=None),
    level: str | None = Query(default=None),
    limit: int = Query(default=100),
) -> dict[str, Any]:
    """Get recent logs with optional service/level/limit filters."""
    _validate_limit(limit)
    logs = await _aggregator.get_recent_logs(service, level, limit)
    return {
        "logs": logs,
        "count": len(logs),
        "filters": {"service": service, "level": level, "limit": limit},
    }


@app.get("/api/v1/logs/search")
async def search_logs(
    q: str = Query(default=""),
    limit: int = Query(default=100),
) -> dict[str, Any]:
    """Search logs by query string parameter 'q'."""
    _validate_limit(limit)
    if not q:
        raise HTTPException(status_code=400, detail="Query parameter 'q' is required")
    logs = await _aggregator.search_logs(q, limit)
    return {"logs": logs, "count": len(logs), "query": q, "limit": limit}


@app.post("/api/v1/logs/collect")
async def collect_logs_endpoint(request: Request) -> dict[str, Any]:
    """Manually trigger log collection with rate limiting."""
    if _aggregator._api_key:
        provided_key = request.headers.get('X-API-Key', '')
        if provided_key != _aggregator._api_key:
            raise HTTPException(status_code=403, detail="Invalid or missing API key")

    now = time.monotonic()
    elapsed = now - _aggregator._last_manual_collect
    if elapsed < 10.0:
        raise HTTPException(
            status_code=429,
            detail="Rate limited. Try again in %.1fs" % (10.0 - elapsed),
        )

    _aggregator._last_manual_collect = now
    logs = await _aggregator.collect_logs()

    return {
        "message": f"Collected {len(logs)} log entries",
        "logs_collected": len(logs),
        "total_logs": len(_aggregator.aggregated_logs),
    }


@app.get("/api/v1/logs/stats")
async def get_log_stats() -> dict[str, Any]:
    """Return log statistics: totals, by-service, by-level, and recent counts."""
    logs = _aggregator.aggregated_logs
    return {
        "total_logs": len(logs),
        "services": _count_by_field(logs, 'service'),
        "levels": _count_by_field(logs, 'level'),
        "recent_logs": _count_recent_logs(logs, hours=1),
    }


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",  # noqa: S104
        port=settings.service_port,
        log_level=settings.log_level.lower(),
    )
