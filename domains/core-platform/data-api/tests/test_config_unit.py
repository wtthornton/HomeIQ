"""Unit tests for config.py and config_manager.py — Story 85.8

Tests Settings construction, ConfigManager CRUD, validation, and sanitization.
"""

import os
import tempfile
from pathlib import Path

import pytest

from src.config_manager import ConfigManager, MASK_VALUE, SENSITIVE_KEY_PATTERNS


# ---------------------------------------------------------------------------
# Settings — tested via monkeypatch (Story 85.8)
# ---------------------------------------------------------------------------

class TestSettings:
    """Test Settings (BaseServiceSettings subclass) construction."""

    def test_settings_with_api_key(self, monkeypatch):
        monkeypatch.setenv("DATA_API_API_KEY", "test-secret-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
        # Force re-import to pick up new env
        from src.config import Settings
        s = Settings()
        assert s.api_key == "test-secret-key"

    def test_settings_anonymous_generates_key(self, monkeypatch):
        monkeypatch.delenv("DATA_API_API_KEY", raising=False)
        monkeypatch.delenv("DATA_API_KEY", raising=False)
        monkeypatch.setenv("DATA_API_ALLOW_ANONYMOUS", "true")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
        from src.config import Settings
        s = Settings()
        assert s.api_key is not None
        assert len(s.api_key) > 10

    def test_settings_no_key_no_anonymous_raises(self, monkeypatch):
        monkeypatch.delenv("DATA_API_API_KEY", raising=False)
        monkeypatch.delenv("DATA_API_KEY", raising=False)
        monkeypatch.delenv("DATA_API_ALLOW_ANONYMOUS", raising=False)
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
        from src.config import Settings
        with pytest.raises(ValueError, match="DATA_API_API_KEY must be set"):
            Settings(allow_anonymous=False)

    def test_settings_defaults(self, monkeypatch):
        monkeypatch.setenv("DATA_API_API_KEY", "key")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
        from src.config import Settings
        s = Settings()
        assert s.service_port == 8006
        assert s.service_name == "data-api"
        assert s.rate_limit_per_min == 100
        assert s.rate_limit_burst == 20
        assert s.request_timeout == 30
        assert s.db_query_timeout == 10

    def test_settings_resolves_data_api_key_fallback(self, monkeypatch):
        monkeypatch.delenv("DATA_API_API_KEY", raising=False)
        monkeypatch.setenv("DATA_API_KEY", "fallback-key")
        monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
        from src.config import Settings
        s = Settings()
        assert s.api_key == "fallback-key"


# ---------------------------------------------------------------------------
# ConfigManager — CRUD and validation
# ---------------------------------------------------------------------------

class TestConfigManagerReadWrite:

    def _make_manager(self, tmp_path):
        return ConfigManager(config_dir=str(tmp_path))

    def test_list_services_empty(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        assert mgr.list_services() == []

    def test_list_services_finds_env_files(self, tmp_path):
        (tmp_path / ".env.websocket").write_text("HA_URL=ws://localhost\n")
        (tmp_path / ".env.weather").write_text("KEY=val\n")
        (tmp_path / ".env.example").write_text("# template\n")  # should be skipped
        mgr = self._make_manager(tmp_path)
        services = mgr.list_services()
        assert "websocket" in services
        assert "weather" in services
        assert "example" not in services

    def test_list_services_sorted(self, tmp_path):
        (tmp_path / ".env.zebra").write_text("X=1\n")
        (tmp_path / ".env.alpha").write_text("X=1\n")
        mgr = self._make_manager(tmp_path)
        assert mgr.list_services() == ["alpha", "zebra"]

    def test_read_config_valid_file(self, tmp_path):
        (tmp_path / ".env.test").write_text("KEY1=value1\nKEY2=value2\n")
        mgr = self._make_manager(tmp_path)
        config = mgr.read_config("test")
        assert config == {"KEY1": "value1", "KEY2": "value2"}

    def test_read_config_skips_comments(self, tmp_path):
        (tmp_path / ".env.test").write_text("# comment\nKEY=val\n")
        mgr = self._make_manager(tmp_path)
        config = mgr.read_config("test")
        assert config == {"KEY": "val"}

    def test_read_config_skips_blank_lines(self, tmp_path):
        (tmp_path / ".env.test").write_text("\n\nKEY=val\n\n")
        mgr = self._make_manager(tmp_path)
        assert mgr.read_config("test") == {"KEY": "val"}

    def test_read_config_file_not_found(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.read_config("nonexistent")

    def test_write_config_updates_existing(self, tmp_path):
        (tmp_path / ".env.test").write_text("KEY1=old\nKEY2=keep\n")
        mgr = self._make_manager(tmp_path)
        mgr.allow_secret_writes = True
        result = mgr.write_config("test", {"KEY1": "new"})
        assert result["KEY1"] == "new"
        assert result["KEY2"] == "keep"

    def test_write_config_adds_new_keys(self, tmp_path):
        (tmp_path / ".env.test").write_text("KEY1=val\n")
        mgr = self._make_manager(tmp_path)
        mgr.allow_secret_writes = True
        result = mgr.write_config("test", {"NEW_KEY": "new_val"})
        assert result["NEW_KEY"] == "new_val"
        assert result["KEY1"] == "val"

    def test_write_config_blocks_sensitive_keys(self, tmp_path):
        (tmp_path / ".env.test").write_text("HA_TOKEN=old\n")
        mgr = self._make_manager(tmp_path)
        mgr.allow_secret_writes = False
        with pytest.raises(PermissionError, match="sensitive"):
            mgr.write_config("test", {"HA_TOKEN": "new"})

    def test_write_config_file_not_found_no_create(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        with pytest.raises(FileNotFoundError):
            mgr.write_config("nonexistent", {"KEY": "val"})

    def test_write_config_create_if_missing(self, tmp_path):
        mgr = self._make_manager(tmp_path)
        mgr.allow_secret_writes = True
        result = mgr.write_config("new_svc", {"KEY": "val"}, create_if_missing=True)
        assert result["KEY"] == "val"


class TestConfigManagerValidation:

    def _mgr(self):
        return ConfigManager(config_dir="nonexistent")

    def test_websocket_valid(self):
        result = self._mgr().validate_config("websocket", {
            "HA_URL": "ws://192.168.1.86:8123",
            "HA_TOKEN": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        })
        assert result["valid"] is True
        assert result["errors"] == []

    def test_websocket_missing_url(self):
        result = self._mgr().validate_config("websocket", {"HA_TOKEN": "longtoken123"})
        assert result["valid"] is False
        assert any("HA_URL" in e for e in result["errors"])

    def test_websocket_invalid_url_scheme(self):
        result = self._mgr().validate_config("websocket", {
            "HA_URL": "http://wrong",
            "HA_TOKEN": "longtoken123"
        })
        assert any("ws://" in e for e in result["errors"])

    def test_websocket_short_token_warning(self):
        result = self._mgr().validate_config("websocket", {
            "HA_URL": "ws://localhost",
            "HA_TOKEN": "short"
        })
        assert any("short" in w for w in result["warnings"])

    def test_weather_valid(self):
        result = self._mgr().validate_config("weather", {
            "WEATHER_API_KEY": "abc123",
            "WEATHER_LAT": "51.5",
            "WEATHER_LON": "-0.12"
        })
        assert result["valid"] is True

    def test_weather_invalid_lat(self):
        result = self._mgr().validate_config("weather", {
            "WEATHER_API_KEY": "abc",
            "WEATHER_LAT": "999"
        })
        assert any("LAT" in e for e in result["errors"])

    def test_weather_invalid_lon(self):
        result = self._mgr().validate_config("weather", {
            "WEATHER_API_KEY": "abc",
            "WEATHER_LON": "-999"
        })
        assert any("LON" in e for e in result["errors"])

    def test_influxdb_valid(self):
        result = self._mgr().validate_config("influxdb", {
            "INFLUXDB_URL": "http://influxdb:8086",
            "INFLUXDB_TOKEN": "token",
            "INFLUXDB_ORG": "homeiq",
            "INFLUXDB_BUCKET": "events"
        })
        assert result["valid"] is True

    def test_influxdb_missing_fields(self):
        result = self._mgr().validate_config("influxdb", {})
        assert result["valid"] is False
        assert len(result["errors"]) >= 4

    def test_unknown_service_no_validation(self):
        result = self._mgr().validate_config("unknown", {})
        assert result["valid"] is True

    def test_websocket_missing_token(self):
        result = self._mgr().validate_config("websocket", {
            "HA_URL": "ws://localhost"
        })
        assert any("HA_TOKEN" in e for e in result["errors"])

    def test_weather_missing_key(self):
        result = self._mgr().validate_config("weather", {})
        assert any("WEATHER_API_KEY" in e for e in result["errors"])

    def test_weather_non_numeric_lat(self):
        result = self._mgr().validate_config("weather", {
            "WEATHER_API_KEY": "abc",
            "WEATHER_LAT": "not_a_number"
        })
        assert any("number" in e.lower() for e in result["errors"])

    def test_weather_non_numeric_lon(self):
        result = self._mgr().validate_config("weather", {
            "WEATHER_API_KEY": "abc",
            "WEATHER_LON": "not_a_number"
        })
        assert any("number" in e.lower() for e in result["errors"])

    def test_influxdb_invalid_url_scheme(self):
        result = self._mgr().validate_config("influxdb", {
            "INFLUXDB_URL": "ftp://wrong",
            "INFLUXDB_TOKEN": "token",
            "INFLUXDB_ORG": "org",
            "INFLUXDB_BUCKET": "bucket"
        })
        assert any("http" in e.lower() for e in result["errors"])


class TestConfigManagerSanitize:

    def test_masks_sensitive_keys(self):
        mgr = ConfigManager(config_dir=".")
        config = {"HA_TOKEN": "secret123", "HA_URL": "ws://localhost"}
        sanitized = mgr.sanitize_config(config)
        assert sanitized["HA_TOKEN"] == MASK_VALUE
        assert sanitized["HA_URL"] == "ws://localhost"

    def test_masks_api_key(self):
        mgr = ConfigManager(config_dir=".")
        config = {"DATA_API_KEY": "key123"}
        assert mgr.sanitize_config(config)["DATA_API_KEY"] == MASK_VALUE

    def test_masks_password(self):
        mgr = ConfigManager(config_dir=".")
        config = {"DB_PASSWORD": "pass123"}
        assert mgr.sanitize_config(config)["DB_PASSWORD"] == MASK_VALUE

    def test_empty_value_not_masked(self):
        mgr = ConfigManager(config_dir=".")
        config = {"HA_TOKEN": ""}
        assert mgr.sanitize_config(config)["HA_TOKEN"] == ""

    def test_non_sensitive_keys_unchanged(self):
        mgr = ConfigManager(config_dir=".")
        config = {"PORT": "8080", "HOST": "localhost"}
        sanitized = mgr.sanitize_config(config)
        assert sanitized["PORT"] == "8080"
        assert sanitized["HOST"] == "localhost"


class TestConfigManagerTemplate:

    def test_websocket_template(self):
        mgr = ConfigManager(config_dir=".")
        template = mgr.get_config_template("websocket")
        assert "HA_URL" in template
        assert "HA_TOKEN" in template
        assert template["HA_TOKEN"]["sensitive"] is True

    def test_unknown_service_returns_empty(self):
        mgr = ConfigManager(config_dir=".")
        assert mgr.get_config_template("unknown") == {}


class TestIsSensitiveKey:

    def test_token_is_sensitive(self):
        mgr = ConfigManager(config_dir=".")
        assert mgr._is_sensitive_key("HA_TOKEN") is True

    def test_api_key_is_sensitive(self):
        mgr = ConfigManager(config_dir=".")
        assert mgr._is_sensitive_key("DATA_API_KEY") is True

    def test_password_is_sensitive(self):
        mgr = ConfigManager(config_dir=".")
        assert mgr._is_sensitive_key("db_password") is True

    def test_url_is_not_sensitive(self):
        mgr = ConfigManager(config_dir=".")
        assert mgr._is_sensitive_key("HA_URL") is False
