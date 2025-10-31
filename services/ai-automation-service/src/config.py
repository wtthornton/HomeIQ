"""Configuration management for AI Automation Service"""

from pydantic_settings import BaseSettings
from typing import Optional


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
    
    class Config:
        env_file = "infrastructure/env.ai-automation"
        case_sensitive = False


# Global settings instance
settings = Settings()

