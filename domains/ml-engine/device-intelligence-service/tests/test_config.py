"""Settings validation and URL derivation for device-intelligence.

Replaces test_mqtt_broker_config.py, which covered MQTT_BROKER semantics.
That setting was removed with the rest of the MQTT path (Zigbee here is HA's
built-in ZHA), so its tests went with it; these cover the validators and URL
helpers that remain.
"""

import pytest
from pydantic import ValidationError
from src.config import Settings

# Settings still reads os.environ, so a developer .env at the repo root would
# otherwise supply HA_WS_URL / NABU_CASA_URL and mask the derivation logic.
_LEAKY_ENV = ("HA_URL", "HA_WS_URL", "NABU_CASA_URL", "ALLOWED_ORIGINS")


@pytest.fixture
def clean_env(monkeypatch):
    for name in _LEAKY_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _settings(**overrides):
    base = {"HA_URL": "http://ha:8123", "HA_TOKEN": "token-1234567890"}
    base.update(overrides)
    return Settings(_env_file=None, **base)


class TestHaUrlValidation:
    def test_trailing_slash_is_stripped(self):
        assert _settings(HA_URL="http://ha:8123/").HA_URL == "http://ha:8123"

    def test_https_accepted(self):
        assert _settings(HA_URL="https://ha.example:8123").HA_URL == "https://ha.example:8123"

    def test_scheme_is_required(self):
        with pytest.raises(ValidationError, match="HA_URL must start with"):
            _settings(HA_URL="ha:8123")


class TestWebsocketUrlDerivation:
    def test_derived_from_http_when_unset(self, clean_env):
        assert _settings().get_ha_ws_url() == "ws://ha:8123/api/websocket"

    def test_https_derives_wss(self, clean_env):
        settings = _settings(HA_URL="https://ha.example")
        assert settings.get_ha_ws_url() == "wss://ha.example/api/websocket"

    def test_explicit_ws_url_wins(self, clean_env):
        settings = _settings(HA_WS_URL="ws://other:8123/api/websocket")
        assert settings.get_ha_ws_url() == "ws://other:8123/api/websocket"

    def test_nabu_casa_is_none_when_unset(self, clean_env):
        assert _settings().get_nabu_casa_ws_url() is None

    def test_nabu_casa_derives_wss(self, clean_env):
        settings = _settings(NABU_CASA_URL="https://x.ui.nabu.casa")
        assert settings.get_nabu_casa_ws_url() == "wss://x.ui.nabu.casa/api/websocket"


class TestAllowedOrigins:
    def test_comma_delimited_string_is_split(self):
        settings = _settings(ALLOWED_ORIGINS="http://a:3000, http://b:3000")
        assert settings.ALLOWED_ORIGINS == ["http://a:3000", "http://b:3000"]

    def test_json_list_is_parsed(self):
        settings = _settings(ALLOWED_ORIGINS='["http://a:3000"]')
        assert settings.ALLOWED_ORIGINS == ["http://a:3000"]

    def test_blank_entries_are_dropped(self):
        settings = _settings(ALLOWED_ORIGINS="http://a:3000,,  ")
        assert settings.ALLOWED_ORIGINS == ["http://a:3000"]

    def test_malformed_json_is_rejected(self):
        with pytest.raises(ValidationError, match="Invalid ALLOWED_ORIGINS JSON"):
            _settings(ALLOWED_ORIGINS='["unterminated')
