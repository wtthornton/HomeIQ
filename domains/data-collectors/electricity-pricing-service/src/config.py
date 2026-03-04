"""Configuration for Electricity Pricing Service.

Uses BaseServiceSettings from homeiq-data for common fields.
"""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Electricity Pricing Service settings loaded from environment variables."""

    service_name: str = "electricity-pricing-service"
    service_port: int = 8011

    # Provider configuration
    pricing_provider: str = Field(default="awattar", description="Pricing data provider name")

    # Service configuration
    fetch_interval: int = Field(default=3600, description="Fetch interval in seconds")
    cache_duration: int = Field(default=60, description="Cache duration in minutes")

    # Security configuration
    allowed_networks: str | None = Field(
        default=None,
        description="Comma-separated CIDR networks for access control",
    )


settings = Settings()
