"""Configuration management for Proactive Agent Service"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment"""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    # Service Configuration
    service_name: str = "proactive-agent-service"
    service_port: int = 8031

    # HA AI Agent Service Configuration
    ha_ai_agent_url: str = Field(
        default="http://ha-ai-agent-service:8030",
        description="HA AI Agent Service URL"
    )
    ha_ai_agent_timeout: int = 30  # Request timeout in seconds
    ha_ai_agent_max_retries: int = 3  # Maximum retry attempts

    # External Data Service URLs
    weather_api_url: str = Field(
        default="http://weather-api:8009",
        description="Weather API service URL"
    )
    # Note: Sports data is accessed via data-api (Epic 31 architecture)
    # The sports-api service writes directly to InfluxDB, and data-api queries it
    carbon_intensity_url: str = Field(
        default="http://carbon-intensity:8010",
        description="Carbon Intensity service URL"
    )
    data_api_url: str = Field(
        default="http://data-api:8006",
        description="Data API service URL"
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/proactive_agent.db",
        description="SQLite database URL for suggestions storage"
    )

    # Scheduler Configuration
    scheduler_enabled: bool = True
    scheduler_time: str = "03:00"  # 3 AM daily batch job
    scheduler_timezone: str = "America/Los_Angeles"

    # OpenAI Configuration (for prompt generation)
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for prompt generation"
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model for prompt generation"
    )
    openai_timeout: int = Field(
        default=30,
        description="OpenAI API timeout in seconds"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")

