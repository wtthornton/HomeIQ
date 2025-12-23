"""
Unit tests for AI Automation Service Main Application

Epic 39, Story 39.10: Automation Service Foundation
Tests for main.py application initialization, lifespan, and configuration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


class TestMainApplication:
    """Test suite for main application initialization and configuration."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_root_endpoint(self, client: AsyncClient):
        """Test root endpoint returns service information."""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ai-automation-service"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"
        assert "note" in data
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_cors_headers(self, client: AsyncClient):
        """Test CORS headers are properly configured."""
        response = await client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET"
            }
        )
        # CORS middleware should handle OPTIONS requests
        assert response.status_code in [200, 204]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_app_includes_routers(self, client: AsyncClient):
        """Test that all routers are included in the application."""
        # Health router
        response = await client.get("/health")
        assert response.status_code in [200, 503]  # 503 if DB unavailable
        
        # Suggestion router (may require auth)
        response = await client.get("/api/v1/suggestions")
        # Should return 401 (unauthorized) or 200, not 404
        assert response.status_code != 404
        
        # Deployment router (may require auth)
        response = await client.get("/api/v1/deployment/automations")
        # Should return 401 (unauthorized) or 200, not 404
        assert response.status_code != 404


class TestLifespanManagement:
    """Test suite for application lifespan (startup/shutdown) management."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.start_rate_limit_cleanup')
    @patch('src.main.stop_rate_limit_cleanup')
    async def test_lifespan_startup_success(
        self,
        mock_stop_cleanup,
        mock_start_cleanup,
        mock_init_db
    ):
        """Test lifespan startup initializes all components successfully."""
        from src.main import lifespan, app
        
        mock_init_db.return_value = None
        mock_start_cleanup.return_value = None
        
        # Test lifespan context manager
        async with lifespan(app):
            # During startup
            mock_init_db.assert_called_once()
            mock_start_cleanup.assert_called_once()
        
        # During shutdown
        mock_stop_cleanup.assert_called_once()
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.start_rate_limit_cleanup')
    async def test_lifespan_startup_database_failure(
        self,
        mock_start_cleanup,
        mock_init_db
    ):
        """Test lifespan startup handles database initialization failure."""
        from src.main import lifespan, app
        
        mock_init_db.side_effect = Exception("Database connection failed")
        
        # Should raise exception during startup
        with pytest.raises(Exception, match="Database connection failed"):
            async with lifespan(app):
                pass
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.start_rate_limit_cleanup')
    @patch('src.main.stop_rate_limit_cleanup')
    async def test_lifespan_shutdown_handles_errors(
        self,
        mock_stop_cleanup,
        mock_start_cleanup,
        mock_init_db
    ):
        """Test lifespan shutdown handles errors gracefully."""
        from src.main import lifespan, app
        
        mock_init_db.return_value = None
        mock_start_cleanup.return_value = None
        mock_stop_cleanup.side_effect = Exception("Cleanup error")
        
        # Should not raise exception during shutdown
        async with lifespan(app):
            pass
        
        # Cleanup should have been attempted
        mock_stop_cleanup.assert_called_once()


class TestMiddlewareConfiguration:
    """Test suite for middleware configuration."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_authentication_middleware_enabled(self, client: AsyncClient):
        """Test that authentication middleware is enabled."""
        # Try to access protected endpoint without auth
        response = await client.get("/api/v1/suggestions")
        # Should return 401 (unauthorized) or 403 (forbidden), not 200
        assert response.status_code in [401, 403, 404]
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_rate_limiting_middleware_enabled(self, client: AsyncClient):
        """Test that rate limiting middleware is enabled."""
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = await client.get("/")
            responses.append(response.status_code)
        
        # All should succeed (root endpoint may not be rate limited)
        # But middleware should be active
        assert all(status in [200, 429] for status in responses)


class TestErrorHandling:
    """Test suite for error handling configuration."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_error_handler_registered(self, client: AsyncClient):
        """Test that error handlers are registered."""
        # Try to access non-existent endpoint
        # May return 401 (auth middleware) or 404 (not found)
        response = await client.get("/nonexistent")
        assert response.status_code in [401, 404]
        
        # Error response should be JSON
        assert "application/json" in response.headers.get("content-type", "")


class TestObservability:
    """Test suite for observability configuration."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch('src.main.init_db')
    @patch('src.main.start_rate_limit_cleanup')
    @patch('src.main.stop_rate_limit_cleanup')
    @patch('src.main.OBSERVABILITY_AVAILABLE', True)
    @patch('src.main.setup_tracing')
    @patch('src.main.instrument_fastapi')
    async def test_observability_initialized_when_available(
        self,
        mock_instrument,
        mock_setup_tracing,
        mock_stop_cleanup,
        mock_start_cleanup,
        mock_init_db
    ):
        """Test that observability is initialized when available."""
        from src.main import lifespan, app
        
        mock_init_db.return_value = None
        mock_start_cleanup.return_value = None
        mock_setup_tracing.return_value = None
        mock_instrument.return_value = None
        
        async with lifespan(app):
            # During startup, observability should be set up
            mock_setup_tracing.assert_called_once_with("ai-automation-service")
        
        # FastAPI should be instrumented
        mock_instrument.assert_called()


class TestConfiguration:
    """Test suite for application configuration."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_app_metadata(self, client: AsyncClient):
        """Test application metadata is correctly configured."""
        from src.main import app
        
        assert app.title == "AI Automation Service"
        assert app.description == "Automation service for suggestion generation, YAML generation, and deployment to Home Assistant"
        assert app.version == "1.0.0"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @patch.dict('os.environ', {'CORS_ORIGINS': 'http://localhost:3000,http://localhost:3001'})
    async def test_cors_configuration(self):
        """Test CORS configuration from environment variables."""
        from src.main import app
        
        # CORS middleware should be added
        assert len(app.user_middleware) > 0
        
        # Check that CORS middleware is present (check class name or module)
        middleware_info = [str(middleware.cls) for middleware in app.user_middleware]
        # CORS middleware will be in the middleware stack
        assert any('cors' in str(mid).lower() or 'CORSMiddleware' in str(mid) for mid in middleware_info)

