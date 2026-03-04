"""Configuration for Carbon Intensity Service.

Uses BaseServiceSettings from homeiq-data for common fields.
"""

import re

from homeiq_data import BaseServiceSettings
from pydantic import Field, field_validator


class Settings(BaseServiceSettings):
    """Carbon Intensity Service settings loaded from environment variables."""

    service_name: str = "carbon-intensity-service"
    service_port: int = 8010

    # WattTime credentials
    watttime_username: str | None = Field(default=None, description="WattTime username")
    watttime_password: str | None = Field(default=None, description="WattTime password")
    watttime_api_token: str | None = Field(default=None, description="Optional static WattTime token")

    # Grid configuration
    grid_region: str = Field(default="CAISO_NORTH", description="WattTime grid region")

    # Service configuration
    fetch_interval: int = Field(default=900, description="Fetch interval in seconds")

    @field_validator("grid_region")
    @classmethod
    def validate_grid_region(cls, v: str) -> str:
        """Ensure grid region contains only safe characters."""
        if not re.match(r"^[A-Za-z0-9_]+$", v):
            msg = f"Invalid GRID_REGION '{v}': must be alphanumeric and underscores only"
            raise ValueError(msg)
        return v


settings = Settings()
