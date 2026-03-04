"""Configuration Settings for RAG Service.

Inherits common fields from BaseServiceSettings (service_name, service_port,
log_level, cors_origins, postgres_url, influxdb_*, data_api_*).
"""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings with environment variable support.

    Service-specific fields only; common fields come from BaseServiceSettings.
    """

    # Database configuration
    database_path: str = "/app/data/rag_service.db"
    database_echo: bool = False

    # OpenVINO service configuration
    openvino_service_url: str = "http://openvino-service:8019"

    # RAG configuration
    embedding_cache_size: int = 100
    default_top_k: int = 5
    default_min_similarity: float = 0.7

    # Override base defaults
    service_port: int = 8027
    service_name: str = "rag-service"


# Global settings instance
settings = Settings()
