"""Health check handler for automation-trace-service."""

from datetime import datetime, timezone
from typing import Any

from . import __version__


class HealthCheckHandler:
    """Build health status from service component states."""

    def __init__(self):
        self.start_time = datetime.now(timezone.utc)

    def build(
        self,
        ha_connected: bool,
        influxdb_ok: bool,
        poller_stats: dict[str, Any],
        dedup_stats: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        uptime = (now - self.start_time).total_seconds()

        components = {
            "ha_websocket": "connected" if ha_connected else "disconnected",
            "influxdb": "ok" if influxdb_ok else "unavailable",
            "trace_poller": "running" if poller_stats.get("poll_count", 0) > 0 or uptime < 300 else "idle",
        }

        all_ok = ha_connected and influxdb_ok
        status = "healthy" if all_ok else "degraded"

        return {
            "status": status,
            "service": "automation-trace-service",
            "version": __version__,
            "uptime_seconds": round(uptime, 1),
            "components": components,
            "metrics": {
                **poller_stats,
                **dedup_stats,
            },
            "timestamp": now.isoformat(),
        }
