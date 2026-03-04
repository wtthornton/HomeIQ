"""Configuration for the Admin API service.

Inherits common fields from BaseServiceSettings and adds
admin-specific settings for auth, rate limiting, and docs.
"""

import secrets

from homeiq_data import BaseServiceSettings
from homeiq_observability.logging_config import setup_logging
from pydantic import Field, model_validator

logger = setup_logging("admin-api.config")


class Settings(BaseServiceSettings):
    """Admin API settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8004
    service_name: str = "admin-api"

    # API metadata
    api_title: str = Field(
        default="Home Assistant Ingestor Admin API",
        alias="API_TITLE",
    )
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    api_description: str = Field(
        default="Admin API for Home Assistant Ingestor",
        alias="API_DESCRIPTION",
    )

    # Authentication
    admin_api_api_key: str | None = Field(default=None)
    api_key: str | None = Field(default=None)
    allow_anonymous: bool = Field(default=False, alias="ADMIN_API_ALLOW_ANONYMOUS")

    # Docs
    docs_enabled: bool = Field(default=False, alias="ADMIN_API_ENABLE_DOCS")
    openapi_enabled: bool = Field(default=False, alias="ADMIN_API_ENABLE_OPENAPI")

    # Rate limiting
    rate_limit_per_min: int = Field(default=60, alias="ADMIN_API_RATE_LIMIT_PER_MIN")
    rate_limit_burst: int = Field(default=20, alias="ADMIN_API_RATE_LIMIT_BURST")

    # CORS (extended)
    cors_methods: str = Field(default="GET,POST,PUT,DELETE", alias="CORS_METHODS")
    cors_headers: str = Field(default="*", alias="CORS_HEADERS")

    @model_validator(mode="after")
    def _resolve_api_key(self) -> "Settings":
        """Resolve and validate the API key after init."""
        resolved = self.admin_api_api_key or self.api_key
        if resolved:
            self.api_key = resolved
        elif self.allow_anonymous:
            self.api_key = secrets.token_urlsafe(48)
            logger.warning(
                "Admin API started in anonymous mode for local testing only. "
                "Set ADMIN_API_API_KEY to enforce authentication."
            )
        else:
            raise ValueError(
                "API_KEY (or ADMIN_API_API_KEY) must be set "
                "before starting admin-api"
            )
        return self

    def get_cors_methods_list(self) -> list[str]:
        """Parse cors_methods string into a list."""
        return [m.strip() for m in self.cors_methods.split(",") if m.strip()]

    def get_cors_headers_list(self) -> list[str]:
        """Parse cors_headers string into a list."""
        return [h.strip() for h in self.cors_headers.split(",") if h.strip()]


settings = Settings()
