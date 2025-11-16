"""Configuration management for HA Setup Service"""
from typing import Optional
from pydantic import field_validator
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
    
    # MQTT broker configuration (for Zigbee2MQTT monitoring)
    mqtt_broker_url: str = "mqtt://core-mosquitto:1883"  # Default HA Mosquitto broker
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    zigbee2mqtt_base_topic: str = "zigbee2mqtt"  # Zigbee2MQTT base topic
    
    # Health check intervals (seconds)
    health_check_interval: int = 60
    integration_check_interval: int = 300  # 5 minutes
    
    # Performance monitoring
    enable_performance_monitoring: bool = True
    performance_sample_interval: int = 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    @field_validator("ha_url", mode="after")
    @classmethod
    def normalize_ha_url(cls, value: str) -> str:
        """Ensure trailing slashes are removed from the HA URL."""
        return value.rstrip("/")


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

