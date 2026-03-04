"""Configuration for Data Retention Service.

Uses BaseServiceSettings from homeiq-data for standardized settings management.
"""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Scheduling intervals
    cleanup_interval_hours: int = 24
    monitoring_interval_minutes: int = 5
    compression_interval_hours: int = 24
    backup_interval_hours: int = 24

    # Backup
    backup_dir: str = "/backups"

    # API authentication
    data_retention_api_key: str | None = None

    # Override base defaults
    service_port: int = 8080
    service_name: str = "data-retention"


settings = Settings()
