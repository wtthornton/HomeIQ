"""Configuration management for AI Automation Service"""

from pydantic_settings import BaseSettings
from typing import Optional, List, Dict


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
    ha_url: str
    ha_token: str
    ha_max_retries: int = 3  # Maximum retry attempts for HA API calls
    ha_retry_delay: float = 1.0  # Initial retry delay in seconds
    ha_timeout: int = 10  # Request timeout in seconds
    
    # MQTT
    mqtt_broker: str
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    
    # OpenAI
    openai_api_key: str
    
    # Multi-Model Entity Extraction
    entity_extraction_method: str = "multi_model"  # multi_model, enhanced, pattern
    ner_model: str = "dslim/bert-base-NER"  # Hugging Face NER model
    openai_model: str = "gpt-4o-mini"  # OpenAI model for complex queries
    ner_confidence_threshold: float = 0.8  # Minimum confidence for NER results
    enable_entity_caching: bool = True  # Enable LRU cache for NER
    max_cache_size: int = 1000  # Maximum cache size
    
    # Scheduling
    analysis_schedule: str = "0 3 * * *"  # 3 AM daily (cron format)
    
    # Pattern detection thresholds (single-home tuning)
    time_of_day_min_occurrences: int = 10
    time_of_day_base_confidence: float = 0.7
    time_of_day_occurrence_overrides: Dict[str, int] = {
        "light": 8,
        "switch": 8,
        "media_player": 6,
        "lock": 4
    }
    time_of_day_confidence_overrides: Dict[str, float] = {
        "light": 0.6,
        "switch": 0.6,
        "media_player": 0.6,
        "lock": 0.85,
        "climate": 0.75
    }
    
    co_occurrence_min_support: int = 10
    co_occurrence_base_confidence: float = 0.7
    co_occurrence_support_overrides: Dict[str, int] = {
        "light": 6,
        "switch": 6,
        "media_player": 4,
        "lock": 4
    }
    co_occurrence_confidence_overrides: Dict[str, float] = {
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
    
    # Safety Validation (AI1.19)
    safety_level: str = "moderate"  # strict, moderate, or permissive
    safety_allow_override: bool = True  # Allow force_deploy override
    safety_min_score: int = 60  # Minimum safety score for moderate level
    
    # Natural Language Generation (AI1.21)
    nl_generation_enabled: bool = True
    nl_model: str = "gpt-4o-mini"  # OpenAI model for NL generation
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

    expert_mode_blocked_services: List[str] = [
        "shell_command",
        "python_script",
        "script.turn_on",
        "automation.reload",
        "homeassistant.restart",
        "homeassistant.stop"
    ]
    """Services blocked in expert mode unless allow_dangerous_operations=true"""

    expert_mode_require_approval_services: List[str] = [
        "notify",
        "camera",
        "lock",
        "cover",
        "climate"
    ]
    """Services that require explicit user confirmation before deployment"""

    class Config:
        env_file = "infrastructure/env.ai-automation"
        case_sensitive = False


# Global settings instance
settings = Settings()

