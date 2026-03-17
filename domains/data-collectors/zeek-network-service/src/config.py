"""Configuration settings for Zeek Network Intelligence Service."""

from homeiq_data import BaseServiceSettings
from pydantic import SecretStr


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8048
    service_name: str = "zeek-network-service"
    influxdb_bucket: str = "home_assistant_events"

    # Zeek log directory (shared volume mount)
    zeek_log_dir: str = "/zeek/logs"

    # Polling intervals
    poll_interval_seconds: int = 30
    device_metrics_interval_seconds: int = 60

    # State persistence (seek offsets for log file tracking)
    state_dir: str = "/app/state"

    # InfluxDB buffer settings
    influx_buffer_max_seconds: int = 300  # 5 min max in-memory buffer

    # InfluxDB write retries
    influxdb_write_retries: int = 3

    # InfluxDB fallback hostnames for DNS resilience
    influxdb_fallback_hosts: str = "influxdb,homeiq-influxdb,localhost"

    # PostgreSQL schema for device metadata
    database_schema: str = "devices"

    # Data API for cross-service feeds
    data_api_url: str = "http://data-api:8006"
    data_api_key: SecretStr | None = None

    # Phase 4 — Anomaly detection thresholds
    beacon_jitter_threshold: float = 5.0  # seconds — max std_dev for beaconing
    beacon_min_connections: int = 20  # minimum connections to flag beaconing
    beacon_min_duration: int = 3600  # seconds — minimum beaconing persistence (1h)
    beaconing_check_interval_seconds: int = 300  # run beaconing analysis every 5 min

    # Cross-service feed URLs
    proactive_agent_url: str = "http://proactive-agent-service:8046"
    ai_pattern_url: str = "http://ai-pattern-service:8040"


settings = Settings()
