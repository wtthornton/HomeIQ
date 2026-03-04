"""Configuration for Air Quality Service.

Uses BaseServiceSettings from homeiq-data for common fields.
"""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Air Quality Service settings loaded from environment variables."""

    service_name: str = "air-quality-service"
    service_port: int = 8012

    # OpenWeather API configuration
    weather_api_key: str = Field(description="OpenWeather API key")

    # Location configuration
    latitude: str = Field(default="36.1699", description="Latitude for AQI monitoring")
    longitude: str = Field(default="-115.1398", description="Longitude for AQI monitoring")

    # Home Assistant configuration (for automatic location detection)
    home_assistant_url: str | None = Field(default=None, description="Home Assistant URL")
    home_assistant_token: str | None = Field(default=None, description="Home Assistant token")
    ha_http_url: str | None = Field(default=None, description="Fallback HA URL")
    ha_token: str | None = Field(default=None, description="Fallback HA token")

    # Service configuration
    fetch_interval: int = Field(default=3600, description="Fetch interval in seconds")
    cache_duration: int = Field(default=60, description="Cache duration in minutes")


settings = Settings()
