"""Tests for Settings token secrecy and ServiceConfig unwrapping.

Regression tests for the AgentForge audit finding that HA / Nabu Casa
tokens were stored as plain ``str`` on ``Settings`` and leaked via
``repr()`` / ``str()`` dumps. Tokens are now ``SecretStr`` (matching the
inherited ``influxdb_token`` pattern) and unwrapped to plain ``str`` at
the ``ServiceConfig`` boundary for downstream connection managers.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from src._service_config import ServiceConfig
from src.config import Settings, settings

TOKEN_ENV_VARS = ("HA_TOKEN", "HOME_ASSISTANT_TOKEN", "NABU_CASA_TOKEN")


@pytest.fixture
def clean_token_env(monkeypatch):
    """Remove token env vars so explicit kwargs fully control each test."""
    for name in TOKEN_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.mark.usefixtures("clean_token_env")
class TestSettingsTokenSecrecy:
    """Token fields must never appear unredacted in Settings dumps."""

    def test_settings_repr_does_not_leak_tokens(self):
        instance = Settings(
            _env_file=None,
            ha_token="raw-ha-token-value",
            home_assistant_token="raw-legacy-token-value",
            nabu_casa_token="raw-nabu-token-value",
        )

        for dump in (repr(instance), str(instance)):
            assert "raw-ha-token-value" not in dump
            assert "raw-legacy-token-value" not in dump
            assert "raw-nabu-token-value" not in dump
            assert "**********" in dump

    def test_token_fields_are_secretstr(self):
        instance = Settings(
            _env_file=None,
            ha_token="raw-ha-token-value",
            home_assistant_token="raw-legacy-token-value",
            nabu_casa_token="raw-nabu-token-value",
        )

        assert isinstance(instance.ha_token, SecretStr)
        assert isinstance(instance.home_assistant_token, SecretStr)
        assert isinstance(instance.nabu_casa_token, SecretStr)


@pytest.mark.usefixtures("clean_token_env")
class TestResolvedHaTokenPrecedence:
    """resolved_ha_token precedence must survive the SecretStr migration."""

    def test_ha_token_wins_over_home_assistant_token(self):
        instance = Settings(
            _env_file=None,
            ha_token="primary-token",
            home_assistant_token="legacy-token",
        )

        assert instance.resolved_ha_token is not None
        assert instance.resolved_ha_token.get_secret_value() == "primary-token"

    def test_falls_back_to_home_assistant_token(self):
        instance = Settings(_env_file=None, home_assistant_token="legacy-token")

        assert instance.resolved_ha_token is not None
        assert instance.resolved_ha_token.get_secret_value() == "legacy-token"

    def test_none_when_no_token_set(self):
        instance = Settings(_env_file=None)

        assert instance.resolved_ha_token is None


class TestServiceConfigTokenUnwrapping:
    """ServiceConfig must expose plain-str tokens for downstream managers."""

    def test_service_config_receives_plain_str_tokens(self, monkeypatch):
        monkeypatch.setattr(settings, "ha_token", SecretStr("plain-ha-token"))
        monkeypatch.setattr(settings, "home_assistant_token", None)
        monkeypatch.setattr(settings, "nabu_casa_token", SecretStr("plain-nabu-token"))

        cfg = ServiceConfig()

        assert cfg.home_assistant_token == "plain-ha-token"
        assert type(cfg.home_assistant_token) is str
        assert cfg.nabu_casa_token == "plain-nabu-token"
        assert type(cfg.nabu_casa_token) is str

    def test_service_config_tokens_none_when_unset(self, monkeypatch):
        monkeypatch.setattr(settings, "ha_token", None)
        monkeypatch.setattr(settings, "home_assistant_token", None)
        monkeypatch.setattr(settings, "nabu_casa_token", None)

        cfg = ServiceConfig()

        assert cfg.home_assistant_token is None
        assert cfg.nabu_casa_token is None
