"""Configuration management for HA Setup Service"""
import os
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Service configuration
    service_name: str = "ha-setup-service"
    service_port: int = 8020  # Changed from 8010 (used by carbon-intensity)
    log_level: str = "INFO"

    # Home Assistant configuration
    ha_url: str = "http://192.168.1.86:8123"
    ha_token: str = ""
    # Also support HOME_ASSISTANT_TOKEN for compatibility
    home_assistant_token: str = ""

    # Database configuration
    database_url: str = "sqlite+aiosqlite:////app/data/ha-setup.db"  # Absolute path for Docker volume

    # Data API configuration
    data_api_url: str = "http://homeiq-data-api:8006"

    # Admin API configuration
    admin_api_url: str = "http://homeiq-admin-api:8003"

    # Health check intervals (seconds)
    health_check_interval: int = 60
    integration_check_interval: int = 300  # 5 minutes

    # Performance monitoring
    enable_performance_monitoring: bool = True
    performance_sample_interval: int = 30

    # CORS configuration
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    class Config:
        env_file = ".env"
        case_sensitive = False
        # Allow reading from environment variables with different names
        env_file_encoding = 'utf-8'

    @field_validator("ha_url", mode="after")
    @classmethod
    def normalize_ha_url(cls, value: str) -> str:
        """Ensure trailing slashes are removed from the HA URL."""
        return value.rstrip("/")

    @model_validator(mode="after")
    def ensure_ha_token(self):
        """Ensure HA token is loaded from environment if not set in config"""
        if not self.ha_token:
            # Try environment variables as fallback
            self.ha_token = (
                os.getenv("HA_TOKEN") or
                os.getenv("HOME_ASSISTANT_TOKEN") or
                self.home_assistant_token or
                ""
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

