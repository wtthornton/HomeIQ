"""Configuration management for AI Automation Service"""

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
    
    # Home Assistant Configuration
    ha_url: str | None = None
    ha_token: str | None = None
    
    # OpenAI Configuration
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_timeout: float = 30.0  # Timeout for OpenAI API calls (seconds)
    
    # Device Intelligence Service
    device_intelligence_url: str = "http://device-intelligence-service:8023"
    
    # Query Service (for entity extraction)
    query_service_url: str = "http://ai-query-service:8018"
    
    # Pattern Service (for pattern data)
    pattern_service_url: str = "http://ai-pattern-service:8020"
    
    # Automation Service Settings
    enable_safety_validation: bool = True
    safety_level: str = "moderate"  # conservative, moderate, permissive
    enable_rollback: bool = True
    max_automation_versions: int = 10  # Keep last 10 versions for rollback
    
    # YAML Generation Settings
    yaml_generation_timeout: float = 30.0
    enable_yaml_validation: bool = True
    enable_yaml_correction: bool = True
    
    # Suggestion Generation Settings
    max_suggestions_per_request: int = 50
    suggestion_cache_ttl: int = 3600  # 1 hour cache
    
    # Logging
    log_level: str = "INFO"
    
    # Service Configuration
    service_port: int = 8025  # Using 8025 since 8021 is taken by device-setup-assistant
    service_name: str = "ai-automation-service"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

