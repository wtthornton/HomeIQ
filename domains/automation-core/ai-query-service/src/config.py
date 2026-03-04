"""Configuration management for AI Query Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment.

    Inherits from BaseServiceSettings which provides: service_name,
    service_port, log_level, database_url, postgres_url, database_schema,
    data_api_url, data_api_key, openai_api_key (SecretStr), cors_origins,
    influxdb_url/token/org/bucket, effective_database_url property,
    and get_cors_origins_list().
    """

    # Override base defaults
    service_name: str = "ai-query-service"
    service_port: int = 8018
    database_schema: str = "automation"

    # Legacy path (kept for backward compat with env vars)
    database_path: str = "/app/data/ai_automation.db"
    database_pool_size: int = 10  # Connection pool size (optimized for query service)
    database_max_overflow: int = 5  # Max overflow connections

    # Home Assistant Configuration
    ha_url: str | None = None
    ha_token: str | None = None

    # Device Intelligence Service
    device_intelligence_url: str = "http://device-intelligence-service:8019"

    # OpenAI Configuration (openai_api_key inherited from base as SecretStr)
    openai_model: str = "gpt-5-mini"  # Better entity extraction than gpt-4o-mini
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


settings = Settings()

