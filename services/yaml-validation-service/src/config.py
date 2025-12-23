"""Configuration management for YAML Validation Service"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Service Configuration
    service_port: int = 8037
    service_name: str = "yaml-validation-service"
    
    # Data API Configuration
    data_api_url: str = "http://data-api:8006"
    
    # Home Assistant Configuration (optional, for service validation)
    ha_url: str | None = None
    ha_token: str | None = None
    
    # Validation Settings
    validation_level: str = "moderate"  # strict, moderate, permissive
    enable_normalization: bool = True
    enable_entity_validation: bool = True
    enable_service_validation: bool = False  # Requires HA client
    
    # Logging
    log_level: str = "INFO"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

