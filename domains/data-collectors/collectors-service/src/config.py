"""Merged configuration for the collectors service.

Combines the six retired services' ``Settings`` classes (weather-api,
sports-api, air-quality-service, electricity-pricing-service,
calendar-service, smart-meter-service) into one, per TAP-7274 section C1.

Fields that were already shared across services under one name
(``HOME_ASSISTANT_URL``/``HOME_ASSISTANT_TOKEN``, ``HA_HTTP_URL``/``HA_TOKEN``,
``INFLUXDB_*``) keep their original env var names unchanged — six containers
reading the same ``.env`` value already made them one shared setting in
practice; one process makes that literal.

Fields whose names collided only by accident once merged into one process —
``fetch_interval``/``cache_duration`` (air-quality and electricity-pricing
each declared their own) and bare ``latitude``/``longitude``
(air-quality) — are renamed below with an adapter prefix so each keeps an
independently configurable env var instead of silently sharing one. See
``docs/architecture/collapse-map.md`` section C1 for the rename list.
"""

from homeiq_data import BaseServiceSettings
from pydantic import Field


class Settings(BaseServiceSettings):
    """Application settings for the merged collectors service."""

    service_name: str = "collectors"
    service_port: int = 8009

    # --- weather adapter (former weather-api) ---
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_location: str = "Las Vegas"
    weather_latitude: float = 35.9561663
    weather_longitude: float = -115.1833246
    cache_ttl_seconds: int = 900
    influxdb_write_retries: int = 3
    influxdb_fallback_hosts: str = "influxdb,homeiq-influxdb,localhost"

    # --- sports adapter (former sports-api) ---
    sports_poll_interval: int = 60
    sports_api_key: str = ""

    # --- air-quality adapter (former air-quality-service) ---
    # Renamed from bare LATITUDE/LONGITUDE/FETCH_INTERVAL/CACHE_DURATION,
    # which collided with electricity-pricing's identically named fields.
    air_quality_api_url: str = Field(
        default="https://air-quality-api.open-meteo.com/v1/air-quality",
        description="Open-Meteo air-quality endpoint",
    )
    air_quality_latitude: str = Field(default="36.1699")
    air_quality_longitude: str = Field(default="-115.1398")
    air_quality_fetch_interval: int = Field(default=3600)
    air_quality_cache_duration_minutes: int = Field(default=60)

    # --- electricity-pricing adapter (former electricity-pricing-service) ---
    # fetch_interval/cache_duration renamed for the same reason as above.
    pricing_provider: str = Field(default="awattar")
    electricity_fetch_interval: int = Field(default=3600)
    electricity_cache_duration_minutes: int = Field(default=60)
    allowed_networks: str | None = Field(default=None)

    # --- calendar adapter (former calendar-service) ---
    calendar_entities: str = "calendar.primary"
    calendar_fetch_interval: int = 900
    calendar_timezone: str = "UTC"
    default_travel_time_minutes: int = 30
    # calendar wrote to the "events" bucket while the other five (and the
    # BaseServiceSettings default) use "home_assistant_events" — kept as its
    # own field rather than overriding the shared influxdb_bucket.
    calendar_influxdb_bucket: str = "events"

    # --- smart-meter adapter (already adapter-shaped; unchanged) ---
    meter_type: str = "home_assistant"
    meter_api_token: str = ""
    meter_device_id: str = ""
    fetch_interval_seconds: int = 300

    # --- shared Home Assistant connection (unprefixed across all six already) ---
    home_assistant_url: str | None = None
    home_assistant_token: str | None = None
    ha_http_url: str | None = None
    ha_token: str | None = None


settings = Settings()
