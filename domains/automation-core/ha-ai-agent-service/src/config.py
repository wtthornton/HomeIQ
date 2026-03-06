"""Configuration management for HA AI Agent Service."""

from homeiq_data import BaseServiceSettings
from pydantic import Field, SecretStr


class Settings(BaseServiceSettings):
    """Application settings loaded from environment.

    Inherits from BaseServiceSettings which provides: service_name,
    service_port, log_level, database_url, postgres_url, database_schema,
    data_api_url, data_api_key, openai_api_key (SecretStr), cors_origins,
    influxdb_url/token/org/bucket, and effective_database_url property.
    """

    # Override base defaults
    service_name: str = "ha-ai-agent-service"
    service_port: int = 8030

    # Home Assistant Configuration
    ha_url: str = Field(
        default="http://homeassistant:8123",
        description="Home Assistant URL",
    )
    ha_token: SecretStr = Field(
        default="",
        description="Home Assistant long-lived access token",
    )
    ha_timeout: int = 10  # Request timeout in seconds
    ha_max_retries: int = 3  # Maximum retry attempts

    # AI Automation Service Configuration
    ai_automation_service_url: str = Field(
        default="http://ai-automation-service-new:8025",
        description="AI Automation Service URL (Hybrid Flow endpoints)",
    )
    ai_automation_api_key: SecretStr | None = Field(
        default=None,
        description="API key for AI Automation Service (required for patterns/synergies endpoints)",
    )

    # Hybrid Flow Configuration
    use_hybrid_flow: bool = Field(
        default=True,
        description="Use Hybrid Flow (template-based) for automation generation (preferred)",
    )

    # YAML Validation Service Configuration (Epic 51)
    yaml_validation_service_url: str = Field(
        default="http://yaml-validation-service:8037",
        description="YAML Validation Service URL for comprehensive YAML validation",
    )
    yaml_validation_api_key: SecretStr | None = Field(
        default=None,
        description="API key for YAML Validation Service (optional)",
    )

    # Device Control Service Configuration (Epic 25)
    ha_device_control_url: str = Field(
        default="http://ha-device-control:8040",
        description="HA Device Control Service URL for direct device control",
    )

    # Device Intelligence Service Configuration
    device_intelligence_url: str = Field(
        default="http://device-intelligence-service:8019",
        description="Device Intelligence Service URL",
    )
    device_intelligence_api_key: SecretStr | None = Field(
        default=None,
        description="API key for Device Intelligence Service (X-API-Key auth)",
    )
    device_intelligence_enabled: bool = True

    # AI Pattern Service Configuration
    ai_pattern_service_url: str = Field(
        default="http://ai-pattern-service:8020",
        description="AI Pattern Service URL for synergy data",
    )

    # Blueprint Suggestion Service Configuration
    blueprint_suggestion_url: str = Field(
        default="http://blueprint-suggestion-service:8032",
        description="Blueprint Suggestion Service URL",
    )

    # WebSocket Ingestion Service (Epic 28 — house status aggregator)
    websocket_ingestion_url: str = Field(
        default="http://websocket-ingestion:8001",
        description="WebSocket Ingestion Service URL for house status aggregator",
    )

    # Sports API Configuration
    sports_api_url: str = Field(
        default="http://sports-api:8005",
        description="Sports API Service URL for Team Tracker data",
    )
    sports_api_key: SecretStr | None = Field(
        default=None,
        description="API key for Sports API (X-API-Key auth)",
    )

    # Weather API Configuration
    weather_api_url: str = Field(
        default="http://weather-api:8009",
        description="Weather API Service URL for weather data",
    )

    # OpenAI Configuration (openai_api_key inherited from base as SecretStr)
    openai_model: str = Field(
        default="gpt-5.2-codex",
        description="OpenAI model for agentic chat, tool calling, and YAML generation",
    )
    openai_max_tokens: int = Field(
        default=8192,
        description="Maximum completion tokens",
    )
    openai_temperature: float = Field(
        default=0.7,
        description="Temperature for OpenAI responses",
    )
    openai_reasoning_effort: str | None = Field(
        default=None,
        description=(
            "Reasoning effort for reasoning models (low, medium, high, xhigh)."
            " None for non-reasoning models."
        ),
    )
    openai_timeout: int = Field(
        default=60,
        description="OpenAI API timeout in seconds",
    )
    openai_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for OpenAI API calls",
    )

    # Database (database_url and postgres_url inherited from base)
    conversation_ttl_days: int = Field(
        default=30,
        description="Time-to-live for conversations in days (default: 30)",
    )

    # Context Cache TTLs (in seconds)
    entity_summary_cache_ttl: int = 300  # 5 minutes
    areas_cache_ttl: int = 600  # 10 minutes
    services_cache_ttl: int = 600  # 10 minutes
    capability_patterns_cache_ttl: int = 900  # 15 minutes
    sun_info_cache_ttl: int = 3600  # 1 hour

    # Token Budget (increased for richer entity context and better suggestions)
    max_context_tokens: int = 3000  # Maximum tokens for initial context (was 1500)

    # Memory Extraction Configuration (Story 30.1)
    enable_memory_extraction: bool = Field(
        default=False,
        description="Enable automatic memory extraction from user messages (Story 30.1)",
    )
    memory_database_url: str | None = Field(
        default=None,
        description="Database URL for memory storage (falls back to DATABASE_URL)",
    )

