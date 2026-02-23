"""Configuration management for HA AI Agent Service"""

from pydantic import Field, SecretStr
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
    ha_token: SecretStr = Field(
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
    data_api_key: SecretStr | None = Field(
        default=None,
        description="API key for Data API (Bearer auth)"
    )

    # AI Automation Service Configuration
    ai_automation_service_url: str = Field(
        default="http://ai-automation-service-new:8036",
        description="AI Automation Service URL (Hybrid Flow endpoints)"
    )
    ai_automation_api_key: SecretStr | None = Field(
        default=None,
        description="API key for AI Automation Service (required for patterns/synergies endpoints)"
    )

    # Hybrid Flow Configuration
    use_hybrid_flow: bool = Field(
        default=True,
        description="Use Hybrid Flow (template-based) for automation generation (preferred)"
    )

    # YAML Validation Service Configuration (Epic 51)
    yaml_validation_service_url: str = Field(
        default="http://yaml-validation-service:8037",
        description="YAML Validation Service URL for comprehensive YAML validation"
    )
    yaml_validation_api_key: SecretStr | None = Field(
        default=None,
        description="API key for YAML Validation Service (optional)"
    )

    # Device Intelligence Service Configuration
    device_intelligence_url: str = Field(
        default="http://device-intelligence-service:8019",
        description="Device Intelligence Service URL"
    )
    device_intelligence_api_key: SecretStr | None = Field(
        default=None,
        description="API key for Device Intelligence Service (X-API-Key auth)"
    )
    device_intelligence_enabled: bool = True

    # OpenAI Configuration
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-5.2-codex",
        description="OpenAI model to use (gpt-5.2-codex for agentic chat + tool calling + YAML generation; see implementation/LLM_ML_MODELS_02222026.md)"
    )
    openai_max_tokens: int = Field(
        default=8192,
        description="Maximum completion tokens"
    )
    openai_temperature: float = Field(
        default=0.7,
        description="Temperature for OpenAI responses"
    )
    openai_reasoning_effort: str | None = Field(
        default=None,
        description="Reasoning effort for reasoning models (low, medium, high, xhigh). None for non-reasoning models."
    )
    openai_timeout: int = Field(
        default=60,
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

    # Token Budget (increased for richer entity context and better suggestions)
    max_context_tokens: int = 3000  # Maximum tokens for initial context (was 1500)

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

