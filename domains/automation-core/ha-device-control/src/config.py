"""Service configuration for ha-device-control.

Loads settings from environment variables using BaseServiceSettings.
"""

from __future__ import annotations

from homeiq_data import BaseServiceSettings
from pydantic import Field, SecretStr


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8040
    service_name: str = "ha-device-control"

    # Home Assistant connection
    ha_url: str = Field(default="http://homeassistant:8123", description="HA REST API base URL")
    ha_token: SecretStr = Field(default=SecretStr(""), description="HA long-lived access token")
    ha_timeout: int = Field(default=15, description="HA REST API timeout in seconds")

    # Entity cache
    entity_cache_ttl_seconds: int = Field(default=1800, description="Entity cache TTL (30 min)")

    # Notification
    default_notify_service: str = Field(
        default="",
        description="Default HA notify service name (e.g. mobile_app_phone)",
    )

    # Blacklist (comma-separated patterns for initial config)
    blacklist_patterns: str = Field(
        default="",
        description="Comma-separated entity blacklist patterns (glob, exact, area:Name)",
    )


settings = Settings()
