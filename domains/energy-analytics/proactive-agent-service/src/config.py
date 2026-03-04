"""Configuration management for Proactive Agent Service."""

from __future__ import annotations

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_name: str = "proactive-agent-service"
    service_port: int = 8031

    # HA AI Agent Service Configuration
    ha_ai_agent_url: str = Field(
        default="http://ha-ai-agent-service:8030",
        description="HA AI Agent Service URL",
    )
    ha_ai_agent_timeout: int = 30
    ha_ai_agent_max_retries: int = 3

    # External Data Service URLs
    weather_api_url: str = Field(
        default="http://weather-api:8009",
        description="Weather API service URL",
    )
    # Note: Sports data is accessed via data-api (Epic 31 architecture)
    carbon_intensity_url: str = Field(
        default="http://carbon-intensity:8010",
        description="Carbon Intensity service URL",
    )

    # Scheduler Configuration
    scheduler_enabled: bool = True
    scheduler_time: str = "03:00"
    scheduler_timezone: str = "America/Los_Angeles"

    # Scheduled Tasks (Epic 27)
    cron_scheduler_enabled: bool = Field(
        default=True,
        description="Enable the cron task scheduler for scheduled AI tasks",
    )
    ha_device_control_notify_url: str = Field(
        default="http://ha-ai-agent-service:8030/api/notify",
        description="Notification endpoint for task results (Story 27.5)",
    )

    # OpenAI Configuration (for prompt generation)
    openai_api_key: str | None = Field(
        default=None,
        description="OpenAI API key for prompt generation",
    )
    openai_model: str = Field(
        default="gpt-5-mini",
        description="OpenAI model for prompt generation",
    )
    openai_timeout: int = Field(
        default=30,
        description="OpenAI API timeout in seconds",
    )

