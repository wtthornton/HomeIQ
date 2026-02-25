"""Configuration management for AI Query Service"""

from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Database
    database_path: str = "/app/data/ai_automation.db"
    database_url: str = "sqlite+aiosqlite:////app/data/ai_automation.db"  # Absolute path for SQLite
    database_pool_size: int = 10  # Connection pool size (optimized for query service)
    database_max_overflow: int = 5  # Max overflow connections

    # PostgreSQL (Epic 3-4 migration)
    postgres_url: str = ""  # Set via POSTGRES_URL env var
    database_schema: str = "automation"  # Set via DATABASE_SCHEMA env var

    @property
    def effective_database_url(self) -> str:
        """Return PostgreSQL URL if set, otherwise fall back to SQLite."""
        return self.postgres_url or self.database_url

    # Data API Configuration
    data_api_url: str = "http://data-api:8006"

    # Home Assistant Configuration
    ha_url: str | None = None
    ha_token: str | None = None

    # Device Intelligence Service
    device_intelligence_url: str = "http://device-intelligence-service:8023"

    # OpenAI Configuration
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"  # Better entity extraction than gpt-4o-mini (see implementation/OPENAI_MODEL_RESEARCH_2026.md)
    openai_timeout: float = 30.0  # Timeout for OpenAI API calls (seconds)

    # Query Service Performance Settings
    query_timeout: float = 5.0  # Max time for query processing (seconds)
    max_query_length: int = 500  # Max characters in query
    enable_caching: bool = True  # Enable query result caching
    cache_ttl: int = 300  # Cache TTL in seconds (5 minutes)

    # Entity Extraction Optimization
    enable_parallel_extraction: bool = True  # Enable parallel entity extraction
    extraction_timeout: float = 2.0  # Timeout for entity extraction (seconds)

    # Clarification Settings
    clarification_enabled: bool = True
    clarification_confidence_threshold: float = 0.7
    max_clarification_questions: int = 3

    # Authentication
    api_keys: set[str] = set()  # Allowed API keys (empty = allow all authenticated)

    # Rate Limiting
    rate_limit_enabled: bool = True

    # Logging
    log_level: str = "INFO"

    # Service Configuration
    service_port: int = 8018
    service_name: str = "ai-query-service"

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


settings = Settings()

