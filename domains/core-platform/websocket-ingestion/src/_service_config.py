"""Environment-based configuration for the WebSocket Ingestion Service.

Thin backward-compatible wrapper around ``config.Settings``
(BaseServiceSettings subclass). Existing code that uses
``ServiceConfig`` continues to work without changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import settings


@dataclass(slots=True)
class ServiceConfig:
    """All tunables — delegates to the shared ``settings`` instance.

    Fields are initialised from the pydantic ``Settings`` model so that
    any environment variables, ``.env`` files, or defaults defined in
    ``config.py`` are respected.
    """

    # Home Assistant connection
    home_assistant_url: str | None = field(
        default_factory=lambda: settings.resolved_ha_http_url
    )
    home_assistant_ws_url: str | None = field(
        default_factory=lambda: settings.resolved_ha_ws_url
    )
    home_assistant_token: str | None = field(
        default_factory=lambda: settings.resolved_ha_token
    )

    # Nabu Casa fallback
    nabu_casa_url: str | None = field(default_factory=lambda: settings.nabu_casa_url)
    nabu_casa_token: str | None = field(default_factory=lambda: settings.nabu_casa_token)

    home_assistant_enabled: bool = field(
        default_factory=lambda: settings.enable_home_assistant
    )

    # High-volume processing
    max_workers: int = field(default_factory=lambda: settings.max_workers)
    processing_rate_limit: int = field(default_factory=lambda: settings.processing_rate_limit)
    batch_size: int = field(default_factory=lambda: settings.batch_size)
    batch_timeout: float = field(default_factory=lambda: settings.batch_timeout)
    max_memory_mb: int = field(default_factory=lambda: settings.max_memory_mb)

    # InfluxDB
    influxdb_url: str = field(default_factory=lambda: settings.influxdb_url)
    influxdb_token: str | None = field(
        default_factory=lambda: settings.influxdb_token.get_secret_value() if settings.influxdb_token else None
    )
    influxdb_org: str = field(default_factory=lambda: settings.influxdb_org)
    influxdb_bucket: str = field(default_factory=lambda: settings.influxdb_bucket)
    influxdb_max_pending_points: int = field(
        default_factory=lambda: settings.influxdb_max_pending_points
    )
    influxdb_overflow_strategy: str = field(
        default_factory=lambda: settings.influxdb_overflow_strategy
    )
