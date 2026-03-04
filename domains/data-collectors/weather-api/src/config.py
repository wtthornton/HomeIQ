"""Configuration settings for Weather API Service."""

from typing import Literal

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8009
    service_name: str = "weather-api"
    influxdb_bucket: str = "weather_data"

    # OpenWeatherMap configuration
    weather_api_key: str | None = None
    weather_location: str = "Las Vegas"
    weather_api_auth_mode: Literal["header", "query"] = "header"

    # Cache
    cache_ttl_seconds: int = 900

    # InfluxDB write retries
    influxdb_write_retries: int = 3

    # InfluxDB fallback hostnames for DNS resilience
    influxdb_fallback_hosts: str = "influxdb,homeiq-influxdb,localhost"


settings = Settings()
