"""Service configuration for automation-trace-service.

Uses BaseServiceSettings for common fields while exposing module-level
constants for backward compatibility with ha_client, influxdb_writer,
and trace_poller modules that import ``config.CONSTANT_NAME``.
"""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables."""

    # Override base defaults
    service_port: int = 8020
    service_name: str = "automation-trace-service"

    # Home Assistant connection
    ha_ws_url: str = Field(default="ws://homeassistant:8123", description="HA WebSocket URL")
    ha_http_url: str = Field(default="http://homeassistant:8123", description="HA HTTP URL")
    ha_token: str = Field(default="", description="HA long-lived access token")

    # InfluxDB write retries
    influxdb_write_retries: int = Field(default=3, description="InfluxDB write retry count")

    # Polling intervals
    trace_poll_interval_seconds: int = Field(default=120, description="Trace poll interval in seconds")
    logbook_poll_interval_seconds: int = Field(default=300, description="Logbook poll interval in seconds")
    logbook_lookback_minutes: int = Field(default=10, description="Logbook lookback window in minutes")

    # Data API key (service-specific env var name)
    data_api_api_key: str = Field(default="", description="Data API bearer token")


settings = Settings()

# ---------------------------------------------------------------------------
# Module-level constants for backward compatibility
# ---------------------------------------------------------------------------
# ha_client.py, influxdb_writer.py, trace_poller.py import these as
# ``from . import config`` then ``config.HA_WS_URL``, etc.

HA_WS_URL = settings.ha_ws_url
HA_HTTP_URL = settings.ha_http_url
HA_TOKEN = settings.ha_token

INFLUXDB_URL = settings.influxdb_url
INFLUXDB_TOKEN = settings.influxdb_token.get_secret_value() if settings.influxdb_token else ""
INFLUXDB_ORG = settings.influxdb_org
INFLUXDB_BUCKET = settings.influxdb_bucket
INFLUXDB_WRITE_RETRIES = settings.influxdb_write_retries

DATA_API_URL = settings.data_api_url
DATA_API_API_KEY = settings.data_api_api_key or (
    settings.data_api_key.get_secret_value() if settings.data_api_key else ""
)

TRACE_POLL_INTERVAL_SECONDS = settings.trace_poll_interval_seconds
LOGBOOK_POLL_INTERVAL_SECONDS = settings.logbook_poll_interval_seconds
LOGBOOK_LOOKBACK_MINUTES = settings.logbook_lookback_minutes

SERVICE_PORT = settings.service_port
SERVICE_NAME = settings.service_name
LOG_LEVEL = settings.log_level
