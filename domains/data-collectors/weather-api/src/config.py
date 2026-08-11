"""Configuration settings for Weather API Service."""

from homeiq_data import BaseServiceSettings


class Settings(BaseServiceSettings):
    """Application settings loaded from environment variables.

    Inherits common fields (service_name, service_port, log_level,
    data_api_url, influxdb_*, postgres_*, cors_origins) from
    BaseServiceSettings.
    """

    # Override base defaults
    service_port: int = 8009
    service_name: str = "weather-api"
    # influxdb_bucket is deliberately NOT overridden: BaseServiceSettings
    # already defaults it to `home_assistant_events`, the bucket that exists.
    # This class used to pin it to `weather_data`, which was never provisioned,
    # so writes had nowhere to land whenever the environment did not happen to
    # supply INFLUXDB_BUCKET.

    # Open-Meteo configuration. Open-Meteo's non-commercial tier needs no API
    # key, so there is no credential to lose or rotate here. It is queried by
    # coordinate, not city name; weather_location is kept as the display label
    # reported back to callers and written as the InfluxDB `location` tag.
    # Named for the provider, not generically: a stale WEATHER_API_URL left in
    # .env from the OpenWeatherMap era would otherwise override this through
    # env_file and silently repoint the service at a provider it can no longer
    # authenticate against.
    open_meteo_forecast_url: str = "https://api.open-meteo.com/v1/forecast"
    weather_location: str = "Las Vegas"
    weather_latitude: float = 35.9561663
    weather_longitude: float = -115.1833246

    # Cache
    cache_ttl_seconds: int = 900

    # InfluxDB write retries
    influxdb_write_retries: int = 3

    # InfluxDB fallback hostnames for DNS resilience
    influxdb_fallback_hosts: str = "influxdb,homeiq-influxdb,localhost"


settings = Settings()
