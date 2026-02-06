"""
Configuration for Calendar Service

Uses Pydantic Settings for environment variable management.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Calendar configuration
    calendar_entities: str = "calendar.primary"
    
    # InfluxDB configuration
    influxdb_url: str = "http://influxdb:8086"
    influxdb_token: str  # Required
    influxdb_org: str = "home_assistant"
    influxdb_bucket: str = "events"
    
    # Service configuration
    calendar_fetch_interval: int = 900  # 15 minutes default
    service_port: int = 8013
    timezone: str = "UTC"
    default_travel_time_minutes: int = 30
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

