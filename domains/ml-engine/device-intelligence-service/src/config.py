"""Device Intelligence Service - Configuration Management.

Inherits common fields from BaseServiceSettings (service_name, service_port,
log_level, cors_origins, postgres_url, database_url, database_schema, etc.).

UPPERCASE aliases are kept for backward compatibility with existing code that
references settings.DEVICE_INTELLIGENCE_PORT, settings.LOG_LEVEL, etc.
"""

import json
import os
from pathlib import Path

from homeiq_data import BaseServiceSettings
from pydantic import Field, SecretStr, field_validator

MODELS_DIR_ENV = "MODELS_DIR"


def _determine_models_dir() -> Path:
    """Resolve where trained model artifacts are written.

    Anchored to the service root, not the process working directory. The path
    used to be a bare relative "models", so it landed wherever a process
    happened to be launched from — running the test suite from the repo root
    left a second, untracked models directory there.
    """
    env_override = os.getenv(MODELS_DIR_ENV)
    if env_override:
        return Path(env_override)

    return Path(__file__).resolve().parents[1] / "models"


DEFAULT_MODELS_DIR = _determine_models_dir()


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables.

    Inherits from BaseServiceSettings for standard fields (service_name,
    service_port, log_level, cors_origins, postgres_url, etc.).
    """

    # Override base defaults
    service_port: int = Field(default=8019, description="Service port")
    service_name: str = "device-intelligence-service"

    # Backward-compatible UPPERCASE aliases (properties)
    @property
    def DEVICE_INTELLIGENCE_PORT(self) -> int:
        """Backward-compatible alias for service_port."""
        return self.service_port

    @property
    def DEVICE_INTELLIGENCE_HOST(self) -> str:
        """Backward-compatible alias for service host."""
        return "0.0.0.0"  # noqa: S104

    @property
    def LOG_LEVEL(self) -> str:
        """Backward-compatible alias for log_level."""
        return self.log_level

    @property
    def DATABASE_URL(self) -> str:
        """Backward-compatible alias for database_url."""
        return self.database_url

    # Home Assistant Configuration
    HA_URL: str = Field(
        default="http://homeassistant:8123",
        description="Home Assistant URL (primary)",
    )
    HA_WS_URL: str | None = Field(
        default=None,
        description="Home Assistant WebSocket URL (primary)",
    )
    HA_TOKEN: str | None = Field(
        default=None,
        description="Home Assistant long-lived access token (primary)",
    )

    # Nabu Casa Fallback Configuration
    NABU_CASA_URL: str | None = Field(
        default=None,
        description="Nabu Casa URL for remote access fallback",
    )
    NABU_CASA_TOKEN: str | None = Field(
        default=None,
        description="Nabu Casa long-lived access token for fallback",
    )

    # Redis
    REDIS_URL: str = Field(
        default="redis://redis:6379/0",
        description="Redis cache URL",
    )

    # Performance Configuration
    MAX_WORKERS: int = Field(default=4, description="Maximum number of worker processes")
    REQUEST_TIMEOUT: int = Field(default=30, description="Request timeout in seconds")

    # Cache Configuration
    CACHE_TTL: int = Field(default=300, description="Default cache TTL in seconds")
    MAX_CACHE_SIZE: int = Field(default=1000, description="Maximum cache size")

    # Name Enhancement Configuration
    AUTO_GENERATE_NAME_SUGGESTIONS: bool = Field(
        default=False,
        description="Automatically generate name suggestions during device discovery",
    )
    OPENAI_API_KEY: SecretStr | None = Field(
        default=None,
        description="OpenAI API key for AI name generation (optional)",
    )
    ENABLE_LOCAL_LLM: bool = Field(
        default=False,
        description="Enable local LLM (Ollama) for name generation (optional)",
    )

    # Authentication Configuration (CRIT-3)
    API_KEY: str | None = Field(
        default=None,
        description="API key for non-health endpoints",
    )
    ADMIN_API_TOKEN: str | None = Field(
        default=None,
        description="Admin token for destructive operations",
    )

    # CORS (UPPERCASE alias for backward compat)
    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
        ],
        description="Allowed CORS origins",
    )

    # ML Model Configuration
    ML_FAILURE_MODEL: str = Field(
        default="randomforest",
        description="Failure prediction model: randomforest, lightgbm, or tabpfn",
    )
    ML_USE_INCREMENTAL: bool = Field(
        default=False,
        description="Use incremental learning for model updates",
    )
    ML_INCREMENTAL_UPDATE_THRESHOLD: int = Field(
        default=100,
        description="Number of samples before incremental update",
    )
    GNN_USE_COMPILE: bool = Field(
        default=True,
        description="Use PyTorch compile for GNN training",
    )

    # Training Scheduler Configuration (Epic 46.2)
    ML_TRAINING_SCHEDULE: str = Field(
        default="0 2 * * *",
        description="Cron expression for training schedule (default: 2 AM daily)",
    )
    ML_TRAINING_ENABLED: bool = Field(
        default=True,
        description="Enable automatic nightly training",
    )
    ML_TRAINING_MODE: str = Field(
        default="incremental",
        description="Training mode: 'full' or 'incremental'",
    )

    @field_validator("HA_URL", mode="after")
    @classmethod
    def validate_ha_url(cls, v: str) -> str:
        """Validate Home Assistant URL format."""
        if not v.startswith(("http://", "https://")):
            msg = "HA_URL must start with http:// or https://"
            raise ValueError(msg)
        return v.rstrip("/")

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def normalize_allowed_origins(cls, value: str | list[str]) -> list[str] | str:
        """Support comma-delimited strings for allowed origins."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                try:
                    parsed = json.loads(stripped)
                    if isinstance(parsed, list):
                        return parsed
                except json.JSONDecodeError as exc:
                    msg = f"Invalid ALLOWED_ORIGINS JSON: {exc}"
                    raise ValueError(msg) from exc
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    def get_database_url(self) -> str:
        """Get the database URL for SQLAlchemy."""
        return self.database_url

    def get_redis_url(self) -> str:
        """Get the Redis URL for caching."""
        return self.REDIS_URL

    def get_ha_url(self) -> str:
        """Get the effective Home Assistant URL with Nabu Casa fallback."""
        return self.HA_URL

    def get_ha_ws_url(self) -> str:
        """Get the WebSocket URL for Home Assistant."""
        if self.HA_WS_URL:
            return self.HA_WS_URL
        return (
            self.HA_URL.replace("http://", "ws://").replace("https://", "wss://") + "/api/websocket"
        )

    def get_nabu_casa_ws_url(self) -> str | None:
        """Get the WebSocket URL for Nabu Casa."""
        if self.NABU_CASA_URL:
            return self.NABU_CASA_URL.replace("https://", "wss://") + "/api/websocket"
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
            msg = (
                f"Missing required configuration values: {', '.join(missing_fields)}. "
                "Set these environment variables before starting the service."
            )
            raise ValueError(msg)

    def get_allowed_origins(self) -> list[str]:
        """Return the configured CORS origins."""
        return self.ALLOWED_ORIGINS


# Global settings instance
settings = Settings()
