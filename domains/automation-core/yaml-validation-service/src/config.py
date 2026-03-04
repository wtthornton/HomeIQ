"""Configuration management for YAML Validation Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8037
    service_name: str = "yaml-validation-service"

    # Fallback API key (shared API_KEY from .env)
    api_key: str | None = None

    # Home Assistant Configuration (optional, for service validation)
    ha_url: str | None = None
    ha_token: str | None = None

    # Validation Settings
    validation_level: str = "moderate"  # strict, moderate, permissive
    enable_normalization: bool = True
    enable_entity_validation: bool = True
    enable_service_validation: bool = False  # Requires HA client


settings = Settings()
