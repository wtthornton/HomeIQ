"""Environment-based configuration for the WebSocket Ingestion Service."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env(key: str, default: str | None = None) -> str | None:
    """Read an environment variable with an optional default."""
    return os.getenv(key, default)


def _env_int(key: str, default: str) -> int:
    return int(os.getenv(key, default))


def _env_float(key: str, default: str) -> float:
    return float(os.getenv(key, default))


@dataclass(slots=True)
class ServiceConfig:
    """All tunables read from environment variables at service init time."""

    # Home Assistant connection (supports old + new variable names)
    home_assistant_url: str | None = field(
        default_factory=lambda: _env('HA_HTTP_URL') or _env('HOME_ASSISTANT_URL')
    )
    home_assistant_ws_url: str | None = field(
        default_factory=lambda: _env('HA_WS_URL') or _env('HA_URL')
    )
    home_assistant_token: str | None = field(
        default_factory=lambda: _env('HA_TOKEN') or _env('HOME_ASSISTANT_TOKEN')
    )

    # Nabu Casa fallback
    nabu_casa_url: str | None = field(default_factory=lambda: _env('NABU_CASA_URL'))
    nabu_casa_token: str | None = field(default_factory=lambda: _env('NABU_CASA_TOKEN'))

    home_assistant_enabled: bool = field(
        default_factory=lambda: (_env('ENABLE_HOME_ASSISTANT', 'true') or '').lower() == 'true'
    )

    # High-volume processing
    max_workers: int = field(default_factory=lambda: _env_int('MAX_WORKERS', '10'))
    processing_rate_limit: int = field(default_factory=lambda: _env_int('PROCESSING_RATE_LIMIT', '1000'))
    batch_size: int = field(default_factory=lambda: _env_int('BATCH_SIZE', '100'))
    batch_timeout: float = field(default_factory=lambda: _env_float('BATCH_TIMEOUT', '5.0'))
    max_memory_mb: int = field(default_factory=lambda: _env_int('MAX_MEMORY_MB', '1024'))

    # InfluxDB
    influxdb_url: str = field(default_factory=lambda: _env('INFLUXDB_URL', 'http://influxdb:8086') or '')
    influxdb_token: str | None = field(default_factory=lambda: _env('INFLUXDB_TOKEN'))
    influxdb_org: str = field(default_factory=lambda: _env('INFLUXDB_ORG', 'homeassistant') or '')
    influxdb_bucket: str = field(default_factory=lambda: _env('INFLUXDB_BUCKET', 'home_assistant_events') or '')
    influxdb_max_pending_points: int = field(default_factory=lambda: _env_int('INFLUXDB_MAX_PENDING_POINTS', '20000'))
    influxdb_overflow_strategy: str = field(
        default_factory=lambda: (_env('INFLUXDB_OVERFLOW_STRATEGY', 'drop_oldest') or '').lower()
    )
