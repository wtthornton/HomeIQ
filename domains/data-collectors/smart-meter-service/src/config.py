"""Configuration for Smart Meter Service.

Uses BaseServiceSettings from homeiq-data for common fields.
"""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Smart Meter Service settings loaded from environment variables."""

    service_name: str = "smart-meter-service"
    service_port: int = 8014

    # Meter configuration
    meter_type: str = Field(default="home_assistant", description="Meter adapter type")
    meter_api_token: str = Field(default="", description="Meter API authentication token")
    meter_device_id: str = Field(default="", description="Meter device identifier")

    # Home Assistant configuration
    home_assistant_url: str | None = Field(default=None, description="Home Assistant URL")
    home_assistant_token: str | None = Field(default=None, description="Home Assistant token")

    # Service configuration
    fetch_interval_seconds: int = Field(default=300, description="Data fetch interval in seconds")


settings = Settings()
