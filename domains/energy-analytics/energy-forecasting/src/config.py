"""Configuration settings for Energy Forecasting Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8037
    service_name: str = "energy-forecasting"

    # Model settings
    model_path: str = "./models/energy_forecaster"

    # Request timeout
    request_timeout_seconds: float = 30.0


settings = Settings()
