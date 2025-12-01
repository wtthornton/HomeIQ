"""
Device Intelligence Service - Configuration Management

Pydantic Settings for environment variable management and validation.
"""

import json
import os
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings

CONFIG_FILE_ENV = "MQTT_ZIGBEE_CONFIG_PATH"


def _determine_default_path() -> Path:
    env_override = os.getenv(CONFIG_FILE_ENV)
    if env_override:
        return Path(env_override)

    module_path = Path(__file__).resolve()
    candidates = [
        Path("/app/infrastructure/config/mqtt_zigbee_config.json"),
        module_path.parents[2] / "infrastructure" / "config" / "mqtt_zigbee_config.json",
        module_path.parents[1] / "config" / "mqtt_zigbee_config.json",
    ]

    for candidate in candidates:
        try:
            if candidate.parent.exists():
                return candidate
        except IndexError:
            continue

    return candidates[-1]


DEFAULT_CONFIG_PATH = _determine_default_path()


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
    HA_WS_URL: str | None = Field(
        default=None,
        description="Home Assistant WebSocket URL (primary)"
    )
    HA_TOKEN: str | None = Field(
        default=None,
        description="Home Assistant long-lived access token (primary)"
    )

    # Nabu Casa Fallback Configuration
    NABU_CASA_URL: str | None = Field(
        default=None,
        description="Nabu Casa URL for remote access fallback"
    )
    NABU_CASA_TOKEN: str | None = Field(
        default=None,
        description="Nabu Casa long-lived access token for fallback"
    )

    # MQTT Configuration
    # Defaults to Home Assistant's MQTT broker (same server as HA HTTP API)
    MQTT_BROKER: str = Field(
        default="mqtt://192.168.1.86:1883",
        description="MQTT broker URL (defaults to HA's MQTT broker)"
    )
    MQTT_USERNAME: str | None = Field(
        default=None,
        description="MQTT username"
    )
    MQTT_PASSWORD: str | None = Field(
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

    # Name Enhancement Configuration
    AUTO_GENERATE_NAME_SUGGESTIONS: bool = Field(
        default=False,
        description="Automatically generate name suggestions during device discovery"
    )
    OPENAI_API_KEY: str | None = Field(
        default=None,
        description="OpenAI API key for AI name generation (optional)"
    )
    ENABLE_LOCAL_LLM: bool = Field(
        default=False,
        description="Enable local LLM (Ollama) for name generation (optional)"
    )

    # HTTP Configuration
    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins"
    )

    # ML Model Configuration (2025 improvements)
    ML_FAILURE_MODEL: str = Field(
        default="randomforest",
        description="Failure prediction model: randomforest, lightgbm, or tabpfn"
    )
    ML_USE_INCREMENTAL: bool = Field(
        default=False,
        description="Use incremental learning for model updates"
    )
    ML_INCREMENTAL_UPDATE_THRESHOLD: int = Field(
        default=100,
        description="Number of samples before incremental update"
    )
    GNN_USE_COMPILE: bool = Field(
        default=True,
        description="Use PyTorch compile for GNN training (1.5-2x speedup)"
    )

    # Training Scheduler Configuration (Epic 46.2: Built-in Nightly Training Scheduler)
    ML_TRAINING_SCHEDULE: str = Field(
        default="0 2 * * *",
        description="Cron expression for training schedule (default: 2 AM daily)"
    )
    ML_TRAINING_ENABLED: bool = Field(
        default=True,
        description="Enable automatic nightly training"
    )
    ML_TRAINING_MODE: str = Field(
        default="incremental",
        description="Training mode: 'full' or 'incremental' (default: incremental for 10-50x faster updates)"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
        "extra": "ignore",
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

    @field_validator("HA_URL", mode="after")
    @classmethod
    def validate_ha_url(cls, v):
        """Validate Home Assistant URL format."""
        if not v.startswith(("http://", "https://")):
            raise ValueError("HA_URL must start with http:// or https://")
        return v.rstrip("/")

    @field_validator("MQTT_BROKER")
    @classmethod
    def validate_mqtt_broker(cls, v):
        """Validate MQTT broker URL format."""
        if not v.startswith(("mqtt://", "mqtts://", "ws://", "wss://")):
            raise ValueError("MQTT_BROKER must start with mqtt://, mqtts://, ws://, or wss://")
        return v

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def normalize_allowed_origins(cls, value):
        """Support comma-delimited strings for allowed origins."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid ALLOWED_ORIGINS JSON: {exc}") from exc
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    def apply_overrides(self) -> None:
        """Apply runtime overrides from the shared MQTT/Zigbee configuration file."""
        config_path = DEFAULT_CONFIG_PATH
        overrides = {}

        try:
            if config_path.exists():
                with config_path.open("r", encoding="utf-8") as config_file:
                    overrides = json.load(config_file) or {}
        except json.JSONDecodeError as exc:
            # Invalid JSON should not prevent service startup; log and proceed with defaults
            import logging

            logging.getLogger(__name__).warning(
                "Failed to parse MQTT/Zigbee configuration overrides (%s): %s",
                config_path,
                exc,
            )

        mapping = {
            "MQTT_BROKER": "MQTT_BROKER",
            "MQTT_USERNAME": "MQTT_USERNAME",
            "MQTT_PASSWORD": "MQTT_PASSWORD",
            "ZIGBEE2MQTT_BASE_TOPIC": "ZIGBEE2MQTT_BASE_TOPIC",
        }

        for attr_name, override_key in mapping.items():
            if override_key in overrides and overrides[override_key] not in (None, ""):
                setattr(self, attr_name, overrides[override_key])

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

    def validate_required_runtime_fields(self) -> None:
        """Validate critical runtime fields before service startup."""
        missing_fields = []

        if not (self.HA_TOKEN and self.HA_TOKEN.strip()):
            missing_fields.append("HA_TOKEN")

        if missing_fields:
            raise ValueError(
                f"Missing required configuration values: {', '.join(missing_fields)}. "
                "Set these environment variables before starting the service."
            )

    def get_allowed_origins(self) -> list[str]:
        """Return the configured CORS origins."""
        return self.ALLOWED_ORIGINS


# Global settings instance
settings = Settings()
settings.apply_overrides()
