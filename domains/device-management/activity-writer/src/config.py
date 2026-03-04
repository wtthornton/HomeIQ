"""Configuration settings for Activity Writer Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8035
    service_name: str = "activity-writer"


settings = Settings()
