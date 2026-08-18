"""Tests for configuration settings."""

import os
from unittest.mock import patch

import pytest

from config import Settings


@pytest.fixture(autouse=True)
def settings_env(monkeypatch, tmp_path):
    """Construct Settings from a known-empty environment (TAP-6154).

    Settings resolve ``env_file`` against the process working directory, so
    running this file from the repository root loaded the repository ``.env``
    and ``test_default_agentforge_api_key`` saw the real AGENTFORGE_API_KEY
    instead of the default it asserts. Every default assertion below has the
    same exposure; the failure just happened to surface on one of them.

    Chdir somewhere with no ``.env`` and clear every name the model reads. The
    name list comes from the model, so a new field cannot reintroduce the leak.
    """
    monkeypatch.chdir(tmp_path)
    for name, field in Settings.model_fields.items():
        for key in {name, field.alias or name}:
            monkeypatch.delenv(key.upper(), raising=False)


class TestSettings:
    def test_default_service_port(self):
        s = Settings()
        assert s.service_port == 8501

    def test_default_service_name(self):
        s = Settings()
        assert s.service_name == "observability-dashboard"

    def test_default_jaeger_url(self):
        s = Settings()
        assert s.jaeger_url == "http://jaeger:16686"

    def test_default_jaeger_api_url(self):
        s = Settings()
        assert s.jaeger_api_url == "http://jaeger:16686/api"

    def test_default_admin_api_url(self):
        s = Settings()
        assert s.admin_api_url == "http://admin-api:8004"

    def test_default_cross_app_urls(self):
        s = Settings()
        assert s.ai_automation_ui_url == "http://localhost:3001"
        assert s.health_dashboard_url == "http://localhost:3000"

    def test_env_override_jaeger_url(self):
        with patch.dict(os.environ, {"JAEGER_URL": "http://custom-jaeger:9999"}):
            s = Settings()
            assert s.jaeger_url == "http://custom-jaeger:9999"

    def test_env_override_service_port(self):
        with patch.dict(os.environ, {"SERVICE_PORT": "9000"}):
            s = Settings()
            assert s.service_port == 9000

    def test_default_agentforge_url(self):
        s = Settings()
        assert s.agentforge_url == "http://localhost:8010"

    def test_default_agentforge_api_key(self):
        s = Settings()
        assert s.agentforge_api_key == ""

    def test_env_override_agentforge_url(self):
        with patch.dict(os.environ, {"AGENTFORGE_URL": "http://custom-af:9999"}):
            s = Settings()
            assert s.agentforge_url == "http://custom-af:9999"

    def test_env_override_agentforge_api_key(self):
        with patch.dict(os.environ, {"AGENTFORGE_API_KEY": "secret-key-123"}):
            s = Settings()
            assert s.agentforge_api_key == "secret-key-123"
