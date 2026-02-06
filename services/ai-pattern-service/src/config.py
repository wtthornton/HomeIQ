"""Configuration management for AI Pattern Service"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Database
    database_path: str = "/app/data/ai_automation.db"
    database_url: str = "sqlite+aiosqlite:////app/data/ai_automation.db"  # Absolute path for SQLite
    database_pool_size: int = 10  # Connection pool size (max 20 per service)
    database_max_overflow: int = 5  # Max overflow connections
    
    # Data API Configuration
    data_api_url: str = "http://data-api:8006"
    
    # Pattern Detection Configuration
    time_of_day_occurrence_overrides: dict = {}
    time_of_day_confidence_overrides: dict = {}
    co_occurrence_support_overrides: dict = {}
    co_occurrence_confidence_overrides: dict = {}
    
    # Synergy Detection Configuration
    synergy_min_confidence: float = 0.5
    synergy_min_impact_score: float = 0.3
    
    # Logging
    log_level: str = "INFO"
    
    # Service Configuration
    service_port: int = 8020
    service_name: str = "ai-pattern-service"
    
    # MQTT Configuration (for scheduler - Story 39.6)
    mqtt_broker: str | None = None
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    
    # Scheduler Configuration (Story 39.6)
    analysis_schedule: str = "0 3 * * *"  # Default: 3 AM daily (cron format)
    enable_incremental: bool = True  # Enable incremental pattern updates
    
    # Internal API authentication
    internal_api_token: str = "change-me-in-production"

    # Home Assistant Configuration (for automation generation)
    ha_url: str = "http://homeassistant:8123"  # Home Assistant URL
    ha_token: str | None = None  # Home Assistant long-lived access token
    ha_version: str = "2025.1"  # Home Assistant version
    
    # Blueprint Index Service Configuration (Phase 2 - Blueprint-First Architecture)
    blueprint_index_url: str | None = "http://blueprint-index:8031"
    
    # Device Intelligence Service Configuration (Phase 1.3 - Capability Integration)
    device_intelligence_url: str = "http://device-intelligence-service:8028"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

