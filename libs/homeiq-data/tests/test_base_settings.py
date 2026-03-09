"""Tests for BaseServiceSettings.

Covers:
  - Default values
  - effective_database_url property
  - CORS origins parsing
  - Subclassing with extra fields
"""

from __future__ import annotations

from pydantic import ConfigDict

from homeiq_data.base_settings import BaseServiceSettings


class _IsolatedSettings(BaseServiceSettings):
    """Subclass that ignores .env file for testing defaults."""
    model_config = ConfigDict(env_file=None)


class TestBaseServiceSettings:
    def test_defaults(self, monkeypatch) -> None:
        # Clear env vars that override defaults
        for var in ("INFLUXDB_URL", "DATA_API_URL", "POSTGRES_URL", "DATABASE_URL",
                    "INFLUXDB_TOKEN", "INFLUXDB_ORG", "INFLUXDB_BUCKET",
                    "SERVICE_NAME", "SERVICE_PORT", "LOG_LEVEL",
                    "DATA_API_KEY", "DATABASE_SCHEMA", "CORS_ORIGINS"):
            monkeypatch.delenv(var, raising=False)
        settings = _IsolatedSettings()
        assert settings.service_name == "homeiq-service"
        assert settings.service_port == 8000
        assert settings.log_level == "INFO"
        assert settings.data_api_url == "http://data-api:8006"
        assert settings.influxdb_url == "http://influxdb:8086"
        assert settings.influxdb_org == "homeiq"
        assert settings.influxdb_bucket == "home_assistant_events"
        assert settings.postgres_url == ""
        assert settings.database_url == ""
        assert settings.database_schema == "public"
        assert settings.cors_origins is None

    def test_effective_database_url_prefers_postgres(self) -> None:
        settings = BaseServiceSettings(
            postgres_url="postgresql://pg:5432/db",
            database_url="postgresql://fallback:5432/db",
        )
        assert settings.effective_database_url == "postgresql://pg:5432/db"

    def test_effective_database_url_falls_back(self) -> None:
        settings = BaseServiceSettings(
            postgres_url="",
            database_url="postgresql://fallback:5432/db",
        )
        assert settings.effective_database_url == "postgresql://fallback:5432/db"

    def test_cors_origins_parsing(self) -> None:
        settings = BaseServiceSettings(cors_origins="http://localhost:3000, http://myapp.com")
        origins = settings.get_cors_origins_list()
        assert origins == ["http://localhost:3000", "http://myapp.com"]

    def test_cors_origins_default_wildcard(self) -> None:
        settings = BaseServiceSettings()
        assert settings.get_cors_origins_list() == ["*"]

    def test_subclassing(self) -> None:
        class MySettings(BaseServiceSettings):
            scheduler_enabled: bool = True
            min_confidence: float = 0.6

        settings = MySettings(service_name="my-svc", service_port=8080)
        assert settings.service_name == "my-svc"
        assert settings.service_port == 8080
        assert settings.scheduler_enabled is True
        assert settings.min_confidence == 0.6
        # Inherited fields still work
        assert settings.data_api_url == "http://data-api:8006"
