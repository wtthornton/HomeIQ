"""Service configuration via environment variables"""

import os

from dotenv import load_dotenv

load_dotenv()


# Home Assistant connection
HA_WS_URL = os.getenv("HA_WS_URL", "ws://homeassistant:8123")
HA_HTTP_URL = os.getenv("HA_HTTP_URL", "http://homeassistant:8123")
HA_TOKEN = os.getenv("HA_TOKEN", "")

# InfluxDB
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://influxdb:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "homeiq")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
INFLUXDB_WRITE_RETRIES = int(os.getenv("INFLUXDB_WRITE_RETRIES", "3"))

# data-api
DATA_API_URL = os.getenv("DATA_API_URL", "http://data-api:8006")
DATA_API_API_KEY = os.getenv("DATA_API_API_KEY", "")

# Polling intervals
TRACE_POLL_INTERVAL_SECONDS = int(os.getenv("TRACE_POLL_INTERVAL_SECONDS", "120"))
LOGBOOK_POLL_INTERVAL_SECONDS = int(os.getenv("LOGBOOK_POLL_INTERVAL_SECONDS", "300"))
LOGBOOK_LOOKBACK_MINUTES = int(os.getenv("LOGBOOK_LOOKBACK_MINUTES", "10"))

# Service
SERVICE_PORT = int(os.getenv("SERVICE_PORT", "8020"))
SERVICE_NAME = "automation-trace-service"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
