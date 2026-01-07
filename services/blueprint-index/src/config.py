"""Configuration settings for Blueprint Index Service."""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "sqlite+aiosqlite:///data/blueprint_index.db"
    database_pool_size: int = 10
    database_max_overflow: int = 5
    
    # GitHub API
    github_token: str | None = None
    github_rate_limit_per_sec: float = 1.0  # Conservative default
    github_retries: int = 3
    
    # Discourse API
    discourse_base_url: str = "https://community.home-assistant.io"
    discourse_rate_limit_per_sec: float = 0.5
    
    # HTTP Settings
    http_timeout_connect: float = 10.0
    http_timeout_read: float = 30.0
    http_timeout_write: float = 30.0
    http_timeout_pool: float = 10.0
    http_max_keepalive: int = 5
    http_max_connections: int = 10
    
    # Search Settings
    search_default_limit: int = 50
    search_max_limit: int = 200
    min_quality_score: float = 0.5
    
    # Indexing Settings
    index_batch_size: int = 100
    index_refresh_interval_hours: int = 24
    
    # Logging
    log_level: str = "INFO"
    
    # Service Configuration
    service_port: int = 8031
    service_name: str = "blueprint-index"
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()
