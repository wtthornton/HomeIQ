"""Configuration for Calendar Service.

Uses BaseServiceSettings from homeiq-data for standardized settings management.
"""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Calendar configuration
    calendar_entities: str = "calendar.primary"
    calendar_fetch_interval: int = 900  # 15 minutes default
    timezone: str = "UTC"
    default_travel_time_minutes: int = 30

    # Override base defaults
    service_port: int = 8013
    service_name: str = "calendar-service"
    influxdb_bucket: str = "events"


settings = Settings()
