"""Tests for Admin API route registration."""

import os
from unittest.mock import MagicMock

os.environ.setdefault("API_KEY", "test-admin-api-key")

from src.main import app
from src.routes import register_root_endpoints, register_routers


class TestRegisterRouters:
    """Tests for register_routers function."""

    def test_includes_all_expected_tags(self) -> None:
        """Verify all expected router tags are present on the app.

        Read from the OpenAPI schema rather than app.routes: FastAPI wraps
        included routers in _IncludedRouter, so tags no longer surface on the
        top-level route objects.
        """
        tags = {
            tag
            for path_item in app.openapi()["paths"].values()
            for operation in path_item.values()
            for tag in operation.get("tags", [])
        }
        assert "Health" in tags
        assert "Docker Management" in tags
        assert "Statistics" in tags
        assert "Monitoring" in tags

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
        registered_tags = {
            tag
            for call in mock_app.include_router.call_args_list
            for tag in call.kwargs.get("tags", [])
        }
        assert {
            "Health",
            "Statistics",
            "Configuration",
            "Docker Management",
            "Monitoring",
        } <= registered_tags
        # The "Integrations" tag existed only for the MQTT broker-config routes,
        # deleted in TAP-6400. Asserting its absence is what stops them coming
        # back: Zigbee here is ZHA and no endpoint may accept broker config.
        assert "Integrations" not in registered_tags


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
        # register_root_endpoints owns /api/info; /health and / are registered
        # by register_public_endpoints.
        assert mock_app.get.call_count == 1
        assert mock_app.get.call_args_list[0].args[0] == "/api/info"
