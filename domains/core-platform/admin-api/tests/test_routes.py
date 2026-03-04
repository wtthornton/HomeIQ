"""Tests for Admin API route registration."""

import os
from unittest.mock import MagicMock

os.environ.setdefault("API_KEY", "test-admin-api-key")

from src.main import app
from src.routes import register_root_endpoints, register_routers


class TestRegisterRouters:
    """Tests for register_routers function."""

    def test_includes_all_expected_tags(self) -> None:
        """Verify all expected router tags are present on the app."""
        tags = set()
        for route in app.routes:
            for tag in getattr(route, "tags", []):
                tags.add(tag)
        assert "Health" in tags
        assert "Docker Management" in tags

    def test_register_routers_adds_routes(self) -> None:
        """Verify register_routers calls app.include_router."""
        mock_app = MagicMock()
        register_routers(
            mock_app,
            auth_manager=MagicMock(),
            health_endpoints=MagicMock(),
            stats_endpoints=MagicMock(),
            config_endpoints=MagicMock(),
            docker_endpoints=MagicMock(),
            monitoring_endpoints=MagicMock(),
        )
        assert mock_app.include_router.call_count == 8


class TestRegisterRootEndpoints:
    """Tests for register_root_endpoints function."""

    def test_register_root_endpoints_adds_routes(self) -> None:
        """Verify register_root_endpoints registers /health, /, and /api/info."""
        mock_app = MagicMock()
        register_root_endpoints(
            mock_app,
            api_title="Test",
            api_version="1.0",
            api_description="Test API",
            allow_anonymous=False,
            docs_enabled=False,
            rate_limiter=MagicMock(),
            health_endpoints=MagicMock(),
        )
        # Should register 3 routes: /health, /, /api/info
        assert mock_app.get.call_count == 3
