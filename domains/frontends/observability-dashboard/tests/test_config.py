"""Tests for configuration settings."""

import os
from unittest.mock import patch

from config import Settings


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
