"""
Configuration Settings for RAG Service

Using pydantic-settings for environment variable management.
Following 2025 patterns: type-safe configuration.
"""

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    
    Environment variables are prefixed with 'RAG_' (e.g., RAG_SERVICE_PORT).
    """
    
    model_config = SettingsConfigDict(
        env_prefix="RAG_",
        case_sensitive=False,
        env_file=".env",
        env_file_encoding="utf-8",
    )
    
    # Service configuration
    service_port: int = 8027
    service_host: str = "0.0.0.0"
    
    # Database configuration
    database_path: str = "/app/data/rag_service.db"
    database_echo: bool = False
    
    # OpenVINO service configuration
    openvino_service_url: str = "http://openvino-service:8019"
    
    # RAG configuration
    embedding_cache_size: int = 100
    default_top_k: int = 5
    default_min_similarity: float = 0.7
    
    # Logging configuration
    log_level: str = "INFO"
    
    # CORS configuration
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Get CORS origins as list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
