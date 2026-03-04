"""Configuration for Log Aggregator Service.

Uses BaseServiceSettings from homeiq-data for standardized settings management.
"""

from pathlib import Path

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Log storage
    log_directory: str = "/app/logs"
    max_logs_memory: int = 10000
    collection_interval: int = 30  # seconds

    # API authentication
    log_aggregator_api_key: str | None = None

    # Override base defaults
    service_port: int = 8015
    service_name: str = "log-aggregator"

    @property
    def log_directory_path(self) -> Path:
        """Return log directory as a Path object."""
        return Path(self.log_directory)


settings = Settings()
