"""Configuration settings for Data API Service.

Inherits common fields from BaseServiceSettings and adds
data-api-specific settings for auth, rate limiting, and timeouts.
"""

import secrets

from homeiq_data import BaseServiceSettings
from homeiq_observability.logging_config import setup_logging
from pydantic import Field, model_validator

logger = setup_logging("data-api.config")


class Settings(BaseServiceSettings):
    """Data API settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8006
    service_name: str = "data-api"

    # API metadata
    api_title: str = "Data API - Feature Data Hub"
    api_version: str = "1.0.0"
    api_description: str = "Feature data access (events, devices, sports, analytics)"

    # Authentication
    data_api_api_key: str | None = Field(default=None)
    data_api_key: str | None = Field(default=None)
    api_key: str | None = Field(default=None)
    allow_anonymous: bool = Field(default=False, alias="DATA_API_ALLOW_ANONYMOUS")

    # Rate limiting
    rate_limit_per_min: int = Field(default=100, alias="DATA_API_RATE_LIMIT_PER_MIN")
    rate_limit_burst: int = Field(default=20, alias="DATA_API_RATE_LIMIT_BURST")

    # Timeouts
    request_timeout: int = Field(default=30, alias="REQUEST_TIMEOUT")
    db_query_timeout: int = Field(default=10, alias="DB_QUERY_TIMEOUT")

    @model_validator(mode="after")
    def _resolve_api_key(self) -> "Settings":
        """Resolve and validate the API key after init."""
        resolved = self.data_api_api_key or self.data_api_key or self.api_key
        if resolved:
            self.api_key = resolved
        elif self.allow_anonymous:
            self.api_key = secrets.token_urlsafe(48)
        else:
            raise ValueError("DATA_API_API_KEY must be set")
        return self


settings = Settings()
