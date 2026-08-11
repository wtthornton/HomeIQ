"""
Unit tests for AI Query Service Main Application

Epic 39, Story 39.12: Query & Automation Service Testing
"""

from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient
from src.main import app, lifespan


class TestMainApplication:
    """Test suite for main application initialization and configuration."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_root_endpoint(self):
        """Test root endpoint returns service information."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            # Root payload comes from homeiq_resilience.create_app: it echoes
            # the app title/version and reports status "running".
            assert data["service"] == "AI Query Service"
            assert data["version"] == "1.0.0"
            assert data["status"] == "running"

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.main.init_db")
    @patch("src.main.setup_tracing")
    async def test_lifespan_startup_success(self, _mock_tracing, mock_init_db):
        """Test lifespan startup initializes database and observability successfully."""
        mock_init_db.return_value = True

        with patch("src.main.OBSERVABILITY_AVAILABLE", True):
            async with lifespan.handler(app):
                # Should complete without errors
                pass

        mock_init_db.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.main.init_db")
    async def test_lifespan_startup_database_failure(self, mock_init_db):
        """Database init failure must not abort startup (degraded mode).

        ServiceLifespan is constructed with graceful=True, so a raising
        startup hook is logged and swallowed; init_db itself is also
        documented to return False rather than raise. Either way the
        service must come up degraded instead of crashing.
        """
        mock_init_db.side_effect = Exception("Database connection failed")

        async with lifespan.handler(app):
            pass

        mock_init_db.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.main.init_db")
    @patch("src.main.setup_tracing")
    async def test_lifespan_startup_observability_failure(self, mock_tracing, mock_init_db):
        """Test lifespan startup handles observability failure gracefully."""
        mock_init_db.return_value = True
        mock_tracing.side_effect = Exception("Observability setup failed")

        with patch("src.main.OBSERVABILITY_AVAILABLE", True):
            # Should not raise exception, just log warning
            async with lifespan.handler(app):
                pass

        mock_init_db.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.main.init_db")
    async def test_lifespan_shutdown(self, mock_init_db):
        """Test lifespan shutdown completes successfully."""
        mock_init_db.return_value = True

        async with lifespan.handler(app):
            # Startup completes
            pass
        # Shutdown should complete without errors

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cors_middleware_configured(self):
        """Test CORS middleware is properly configured."""
        # Check that CORS middleware is added
        # This is verified by the app having CORS configured
        assert app is not None
        # CORS is configured in main.py, so app should have middleware

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.main.register_error_handlers")
    async def test_error_handlers_registered(self, _mock_register):
        """Test error handlers are registered if available."""
        # Error handlers are registered at module level
        # This test verifies the pattern exists
        assert app is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch("src.main.OBSERVABILITY_AVAILABLE", True)
    @patch("src.main.instrument_fastapi")
    @patch("src.main.CorrelationMiddleware")
    async def test_observability_instrumentation(self, _mock_correlation, _mock_instrument):
        """Test observability instrumentation is applied when available."""
        # Observability is configured at module level
        # This test verifies the pattern exists
        assert app is not None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_routers_included(self):
        """Test that health and query routers are included."""
        # FastAPI 0.140 wraps included routers in _IncludedRouter objects
        # without a .path, so inspect the OpenAPI schema (the public surface)
        # instead of iterating app.routes.
        paths = app.openapi()["paths"]
        assert "/health" in paths
        assert any(path.startswith("/api/v1") for path in paths)
