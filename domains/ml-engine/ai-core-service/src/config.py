"""Configuration settings for AI Core Service."""

from pydantic import SecretStr

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Service identity
    service_port: int = 8018
    service_name: str = "ai-core-service"

    # API key for authentication
    ai_core_api_key: SecretStr | None = None

    # Downstream service URLs
    openvino_service_url: str = "http://openvino-service:8019"
    ml_service_url: str = "http://ml-service:8020"
    ner_service_url: str = "http://ner-service:8031"
    openai_service_url: str = "http://openai-service:8020"

    # Rate limiting
    ai_core_rate_limit: int = 60
    ai_core_rate_limit_window: int = 60

    # Request body size limit (bytes)
    max_content_length: int = 2_097_152  # 2MB


settings = Settings()
