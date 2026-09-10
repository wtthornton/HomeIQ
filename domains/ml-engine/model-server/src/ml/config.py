"""Configuration settings for ML Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Service identity
    service_port: int = 8020
    service_name: str = "ml-service"

    # Algorithm limits
    ml_max_clusters: int = 100
    ml_max_batch_size: int = 100
    ml_algorithm_timeout_seconds: float = 8.0

    # Rate limiting
    ml_rate_limit_window: int = 60
    ml_rate_limit_max_requests: int = 120


settings = Settings()
