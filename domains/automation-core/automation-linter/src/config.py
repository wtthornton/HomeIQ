"""Configuration settings for Automation Linter Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8020
    service_name: str = "automation-linter"


settings = Settings()
