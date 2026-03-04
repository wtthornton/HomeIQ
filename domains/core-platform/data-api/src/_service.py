"""DataAPIService — auth, InfluxDB client, rate limiter, and metrics.

Extracted from main.py for maintainability index compliance.
Configuration is loaded from ``config.Settings`` (BaseServiceSettings).
"""

from __future__ import annotations

from datetime import datetime

from homeiq_data.auth import AuthManager
from homeiq_data.influxdb_query_client import InfluxDBQueryClient
from homeiq_data.rate_limiter import RateLimiter
from homeiq_observability.logging_config import setup_logging
from homeiq_observability.monitoring import alerting_service, metrics_service

from .config import settings
from .ha_automation_endpoints import start_webhook_detector, stop_webhook_detector
from .sports_influxdb_writer import get_sports_writer

logger = setup_logging("data-api")


class DataAPIService:
    """Auth, InfluxDB client, rate limiter, and runtime metrics."""

    def __init__(self) -> None:
        """Initialize from shared settings and create components."""
        # Config proxies for backward compatibility
        self.api_host = "0.0.0.0"  # noqa: S104  # nosec B104
        self.api_port = settings.service_port
        self.request_timeout = settings.request_timeout
        self.db_query_timeout = settings.db_query_timeout
        self.api_title = settings.api_title
        self.api_version = settings.api_version
        self.api_description = settings.api_description
        self.allow_anonymous = settings.allow_anonymous
        self.cors_origins = settings.get_cors_origins_list()

        # Components
        self.rate_limiter = RateLimiter(
            rate=settings.rate_limit_per_min,
            per=60,
            burst=settings.rate_limit_burst,
        )
        self.auth_manager = AuthManager(
            api_key=settings.api_key,
            allow_anonymous=settings.allow_anonymous,
        )
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
