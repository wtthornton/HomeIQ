"""Configuration settings for WebSocket Ingestion Service.

Inherits common fields from BaseServiceSettings and adds
websocket-ingestion-specific settings for HA connection, processing,
and InfluxDB overflow configuration.
"""

from __future__ import annotations

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """WebSocket Ingestion settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8001
    service_name: str = "websocket-ingestion"
    influxdb_bucket: str = "home_assistant_events"
    influxdb_org: str = "homeiq"

    # Home Assistant connection (supports old + new variable names)
    ha_http_url: str | None = Field(default=None)
    home_assistant_url: str | None = Field(default=None)
    ha_ws_url: str | None = Field(default=None)
    ha_url: str | None = Field(default=None)
    ha_token: str | None = Field(default=None)
    home_assistant_token: str | None = Field(default=None)

    # Nabu Casa fallback
    nabu_casa_url: str | None = Field(default=None)
    nabu_casa_token: str | None = Field(default=None)

    enable_home_assistant: bool = Field(default=True)

    # High-volume processing
    max_workers: int = Field(default=10)
    processing_rate_limit: int = Field(default=1000)
    batch_size: int = Field(default=100)
    batch_timeout: float = Field(default=5.0)
    max_memory_mb: int = Field(default=1024)

    # InfluxDB overflow
    influxdb_max_pending_points: int = Field(default=20000)
    influxdb_overflow_strategy: str = Field(default="drop_oldest")

    @property
    def resolved_ha_http_url(self) -> str | None:
        """Return the best available HA HTTP URL."""
        return self.ha_http_url or self.home_assistant_url

    @property
    def resolved_ha_ws_url(self) -> str | None:
        """Return the best available HA WebSocket URL."""
        return self.ha_ws_url or self.ha_url

    @property
    def resolved_ha_token(self) -> str | None:
        """Return the best available HA token."""
        return self.ha_token or self.home_assistant_token


settings = Settings()
