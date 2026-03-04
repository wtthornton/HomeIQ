"""Configuration settings for OpenVINO Service."""

from pydantic import SecretStr

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Service identity
    service_port: int = 8019
    service_name: str = "openvino-service"

    # Model configuration
    openvino_max_embedding_texts: int = 100
    openvino_max_text_length: int = 4000
    openvino_max_rerank_candidates: int = 200
    openvino_max_rerank_top_k: int = 50
    openvino_max_query_length: int = 2000
    openvino_max_pattern_length: int = 4000
    openvino_preload_models: bool = False
    model_cache_dir: str = "/app/models"

    # Optional API key authentication (SEC-2)
    openvino_api_key: SecretStr | None = None


settings = Settings()
