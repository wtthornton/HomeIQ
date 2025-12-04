"""Configuration management for HA AI Agent Service"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Service Configuration
    service_name: str = "ha-ai-agent-service"
    service_port: int = 8030

    # Home Assistant Configuration
    ha_url: str = Field(
        default="http://homeassistant:8123",
        description="Home Assistant URL"
    )
    ha_token: str = Field(
        default="",
        description="Home Assistant long-lived access token"
    )
    ha_timeout: int = 10  # Request timeout in seconds
    ha_max_retries: int = 3  # Maximum retry attempts

    # Data API Configuration
    data_api_url: str = Field(
        default="http://data-api:8006",
        description="Data API service URL"
    )

    # Device Intelligence Service Configuration
    device_intelligence_url: str = Field(
        default="http://device-intelligence-service:8019",
        description="Device Intelligence Service URL"
    )
    device_intelligence_enabled: bool = True

    # OpenAI Configuration
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for GPT-5.1 (better quality and 50% cost savings vs GPT-4o)"
    )
    openai_model: str = Field(
        default="gpt-5.1",
        description="OpenAI model to use (gpt-5.1 recommended - better quality and 50% cost savings vs GPT-4o)"
    )
    openai_max_tokens: int = Field(
        default=2048,
        description="Maximum tokens for OpenAI responses (GPT-5.1 generates concise YAML)"
    )
    openai_temperature: float = Field(
        default=0.5,
        description="Temperature for OpenAI responses (0.0-2.0). GPT-5.1 benefits from 0.4-0.6 for YAML generation"
    )
    openai_timeout: int = Field(
        default=30,
        description="OpenAI API timeout in seconds"
    )
    openai_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for OpenAI API calls"
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/ha_ai_agent.db",
        description="SQLite database URL for context cache and conversations"
    )
    conversation_ttl_days: int = Field(
        default=30,
        description="Time-to-live for conversations in days (default: 30)"
    )

    # Context Cache TTLs (in seconds)
    entity_summary_cache_ttl: int = 300  # 5 minutes
    areas_cache_ttl: int = 600  # 10 minutes
    services_cache_ttl: int = 600  # 10 minutes
    capability_patterns_cache_ttl: int = 900  # 15 minutes
    sun_info_cache_ttl: int = 3600  # 1 hour

    # Token Budget
    max_context_tokens: int = 1500  # Maximum tokens for initial context

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

