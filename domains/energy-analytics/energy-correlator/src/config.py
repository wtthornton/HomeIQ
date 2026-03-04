"""Configuration settings for Energy Correlator Service."""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8017
    service_name: str = "energy-correlator"
    influxdb_bucket: str = "home_assistant_events"

    # Processing configuration
    processing_interval: int = Field(default=60, ge=1, description="Seconds between correlation runs")
    lookback_minutes: int = Field(default=5, ge=1, description="Minutes of events to look back")
    max_events_per_interval: int = Field(default=500, ge=1)
    max_retry_queue_size: int = Field(default=250, ge=1)
    retry_window_minutes: int = 0  # 0 means use lookback_minutes
    correlation_window_seconds: int = 10
    power_lookup_padding_seconds: int = 30
    min_power_delta: float = 10.0
    error_retry_interval: int = 60

    # Network validation
    allowed_networks: str = ""


settings = Settings()
