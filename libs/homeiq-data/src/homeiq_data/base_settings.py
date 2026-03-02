"""Base settings class for HomeIQ services.

Provides common fields shared across 16+ services so each service
only needs to declare its service-specific settings.

Usage::

    from homeiq_data import BaseServiceSettings

    class Settings(BaseServiceSettings):
        # Service-specific fields only
        scheduler_enabled: bool = True
        min_confidence: float = 0.6

        class Config:
            env_prefix = "MY_SERVICE_"

    settings = Settings()
"""

from __future__ import annotations

from pydantic import ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings


class BaseServiceSettings(BaseSettings):
    """Common settings inherited by all HomeIQ services.

    Fields are loaded from environment variables.  Each service
    subclass should add its own service-specific fields and
    optionally set ``env_prefix`` for namespaced env vars.
    """

    # Service identity
    service_name: str = Field(default="homeiq-service", description="Service name for logging and health checks")
    service_port: int = Field(default=8000, description="Port the service listens on")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

    # Data API
    data_api_url: str = Field(default="http://data-api:8006", description="Data API base URL")
    data_api_key: SecretStr | None = Field(default=None, description="Data API Bearer token")

    # InfluxDB
    influxdb_url: str = Field(default="http://influxdb:8086", description="InfluxDB base URL")
    influxdb_token: SecretStr | None = Field(default=None, description="InfluxDB auth token")
    influxdb_org: str = Field(default="homeiq", description="InfluxDB organization")
    influxdb_bucket: str = Field(default="home_assistant_events", description="InfluxDB bucket")

    # PostgreSQL
    postgres_url: str = Field(default="", description="PostgreSQL connection URL")
    database_url: str = Field(default="", description="Fallback database URL")
    database_schema: str = Field(default="public", description="PostgreSQL schema name")

    # CORS
    cors_origins: str | None = Field(
        default=None,
        description="Comma-separated allowed CORS origins (None = ['*'])",
    )

    @property
    def effective_database_url(self) -> str:
        """Return the best available database URL."""
        return self.postgres_url or self.database_url

    def get_cors_origins_list(self) -> list[str]:
        """Parse cors_origins string into a list."""
        if self.cors_origins:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        return ["*"]

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
