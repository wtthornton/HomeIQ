"""Configuration management for AI Automation Service"""

import os
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    # Data API
    data_api_url: str = "http://data-api:8006"

    # Device Intelligence Service (Story DI-2.1)
    device_intelligence_url: str = "http://homeiq-device-intelligence:8019"
    device_intelligence_enabled: bool = True

    # InfluxDB (for direct event queries)
    influxdb_url: str = "http://influxdb:8086"
    influxdb_token: str = "homeiq-token"
    influxdb_org: str = "homeiq"
    influxdb_bucket: str = "home_assistant_events"

    # Home Assistant (Story AI4.1: Enhanced configuration)
    # Support multiple environment variable names for compatibility
    ha_url: str = Field(
        default="",
        description="Home Assistant URL (supports HA_URL, HA_HTTP_URL, HOME_ASSISTANT_URL)"
    )
    ha_token: str = Field(
        default="",
        description="Home Assistant token (supports HA_TOKEN, HOME_ASSISTANT_TOKEN)"
    )
    ha_max_retries: int = 3  # Maximum retry attempts for HA API calls
    ha_retry_delay: float = 1.0  # Initial retry delay in seconds
    ha_timeout: int = 10  # Request timeout in seconds

    # MQTT
    mqtt_broker: str
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None

    # OpenAI
    openai_api_key: str

    # Multi-Model Entity Extraction
    entity_extraction_method: str = "multi_model"  # multi_model, enhanced, pattern
    ner_model: str = "dslim/bert-base-NER"  # Hugging Face NER model
    openai_model: str = "gpt-5.1"  # OpenAI model for complex queries (GPT-5.1 - 50% cost savings vs GPT-4o)
    ner_confidence_threshold: float = 0.8  # Minimum confidence for NER results
    enable_entity_caching: bool = True  # Enable LRU cache for NER
    max_cache_size: int = 1000  # Maximum cache size

    # Scheduling
    analysis_schedule: str = "0 3 * * *"  # 3 AM daily (cron format)

    # Quality Framework Filtering (Quality Framework Enhancement 2025)
    pattern_min_quality_score: float = 0.5  # Minimum quality score for pattern acceptance (0.0-1.0)
    synergy_min_quality_score: float = 0.6  # Minimum quality score for synergy acceptance (0.0-1.0)
    enable_quality_filtering: bool = True  # Enable quality-based filtering for patterns and synergies

    # Pattern detection thresholds (single-home tuning)
    time_of_day_min_occurrences: int = 10
    time_of_day_base_confidence: float = 0.7
    time_of_day_occurrence_overrides: dict[str, int] = {
        "light": 8,
        "switch": 8,
        "media_player": 6,
        "lock": 4
    }
    time_of_day_confidence_overrides: dict[str, float] = {
        "light": 0.6,
        "switch": 0.6,
        "media_player": 0.6,
        "lock": 0.85,
        "climate": 0.75
    }

    co_occurrence_min_support: int = 10
    co_occurrence_base_confidence: float = 0.7
    co_occurrence_support_overrides: dict[str, int] = {
        "light": 6,
        "switch": 6,
        "media_player": 4,
        "lock": 4
    }
    co_occurrence_confidence_overrides: dict[str, float] = {
        "light": 0.6,
        "switch": 0.6,
        "media_player": 0.6,
        "lock": 0.85,
        "climate": 0.75
    }

    manual_refresh_cooldown_hours: int = 24

    # Database
    database_path: str = "/app/data/ai_automation.db"
    database_url: str = "sqlite+aiosqlite:///data/ai_automation.db"

    # Logging
    log_level: str = "INFO"

    # Authentication / Authorization (MANDATORY - cannot be disabled)
    # CRITICAL: Authentication is always required in production
    # Set AI_AUTOMATION_API_KEY environment variable to enable
    ai_automation_api_key: str = Field(
        default="",
        description="API key for authentication (REQUIRED - set via environment variable)"
    )
    ai_automation_admin_api_key: str | None = Field(
        default=None,
        description="Admin API key for elevated privileges (optional, defaults to regular API key)"
    )

    # Rate limiting (disabled for internal single-home use)
    rate_limit_enabled: bool = False  # Disable rate limiting for internal projects
    rate_limit_requests_per_minute: int = 120
    rate_limit_requests_per_hour: int = 2400
    rate_limit_internal_requests_per_minute: int = 600

    # Safety Validation (AI1.19)
    safety_level: str = "moderate"  # strict, moderate, or permissive
    safety_allow_override: bool = True  # Allow force_deploy override
    safety_min_score: int = 60  # Minimum safety score for moderate level

    # Natural Language Generation (AI1.21)
    nl_generation_enabled: bool = True
    nl_model: str = "gpt-5.1"  # OpenAI model for NL generation (GPT-5.1 - 50% cost savings vs GPT-4o)
    nl_max_tokens: int = 1500
    nl_temperature: float = 0.3  # Lower = more consistent

    # Unified Prompt System
    enable_device_intelligence_prompts: bool = True
    device_intelligence_timeout: int = 5

    # Prompt Configuration
    default_temperature: float = 0.7
    creative_temperature: float = 1.0  # For Ask AI - Maximum creativity for crazy ideas
    description_max_tokens: int = 300
    yaml_max_tokens: int = 600

    # Model Selection Configuration (Optimized for Cost/Quality Balance - 2025)
    # GPT-5.1: Best quality with 50% cost savings vs GPT-4o
    # GPT-5.1-mini: 80% cost savings with 90-95% quality for well-defined tasks
    # Phase 1: Switched low-risk tasks to GPT-5.1-mini for 80% cost savings
    suggestion_generation_model: str = "gpt-5.1"  # Best quality suggestions with 50% cost savings
    yaml_generation_model: str = "gpt-5.1"  # Best quality YAML generation (50% cheaper than GPT-4o)
    classification_model: str = "gpt-5.1-mini"  # Phase 1: 80% cost savings, 95% quality for classification
    entity_extraction_model: str = "gpt-5.1-mini"  # Phase 1: 80% cost savings, 95% quality for extraction

    # Token Budget Configuration (Phase 2)
    max_entity_context_tokens: int = 7_000  # Limit entity context size to reduce input tokens (reduced from 10_000 for optimization)
    max_enrichment_context_tokens: int = 2_000  # Limit enrichment data (weather, carbon, etc.)
    max_conversation_history_tokens: int = 1_000  # Limit conversation history size
    enable_token_counting: bool = True  # Enable token counting before API calls
    warn_on_token_threshold: int = 20_000  # Log warning when approaching this token count

    # Caching Configuration (Phase 4)
    entity_cache_ttl_seconds: int = 300  # 5-minute TTL for enriched entity data cache
    enable_prompt_caching: bool = True  # Enable OpenAI native prompt caching (90% discount)
    conversation_history_max_turns: int = 3  # Keep only last N conversation turns

    # Synthetic Home Generation OpenAI Enhancement
    synthetic_enable_openai: bool = False  # Enable OpenAI enhancement
    synthetic_enhancement_percentage: float = 0.20  # 20% OpenAI-enhanced
    synthetic_validation_percentage: float = 0.10  # 10% validation
    synthetic_openai_model: str = "gpt-5.1"  # Model for synthetic generation
    synthetic_openai_temperature: float = 0.3  # Temperature for structured outputs

    # Soft Prompt Fallback (single-home tuning)
    soft_prompt_enabled: bool = True
    soft_prompt_model_dir: str = "data/ask_ai_soft_prompt"
    soft_prompt_confidence_threshold: float = 0.85

    # Clarification Confidence Settings
    clarification_calibration_enabled: bool = True
    """Enable calibration for clarification confidence scores."""

    clarification_calibration_min_samples: int = 10
    """Minimum number of samples required for calibration training."""

    clarification_calibration_retrain_interval_days: int = 7
    """Interval in days for periodic calibration model retraining."""

    adaptive_threshold_enabled: bool = True
    """Enable adaptive confidence thresholds based on query complexity."""

    default_risk_tolerance: str = "medium"
    """Default user risk tolerance for adaptive thresholds: 'high', 'medium', or 'low'."""

    # Guardrails
    guardrail_enabled: bool = True
    guardrail_model_name: str = "unitary/toxic-bert"
    guardrail_threshold: float = 0.6

    # OpenAI Rate Limiting (Performance Optimization)
    openai_concurrent_limit: int = 5  # Max concurrent API calls

    # Synergy Selection Configuration
    synergy_max_suggestions: int = 7
    """Maximum number of synergy suggestions to generate in daily batch (default: 7)
    
    Increased from hardcoded 5 to better utilize 6,324 available opportunities.
    Rationale: With 82.6% pattern-validated synergies, we can safely increase
    the limit to improve suggestion diversity while maintaining quality.
    """

    synergy_min_priority: float = 0.6
    """Minimum priority score threshold for synergy selection (default: 0.6)
    
    Only synergies with calculated priority score >= this value will be
    considered for suggestion generation. Priority score combines:
    - 40% impact_score
    - 25% confidence
    - 25% pattern_support_score
    - 10% validation bonus
    - Complexity adjustment
    """

    synergy_use_priority_scoring: bool = True
    """Enable priority-based synergy selection (default: True)
    
    When enabled, synergies are selected using calculated priority score
    instead of simple impact_score ranking. This prioritizes pattern-validated
    synergies (5,224 out of 6,324) for better suggestion quality.
    """

    # Auto-Draft Generation Configuration (Story: Auto-Draft API)
    auto_draft_suggestions_enabled: bool = True
    """Enable automatic YAML draft generation during suggestion creation"""

    auto_draft_count: int = 1
    """Number of top suggestions to auto-generate YAML for (default: 1)

    Rationale:
    - 1 = Best UX/cost balance (most users approve top suggestion)
    - 3 = Good for batch reviews
    - 5+ = Use async pattern (see auto_draft_async_threshold)
    """

    auto_draft_async_threshold: int = 3
    """If auto_draft_count > this value, use async background jobs

    Rationale:
    - ≤3 drafts: Synchronous (200-500ms each = 0.6-1.5s total, acceptable)
    - >3 drafts: Async to prevent API timeout (>2s would degrade UX)
    """

    auto_draft_run_safety_validation: bool = False
    """Run safety validation during auto-draft generation (default: False)

    Rationale:
    - False = Faster generation, validation runs on approval (recommended)
    - True = Early validation, but slower API response (adds ~300ms per draft)
    """

    auto_draft_confidence_threshold: float = 0.70
    """Minimum confidence score to trigger auto-draft generation

    Only generate YAML for suggestions with confidence >= this threshold.
    Helps reduce wasted YAML generation for low-quality suggestions.
    """

    auto_draft_max_retries: int = 2
    """Max retries for YAML generation if OpenAI call fails"""

    auto_draft_timeout: int = 10
    """Timeout (seconds) for auto-draft generation per suggestion"""

    # Action Executor Configuration
    action_executor_workers: int = 2
    """Number of worker tasks for action execution (default: 2)"""

    action_executor_max_retries: int = 3
    """Maximum retry attempts for action execution (default: 3)"""

    action_executor_retry_delay: float = 1.0
    """Initial retry delay in seconds for action execution (default: 1.0)"""

    use_action_executor: bool = True
    """Use ActionExecutor for test execution instead of create/delete automations (default: True)"""

    # Expert Mode Configuration
    expert_mode_enabled: bool = True
    """Enable expert mode for advanced users who want full control over each step"""

    expert_mode_default: bool = False
    """Default mode if not specified in request: False=auto_draft, True=expert"""

    expert_mode_allow_mode_switching: bool = True
    """Allow users to switch between Standard and Expert modes mid-flow"""

    expert_mode_yaml_validation_strict: bool = True
    """Enforce strict YAML validation in expert mode (recommended)"""

    expert_mode_validate_on_save: bool = True
    """Validate YAML on save rather than on every keystroke (better performance)"""

    expert_mode_show_yaml_diff: bool = True
    """Show YAML diffs when editing (helpful for experts to track changes)"""

    expert_mode_max_yaml_edits: int = 10
    """Maximum number of YAML edits allowed per suggestion (prevent abuse)"""

    expert_mode_allow_dangerous_operations: bool = False
    """Allow potentially dangerous YAML operations (shell_command, python_script, etc.)

    SECURITY: Only enable this for trusted admin users. Dangerous operations include:
    - shell_command.* (arbitrary shell execution)
    - python_script.* (arbitrary Python code)
    - script.turn_on (script execution)
    - homeassistant.restart (system restart)
    """

    expert_mode_blocked_services: list[str] = [
        "shell_command",
        "python_script",
        "script.turn_on",
        "automation.reload",
        "homeassistant.restart",
        "homeassistant.stop"
    ]
    """Services blocked in expert mode unless allow_dangerous_operations=true"""

    expert_mode_require_approval_services: list[str] = [
        "notify",
        "camera",
        "lock",
        "cover",
        "climate"
    ]
    """Services that require explicit user confirmation before deployment"""

    # Experimental Orchestration Flags
    enable_langchain_prompt_builder: bool = False
    """Use LangChain-based prompt templating for Ask AI (prototype)."""

    enable_langchain_pattern_chain: bool = False
    """Run selected pattern detectors through LangChain sequential chain (prototype)."""

    enable_pdl_workflows: bool = False
    """Execute nightly batch and synergy guardrails through PDL interpreter."""

    enable_self_improvement_pilot: bool = False
    """Enable weekly self-improvement summary using LangChain templating."""

    # Admin / training safeguards
    training_script_path: str = "scripts/train_soft_prompt.py"
    training_script_sha256: str | None = None

    # Fuzzy Matching Configuration
    fuzzy_matching_enabled: bool = True
    """Enable fuzzy matching for entity resolution and device mapping (default: True)
    
    When enabled, uses rapidfuzz for typo handling, abbreviation matching,
    and word order independence. Improves user experience by handling:
    - Typos: "office lite" → "office light"
    - Abbreviations: "LR light" → "Living Room Light"
    - Word order: "light living room" → "living room light"
    """
    
    fuzzy_matching_threshold: float = 0.7
    """Minimum fuzzy match score threshold (0.0-1.0) for entity resolution (default: 0.7)
    
    Threshold selection rationale:
    - 0.6: More permissive, catches more typos but may have false positives
    - 0.7: Balanced (recommended) - good accuracy with reasonable typo tolerance
    - 0.8: Stricter, fewer false positives but may miss some valid matches
    - 0.9: Very strict, only high-confidence matches
    
    Lower thresholds (0.6-0.7) are recommended for entity resolution where
    user intent is clear from context. Higher thresholds (0.8-0.9) may be
    used for critical operations where precision is paramount.
    """

    # Device Matching Configuration (2025 Enhancement)
    device_matching_auto_select_threshold: float = 0.90
    """Auto-select if single match above this score (default: 0.90)
    
    When device matching finds a single match with score >= this threshold,
    it will be automatically selected without user confirmation.
    """

    device_matching_high_confidence_threshold: float = 0.85
    """Return top 3 matches if above this score (default: 0.85)
    
    When device matching finds matches with score >= this threshold,
    return top 3 matches for user selection.
    """

    device_matching_minimum_threshold: float = 0.70
    """Minimum score to consider a match (default: 0.70)
    
    Only matches with score >= this threshold will be considered.
    Lower scores are discarded as invalid matches.
    """

    device_matching_area_fuzzy_threshold: float = 0.80
    """Area name fuzzy matching threshold (default: 0.80)
    
    When matching area names from queries against HA area registry,
    only matches with score >= this threshold will be considered.
    """

    device_matching_max_candidates: int = 100
    """Max entities for fuzzy matching performance (default: 100)
    
    Limits the number of candidate entities for fuzzy matching to
    prevent performance degradation with large entity sets.
    """

    # Blueprint Integration
    automation_miner_url: str = "http://automation-miner:8029"
    """Base URL for automation-miner service (default: http://automation-miner:8029)"""

    blueprint_match_threshold: float = 0.8
    """Minimum fit score to use blueprint instead of AI generation (default: 0.8)
    
    Only blueprints with fit_score >= this threshold will be used.
    Lower scores fall back to AI generation.
    """

    blueprint_enabled: bool = True
    """Enable blueprint integration for YAML generation (default: True)
    
    When enabled, the service will attempt to match suggestions to blueprints
    before falling back to AI generation. Set to False to disable blueprint matching.
    """

    # GNN Synergy Detection Configuration
    gnn_hidden_dim: int = 64
    """Hidden dimension size for GNN model (default: 64)"""

    gnn_num_layers: int = 2
    """Number of GNN layers (default: 2, start conservative)"""

    gnn_learning_rate: float = 0.001
    """Learning rate for GNN training (default: 0.001)"""

    gnn_batch_size: int = 32
    """Batch size for GNN training (default: 32)"""

    gnn_epochs: int = 30
    """Number of training epochs (default: 30, start conservative)"""

    gnn_early_stopping_patience: int = 5
    """Early stopping patience in epochs (default: 5)"""

    gnn_model_path: str = "/app/models/gnn_synergy_detector.pth"
    """Path to save/load GNN model (default: /app/models/gnn_synergy_detector.pth)"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields from environment to prevent validation errors
        env_ignore_empty=True,  # Ignore empty environment variables
    )
    
    @field_validator("ha_url", mode="before")
    @classmethod
    def validate_ha_url(cls, v: str | None) -> str:
        """Validate and load HA URL from alternative environment variable names"""
        if v:
            return v
        # Try alternative environment variable names
        return (
            os.getenv("HA_URL") or
            os.getenv("HA_HTTP_URL") or
            os.getenv("HOME_ASSISTANT_URL") or
            ""
        )
    
    @field_validator("ha_token", mode="before")
    @classmethod
    def validate_ha_token(cls, v: str | None) -> str:
        """Validate and load HA token from alternative environment variable names"""
        if v:
            return v
        # Try alternative environment variable names
        return (
            os.getenv("HA_TOKEN") or
            os.getenv("HOME_ASSISTANT_TOKEN") or
            ""
        )
    
    @model_validator(mode="after")
    def validate_required_fields(self):
        """Validate required fields after initialization (Pydantic v2 pattern)"""
        if not self.ha_url:
            raise ValueError(
                "ha_url is required. Set HA_URL, HA_HTTP_URL, or HOME_ASSISTANT_URL in environment."
            )
        if not self.ha_token:
            raise ValueError(
                "ha_token is required. Set HA_TOKEN or HOME_ASSISTANT_TOKEN in environment."
            )
        return self


# Global settings instance
settings = Settings()

