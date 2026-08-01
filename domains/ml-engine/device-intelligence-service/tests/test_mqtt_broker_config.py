"""MQTT_BROKER config semantics: empty/unset means MQTT disabled.

Regression: compose passes MQTT_BROKER as an empty string when no broker
is configured; the validator rejected "" and the service crash-looped at
boot on hosts with no MQTT broker.
"""

import pytest
from pydantic import ValidationError
from src.config import Settings


def _settings(**overrides):
    base = {"HA_URL": "http://ha:8123", "HA_TOKEN": "token-1234567890"}
    base.update(overrides)
    return Settings(_env_file=None, **base)


class TestMqttBrokerConfig:
    def test_empty_string_means_unconfigured(self):
        assert _settings(MQTT_BROKER="").MQTT_BROKER is None

    def test_whitespace_means_unconfigured(self):
        assert _settings(MQTT_BROKER="   ").MQTT_BROKER is None

    def test_unset_defaults_to_none(self):
        assert _settings().MQTT_BROKER is None

    def test_valid_url_accepted(self):
        assert _settings(MQTT_BROKER="mqtt://broker:1883").MQTT_BROKER == "mqtt://broker:1883"

    def test_invalid_scheme_still_rejected(self):
        with pytest.raises(ValidationError, match="MQTT_BROKER must start with"):
            _settings(MQTT_BROKER="http://broker:1883")
