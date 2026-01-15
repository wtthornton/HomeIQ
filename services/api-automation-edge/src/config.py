"""
Configuration for API Automation Edge Service
"""

import os
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # Service configuration
    service_name: str = "api-automation-edge"
    service_port: int = int(os.getenv("SERVICE_PORT", "8025"))
    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Home Assistant configuration
    ha_url: Optional[str] = os.getenv("HA_URL") or os.getenv("HOME_ASSISTANT_URL")
    ha_token: Optional[str] = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
    ha_http_url: Optional[str] = os.getenv("HA_HTTP_URL")
    ha_ws_url: Optional[str] = os.getenv("HA_WS_URL")
    
    # Home ID
    home_id: str = os.getenv("HOME_ID", "default")
    
    # Database configuration (synchronous SQLite for SQLAlchemy)
    database_url: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///./api-automation-edge.db"
    )
    
    # InfluxDB configuration (for metrics)
    influxdb_url: Optional[str] = os.getenv("INFLUXDB_URL")
    influxdb_token: Optional[str] = os.getenv("INFLUXDB_TOKEN")
    influxdb_org: Optional[str] = os.getenv("INFLUXDB_ORG")
    influxdb_bucket: Optional[str] = os.getenv("INFLUXDB_BUCKET", "homeiq_metrics")
    
    # Retry configuration
    max_retries: int = int(os.getenv("MAX_RETRIES", "3"))
    retry_delay: float = float(os.getenv("RETRY_DELAY", "1.0"))
    timeout: float = float(os.getenv("TIMEOUT", "10.0"))
    
    # Circuit breaker configuration
    circuit_breaker_failure_threshold: int = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "5"))
    circuit_breaker_timeout: float = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "60.0"))
    
    # WebSocket configuration
    ws_ping_interval: int = int(os.getenv("WS_PING_INTERVAL", "20"))
    ws_ping_timeout: int = int(os.getenv("WS_PING_TIMEOUT", "10"))
    ws_reconnect_delay: float = float(os.getenv("WS_RECONNECT_DELAY", "5.0"))
    ws_max_reconnect_attempts: int = int(os.getenv("WS_MAX_RECONNECT_ATTEMPTS", "10"))
    
    # Capability graph configuration
    capability_graph_refresh_interval: int = int(os.getenv("CAPABILITY_GRAPH_REFRESH_INTERVAL", "3600"))
    capability_graph_ttl: int = int(os.getenv("CAPABILITY_GRAPH_TTL", "86400"))
    
    # Idempotency configuration
    idempotency_ttl: int = int(os.getenv("IDEMPOTENCY_TTL", "3600"))
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
