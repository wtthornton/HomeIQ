"""Configuration settings for Sports API Service."""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8005
    service_name: str = "sports-api"
    influxdb_bucket: str = "home_assistant_events"

    # Home Assistant configuration
    ha_http_url: str = ""
    home_assistant_url: str = "http://192.168.1.86:8123"
    ha_token: str | None = Field(default=None, alias="HA_TOKEN")
    home_assistant_token: str | None = None

    # Polling
    sports_poll_interval: int = 60

    # API key for endpoint protection
    sports_api_key: str = ""

    # InfluxDB write retries
    influxdb_write_retries: int = 3

    # InfluxDB fallback hostnames for DNS resilience
    influxdb_fallback_hosts: str = "influxdb,homeiq-influxdb,localhost"

    @property
    def effective_ha_url(self) -> str:
        """Return the best available HA URL."""
        return (self.ha_http_url or self.home_assistant_url).rstrip("/")

    @property
    def effective_ha_token(self) -> str | None:
        """Return the best available HA token."""
        return self.ha_token or self.home_assistant_token


settings = Settings()
