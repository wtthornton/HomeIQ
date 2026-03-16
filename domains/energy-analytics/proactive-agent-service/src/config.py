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

    # Memory Brain Configuration (Story 33.4)
    memory_enabled: bool = Field(
        default=True,
        description="Enable memory-aware proactive suggestions",
    )
    memory_database_url: str | None = Field(
        default=None,
        description="PostgreSQL URL for Memory Brain (uses postgres_dsn if not set)",
    )
    memory_min_confidence: float = Field(
        default=0.3,
        description="Minimum confidence threshold for memory retrieval",
    )

    # Epic 68: Autonomous Agent Upgrade
    # Observe-Reason-Act loop
    agent_loop_enabled: bool = Field(
        default=True,
        description="Enable observe-reason-act agent loop (Epic 68)",
    )
    agent_loop_interval_minutes: int = Field(
        default=15,
        description="Interval between observe-reason-act cycles (minutes)",
    )

    # ha-device-control for autonomous execution (Story 68.4)
    ha_device_control_url: str = Field(
        default="http://ha-device-control:8040",
        description="HA Device Control service URL for autonomous execution",
    )
    ha_device_control_timeout: int = Field(
        default=10,
        description="Timeout for ha-device-control calls (seconds)",
    )

    # Confidence & risk thresholds (Story 68.3)
    auto_execute_confidence_threshold: int = Field(
        default=85,
        description="Minimum confidence (0-100) to auto-execute an action",
    )
    suggest_confidence_threshold: int = Field(
        default=50,
        description="Minimum confidence (0-100) to surface as suggestion",
    )
    suppress_confidence_threshold: int = Field(
        default=30,
        description="Below this confidence, suppress the suggestion entirely",
    )

    # Safety guardrails (Story 68.6)
    autonomous_execution_enabled: bool = Field(
        default=True,
        description="Master switch for autonomous execution",
    )
    safety_blocked_domains: str = Field(
        default="lock,alarm,camera",
        description="Comma-separated HA entity domains that can never be auto-executed",
    )
    quiet_hours_start: str = Field(
        default="23:00",
        description="Start of quiet hours (no autonomous actions)",
    )
    quiet_hours_end: str = Field(
        default="06:00",
        description="End of quiet hours",
    )
    undo_window_minutes: int = Field(
        default=15,
        description="Time window (minutes) for undoing autonomous actions",
    )

