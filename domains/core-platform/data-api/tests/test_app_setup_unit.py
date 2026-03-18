"""Unit tests for _app_setup.py — Story 85.7

Tests middleware configuration and router registration.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src._app_setup import configure_middleware, register_routers


class TestConfigureMiddleware:
    """Test middleware configuration."""

    def _make_app_and_svc(self, cors_origins=None):
        app = MagicMock()
        app.add_middleware = MagicMock()
        app.middleware = MagicMock(return_value=lambda fn: fn)

        svc = MagicMock()
        svc.cors_origins = cors_origins or ["http://localhost:3000"]
        svc.rate_limiter = MagicMock()
        svc.total_requests = 0
        svc.failed_requests = 0
        return app, svc

    @patch("src._app_setup.OBSERVABILITY_AVAILABLE", False)
    def test_cors_middleware_added(self):
        app, svc = self._make_app_and_svc(["http://localhost:3000"])
        with patch("homeiq_data.rate_limiter.rate_limit_middleware", create=True):
            configure_middleware(app, svc)
        # CORSMiddleware should be added
        cors_calls = [c for c in app.add_middleware.call_args_list
                      if "CORSMiddleware" in str(c)]
        assert len(cors_calls) >= 1

    @patch("src._app_setup.OBSERVABILITY_AVAILABLE", False)
    def test_cors_no_credentials_with_wildcard(self):
        """CORS credentials disabled when origins include '*'."""
        app, svc = self._make_app_and_svc(["*"])
        with patch("homeiq_data.rate_limiter.rate_limit_middleware", create=True):
            configure_middleware(app, svc)
        # Find the CORS call and check allow_credentials
        for call in app.add_middleware.call_args_list:
            if len(call.args) > 0 and "CORS" in str(call.args[0]):
                assert call.kwargs.get("allow_credentials") is False
                break

    @patch("src._app_setup.OBSERVABILITY_AVAILABLE", False)
    def test_cors_credentials_with_specific_origins(self):
        app, svc = self._make_app_and_svc(["http://localhost:3000"])
        with patch("homeiq_data.rate_limiter.rate_limit_middleware", create=True):
            configure_middleware(app, svc)
        for call in app.add_middleware.call_args_list:
            if len(call.args) > 0 and "CORS" in str(call.args[0]):
                assert call.kwargs.get("allow_credentials") is True
                break

    @patch("src._app_setup.OBSERVABILITY_AVAILABLE", False)
    def test_correlation_middleware_fallback(self):
        """When observability not available, uses FastAPICorrelationMiddleware."""
        app, svc = self._make_app_and_svc()
        with patch("homeiq_data.rate_limiter.rate_limit_middleware", create=True):
            configure_middleware(app, svc)
        middleware_names = [str(c) for c in app.add_middleware.call_args_list]
        assert any("Correlation" in m for m in middleware_names)


class TestRegisterRouters:
    """Test that all routers are registered."""

    def test_registers_authenticated_routers(self):
        app = MagicMock()
        svc = MagicMock()
        svc.auth_manager.get_current_user = MagicMock()

        register_routers(app, svc)

        # Count include_router calls
        assert app.include_router.call_count >= 14  # 14 authenticated + 2 internal

    def test_automation_internal_has_no_auth_dependency(self):
        """automation_internal_router should be registered without auth."""
        app = MagicMock()
        svc = MagicMock()
        svc.auth_manager.get_current_user = MagicMock()

        register_routers(app, svc)

        # Find the call for automation_internal_router (no "dependencies" key)
        for call in app.include_router.call_args_list:
            kwargs = call.kwargs
            tags = kwargs.get("tags", [])
            if "Automation Trace (Internal)" in tags:
                assert "dependencies" not in kwargs
                break

    def test_routers_have_prefixes(self):
        """Most routers should have /api/v1 prefix."""
        app = MagicMock()
        svc = MagicMock()
        svc.auth_manager.get_current_user = MagicMock()

        register_routers(app, svc)

        prefix_calls = [c for c in app.include_router.call_args_list
                        if c.kwargs.get("prefix") == "/api/v1"]
        assert len(prefix_calls) >= 8
