"""Configuration for API Automation Edge Service."""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_name: str = "api-automation-edge"
    service_port: int = 8025

    # Home Assistant configuration
    ha_url: str | None = None
    ha_token: str | None = None
    ha_http_url: str | None = None
    ha_ws_url: str | None = None

    # Home ID
    home_id: str = "default"

    # Retry configuration
    max_retries: int = 3
    retry_delay: float = 1.0
    timeout: float = 10.0

    # Circuit breaker configuration
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: float = 60.0

    # WebSocket configuration
    ws_ping_interval: int = 20
    ws_ping_timeout: int = 10
    ws_reconnect_delay: float = 5.0
    ws_max_reconnect_attempts: int = 10

    # Capability graph configuration
    capability_graph_refresh_interval: int = 3600
    capability_graph_ttl: int = 86400

    # Idempotency configuration
    idempotency_ttl: int = 3600

    # Huey Task Queue configuration
    huey_database_path: str = "./data/automation_queue.db"
    huey_workers: int = 4
    huey_result_ttl: int = Field(default=604800, description="7 days")
    huey_scheduler_interval: float = 1.0
    use_task_queue: bool = True


settings = Settings()
