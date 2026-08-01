"""Configuration management for HA Setup Service."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from pydantic import field_validator, model_validator

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings with environment variable support.

    Inherits common fields (service_name, service_port, log_level,
    database_url, data_api_url, cors_origins, etc.) from BaseServiceSettings.
    """

    # Override base defaults
    service_name: str = "ha-setup-service"
    service_port: int = 8020

    # Home Assistant configuration (no default: must be configured explicitly)
    ha_url: str = ""
    ha_token: str = ""
    home_assistant_token: str = ""

    # Admin API configuration
    admin_api_url: str = "http://homeiq-admin-api:8004"

    # Health check intervals (seconds)
    health_check_interval: int = 60
    integration_check_interval: int = 300  # 5 minutes

    # Performance monitoring
    enable_performance_monitoring: bool = True
    performance_sample_interval: int = 30

    @field_validator("ha_url", mode="after")
    @classmethod
    def normalize_ha_url(cls, value: str) -> str:
        """Ensure trailing slashes are removed from the HA URL."""
        return value.rstrip("/")

    @model_validator(mode="after")
    def ensure_ha_token(self) -> Settings:
        """Ensure HA token is loaded from environment if not set in config."""
        if not self.ha_token:
            self.ha_token = (
                os.getenv("HA_TOKEN")
                or os.getenv("HOME_ASSISTANT_TOKEN")
                or self.home_assistant_token
                or ""
            )
        return self

    @model_validator(mode="after")
    def ensure_ha_url(self) -> Settings:
        """Fall back to alternate env vars; log loudly when HA URL is unconfigured."""
        if not self.ha_url:
            self.ha_url = (
                os.getenv("HA_HTTP_URL")
                or os.getenv("HOME_ASSISTANT_URL")
                or ""
            ).rstrip("/")
        if not self.ha_url:
            logging.getLogger(__name__).error(
                "HA URL is not configured — set HA_URL, HA_HTTP_URL, or "
                "HOME_ASSISTANT_URL. Home Assistant requests will fail until it is set."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
