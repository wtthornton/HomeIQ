"""DataAPIService — configuration, auth, InfluxDB client, and metrics.

Extracted from main.py for maintainability index compliance.
"""

from __future__ import annotations

import os
import secrets
from datetime import datetime

from homeiq_data.auth import AuthManager
from homeiq_data.influxdb_query_client import InfluxDBQueryClient
from homeiq_data.rate_limiter import RateLimiter
from homeiq_observability.logging_config import setup_logging
from homeiq_observability.monitoring import alerting_service, metrics_service

from .ha_automation_endpoints import start_webhook_detector, stop_webhook_detector
from .sports_influxdb_writer import get_sports_writer

logger = setup_logging("data-api")


class DataAPIService:
    """Configuration, auth, InfluxDB client, and runtime metrics."""

    def __init__(self) -> None:
        """Read configuration from environment and initialise components."""
        self.api_host = os.getenv("DATA_API_HOST", "0.0.0.0")  # noqa: S104  # nosec B104
        self.api_port = int(os.getenv("DATA_API_PORT", "8006"))
        self.request_timeout = int(os.getenv("REQUEST_TIMEOUT", "30"))
        self.db_query_timeout = int(os.getenv("DB_QUERY_TIMEOUT", "10"))
        self.api_title = "Data API - Feature Data Hub"
        self.api_version = "1.0.0"
        self.api_description = "Feature data access (events, devices, sports, analytics)"

        # Authentication
        self.api_key = (
            os.getenv("DATA_API_API_KEY") or os.getenv("DATA_API_KEY") or os.getenv("API_KEY")
        )
        self.allow_anonymous = os.getenv("DATA_API_ALLOW_ANONYMOUS", "false").lower() == "true"
        if not self.api_key:
            if not self.allow_anonymous:
                raise RuntimeError("DATA_API_API_KEY must be set")
            self.api_key = secrets.token_urlsafe(48)

        self.cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
        self.rate_limiter = RateLimiter(
            rate=int(os.getenv("DATA_API_RATE_LIMIT_PER_MIN", "100")),
            per=60,
            burst=int(os.getenv("DATA_API_RATE_LIMIT_BURST", "20")),
        )
        self.auth_manager = AuthManager(api_key=self.api_key, allow_anonymous=self.allow_anonymous)
        self.influxdb_client = InfluxDBQueryClient()

        # Runtime state
        self.start_time = datetime.now()
        self.is_running = False
        self.total_requests = 0
        self.failed_requests = 0

    async def startup(self) -> None:
        """Start monitoring, connect InfluxDB, start webhook detector."""
        await alerting_service.start()
        await metrics_service.start()
        try:
            from .metrics_state import metrics_buffer

            self.influxdb_client.query_latency_callback = metrics_buffer.record_db_query
            if await self.influxdb_client.connect():
                sw = get_sports_writer()
                await sw.connect()
                start_webhook_detector()
        except Exception as e:
            logger.error("InfluxDB startup error: %s", e)
        self.is_running = True

    async def shutdown(self) -> None:
        """Stop monitoring and close connections."""
        stop_webhook_detector()
        await alerting_service.stop()
        await metrics_service.stop()
        try:
            await self.influxdb_client.close()
        except Exception as e:
            logger.error("InfluxDB close error: %s", e)
        self.is_running = False
