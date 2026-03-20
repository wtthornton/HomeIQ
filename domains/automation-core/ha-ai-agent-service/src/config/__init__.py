"""Configuration management for HA AI Agent Service."""

from homeiq_data import BaseServiceSettings
from pydantic import Field, SecretStr


class Settings(BaseServiceSettings):
    """Application settings loaded from environment.

    Inherits from BaseServiceSettings which provides: service_name,
    service_port, log_level, database_url, postgres_url, database_schema,
    data_api_url, data_api_key, cors_origins,
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

    # Anthropic Configuration (Epic 97: Prompt Caching & Claude Provider)
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Anthropic API key for Claude-based automation generation",
    )
    anthropic_model: str = Field(
        default="claude-sonnet-4-6",
        description="Anthropic model for automation generation",
    )
    llm_provider: str = Field(
        default="openai",
        description="Primary LLM provider: 'openai' or 'anthropic'",
    )
    llm_fallback_provider: str | None = Field(
        default="openai",
        description="Fallback LLM provider if primary fails (None to disable)",
    )

    # OpenAI Configuration
    openai_api_key: SecretStr = Field(
        default="",
        description="OpenAI API key for GPT-based automation generation",
    )
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

    # Epic 70: Self-Improving Agent — Hermes-Inspired Features

    # Story 70.3: Smart Model Routing
    routing_enabled: bool = Field(
        default=True,
        description="Enable smart model routing (cheap model for simple queries)",
    )
    cheap_model: str = Field(
        default="gpt-4.1-mini",
        description="Cheap/fast model for simple queries",
    )
    cheap_model_max_chars: int = Field(
        default=160,
        description="Max message chars for cheap model routing",
    )
    cheap_model_max_words: int = Field(
        default=28,
        description="Max message words for cheap model routing",
    )

    # Story 70.1: Skill Learning
    enable_skill_learning: bool = Field(
        default=True,
        description="Enable procedural skill learning from conversations",
    )

    # Story 70.4: Context Compression
    context_compression_enabled: bool = Field(
        default=True,
        description="Enable intelligent context compression",
    )
    compression_threshold_pct: float = Field(
        default=0.5,
        description="Context usage threshold (0.0-1.0) to trigger compression",
    )

    # Story 70.5: Subagent Delegation
    delegation_enabled: bool = Field(
        default=True,
        description="Enable multi-area subagent delegation",
    )
    max_subagents: int = Field(
        default=3,
        description="Maximum parallel subagents",
    )
    subagent_max_tokens: int = Field(
        default=8000,
        description="Per-subagent output token budget",
    )

    # Story 70.6: Session Search
    session_search_enabled: bool = Field(
        default=True,
        description="Enable cross-conversation session search",
    )

    # Story 70.7: User Modeling
    user_modeling_enabled: bool = Field(
        default=True,
        description="Enable cross-session user preference modeling",
    )
    profile_ttl_days: int = Field(
        default=90,
        description="TTL for user preference dimensions (days)",
    )

    # Story 70.8: Prompt Caching
    prompt_caching_enabled: bool = Field(
        default=True,
        description="Enable prompt caching for reduced token costs",
    )

    # Epic 69: Agent Eval — Adaptive Model Routing & Feedback Loop

    # Story 69.1-69.2: Adaptive Model Routing
    adaptive_routing_enabled: bool = Field(
        default=True,
        description="Enable eval-score-driven adaptive model routing",
    )
    eval_score_floor: float = Field(
        default=70.0,
        description="Min eval score before auto-upgrading to primary model",
    )

    # Story 69.4: Eval Degradation Alerting
    eval_alerting_enabled: bool = Field(
        default=True,
        description="Enable automated eval degradation alerts",
    )
    eval_drop_threshold_pct: float = Field(
        default=10.0,
        description="Percent drop threshold to trigger alert (vs 7-day baseline)",
    )

    # Story 69.6: Cost Tracking
    cost_tracking_enabled: bool = Field(
        default=True,
        description="Enable API cost tracking and savings reporting",
    )

