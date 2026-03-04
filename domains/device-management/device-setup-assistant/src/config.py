"""Configuration for Device Setup Assistant Service."""

from __future__ import annotations

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings for Device Setup Assistant.

    Inherits common fields (service_name, service_port, log_level,
    database_url, data_api_url, cors_origins, etc.) from BaseServiceSettings.
    """

    # Override base defaults
    service_name: str = "device-setup-assistant"
    service_port: int = 8021

    # Home Assistant configuration
    ha_url: str = ""
    ha_token: str = ""
    home_assistant_token: str = ""


settings = Settings()
