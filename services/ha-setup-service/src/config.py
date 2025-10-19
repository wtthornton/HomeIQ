"""Configuration management for HA Setup Service"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Service configuration
    service_name: str = "ha-setup-service"
    service_port: int = 8020  # Changed from 8010 (used by carbon-intensity)
    log_level: str = "INFO"
    
    # Home Assistant configuration
    ha_url: str = "http://192.168.1.86:8123"
    ha_token: str = ""
    
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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

