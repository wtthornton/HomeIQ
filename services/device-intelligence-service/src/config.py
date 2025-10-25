"""
Device Intelligence Service - Configuration Management

Pydantic Settings for environment variable management and validation.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    DEVICE_INTELLIGENCE_PORT: int = Field(default=8019, description="Service port")
    DEVICE_INTELLIGENCE_HOST: str = Field(default="0.0.0.0", description="Service host")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Database Configuration
    SQLITE_DATABASE_URL: str = Field(
        default="sqlite:///./data/device_intelligence.db",
        description="SQLite database URL"
    )
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis cache URL"
    )
    
    # Home Assistant Configuration
    HA_URL: str = Field(
        default="http://homeassistant:8123",
        description="Home Assistant URL (primary)"
    )
    HA_WS_URL: Optional[str] = Field(
        default=None,
        description="Home Assistant WebSocket URL (primary)"
    )
    HA_TOKEN: Optional[str] = Field(
        default=None,
        description="Home Assistant long-lived access token (primary)"
    )
    
    # Nabu Casa Fallback Configuration
    NABU_CASA_URL: Optional[str] = Field(
        default=None,
        description="Nabu Casa URL for remote access fallback"
    )
    NABU_CASA_TOKEN: Optional[str] = Field(
        default=None,
        description="Nabu Casa long-lived access token for fallback"
    )
    
    # Local HA Fallback Configuration (Optional)
    LOCAL_HA_URL: Optional[str] = Field(
        default=None,
        description="Local Home Assistant URL for additional fallback"
    )
    LOCAL_HA_TOKEN: Optional[str] = Field(
        default=None,
        description="Local Home Assistant token for additional fallback"
    )
    
    # MQTT Configuration
    MQTT_BROKER: str = Field(
        default="mqtt://mosquitto:1883",
        description="MQTT broker URL"
    )
    MQTT_USERNAME: Optional[str] = Field(
        default=None,
        description="MQTT username"
    )
    MQTT_PASSWORD: Optional[str] = Field(
        default=None,
        description="MQTT password"
    )
    
    # Zigbee2MQTT Configuration
    ZIGBEE2MQTT_BASE_TOPIC: str = Field(
        default="zigbee2mqtt",
        description="Zigbee2MQTT base topic"
    )
    
    # Performance Configuration
    MAX_WORKERS: int = Field(
        default=4,
        description="Maximum number of worker processes"
    )
    REQUEST_TIMEOUT: int = Field(
        default=30,
        description="Request timeout in seconds"
    )
    
    # Cache Configuration
    CACHE_TTL: int = Field(
        default=300,
        description="Default cache TTL in seconds"
    )
    MAX_CACHE_SIZE: int = Field(
        default=1000,
        description="Maximum cache size"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True
    }
        
    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v):
        """Validate log level is a valid logging level."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of {valid_levels}")
        return v.upper()
    
    @field_validator("DEVICE_INTELLIGENCE_PORT")
    @classmethod
    def validate_port(cls, v):
        """Validate port is in valid range."""
        if not 1 <= v <= 65535:
            raise ValueError("DEVICE_INTELLIGENCE_PORT must be between 1 and 65535")
        return v
    
    @field_validator("HA_URL")
    @classmethod
    def validate_ha_url(cls, v):
        """Validate Home Assistant URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("HA_URL must start with http:// or https://")
        return v
    
    @field_validator("MQTT_BROKER")
    @classmethod
    def validate_mqtt_broker(cls, v):
        """Validate MQTT broker URL format."""
        if not v.startswith(("mqtt://", "mqtts://", "ws://", "wss://")):
            raise ValueError("MQTT_BROKER must start with mqtt://, mqtts://, ws://, or wss://")
        return v
    
    def get_database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return self.SQLITE_DATABASE_URL
    
    def get_redis_url(self) -> str:
        """Get the Redis URL for caching."""
        return self.REDIS_URL
    
    def get_ha_url(self) -> str:
        """Get the effective Home Assistant URL with Nabu Casa fallback."""
        # Try local HA first, fallback to Nabu Casa if local HA fails
        return self.HA_URL
    
    def get_ha_ws_url(self) -> str:
        """Get the WebSocket URL for Home Assistant."""
        # Use HA_WS_URL if available, otherwise construct from HA_URL
        if hasattr(self, 'HA_WS_URL') and self.HA_WS_URL:
            return self.HA_WS_URL
        return self.HA_URL.replace('http://', 'ws://').replace('https://', 'wss://') + '/api/websocket'
    
    def get_nabu_casa_ws_url(self) -> str:
        """Get the WebSocket URL for Nabu Casa."""
        if self.NABU_CASA_URL:
            return self.NABU_CASA_URL.replace('https://', 'wss://') + '/api/websocket'
        return None
    
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "development"
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return os.getenv("ENVIRONMENT", "development").lower() == "production"


# Global settings instance
settings = Settings()
