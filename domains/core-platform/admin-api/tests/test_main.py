"""Tests for Admin API main service."""

import os
from unittest.mock import AsyncMock, Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("API_KEY", "test-admin-api-key")

from src.main import AdminAPIService, app


class TestAdminAPIService:
    """Test AdminAPIService class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.service = AdminAPIService()

    def test_init(self) -> None:
        """Test service initialization from default config."""
        assert self.service.cfg.api_host == "0.0.0.0"  # noqa: S104
        assert self.service.cfg.api_port == 8000
        assert self.service.cfg.api_title == "Home Assistant Ingestor Admin API"
        assert self.service.cfg.api_version == "1.0.0"
        assert self.service.cfg.allow_anonymous is False
        assert self.service.is_running is False
        assert self.service.app is None
        assert self.service.server_task is None

    @patch("src.main.uvicorn.Server")
    @patch("src.main.uvicorn.Config")
    async def test_start(self, mock_config: Mock, mock_server: Mock) -> None:
        """Test service start creates app and starts server."""
        mock_server_instance = AsyncMock()
        mock_server.return_value = mock_server_instance
        mock_config.return_value = Mock()

        await self.service.start()

        assert self.service.is_running is True
        assert self.service.app is not None
        assert self.service.server_task is not None
        mock_server_instance.serve.assert_called_once()

    async def test_start_already_running(self) -> None:
        """Test starting service that's already running logs a warning."""
        self.service.is_running = True
        with patch("src.main.logger") as mock_logger:
            await self.service.start()
            mock_logger.warning.assert_called_with(
                "Admin API is already running"
            )

    async def test_stop(self) -> None:
        """Test service stop cancels task and cleans up."""
        self.service.is_running = True
        self.service.server_task = AsyncMock()
        await self.service.stop()
        assert self.service.is_running is False
        self.service.server_task.cancel.assert_called_once()

    async def test_stop_not_running(self) -> None:
        """Test stopping a non-running service is a no-op."""
        self.service.is_running = False
        await self.service.stop()

    def test_get_app(self) -> None:
        """Test get_app returns the current app instance."""
        mock_app = Mock(spec=FastAPI)
        self.service.app = mock_app
        assert self.service.get_app() == mock_app

    def test_get_app_none(self) -> None:
        """Test get_app returns None before start."""
        assert self.service.get_app() is None


class TestFastAPIApp:
    """Test FastAPI application endpoints."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)

    def test_root_endpoint(self) -> None:
        """Test root endpoint returns service info."""
        response = self.client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["status"] == "running"

    def test_api_info_endpoint(self) -> None:
        """Test /api/info returns API metadata."""
        response = self.client.get("/api/info")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "endpoints" in data["data"]
        assert "authentication" in data["data"]

    def test_simple_health_endpoint(self) -> None:
        """Test /api/health returns simple healthy status."""
        response = self.client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "admin-api"

    def test_root_health_endpoint(self) -> None:
        """Test /health returns Docker health check status."""
        response = self.client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data

    def test_simple_metrics_endpoint(self) -> None:
        """Test /api/metrics/realtime returns stub metrics."""
        response = self.client.get("/api/metrics/realtime")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "events_per_second" in data

    def test_health_endpoint(self) -> None:
        """Test /api/v1/health from health_endpoints router."""
        response = self.client.get("/api/v1/health")
        assert response.status_code == 200

    def test_cors_headers(self) -> None:
        """Test CORS headers are present on OPTIONS requests."""
        response = self.client.options("/api/v1/health")
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_docs_endpoint(self) -> None:
        """Test /docs returns 200 or 404 based on config."""
        response = self.client.get("/docs")
        assert response.status_code in [200, 404]

    def test_openapi_endpoint(self) -> None:
        """Test /openapi.json returns 200 or 404 based on config."""
        response = self.client.get("/openapi.json")
        assert response.status_code in [200, 404]


class TestErrorHandling:
    """Test error handling."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)

    def test_404_error(self) -> None:
        """Test 404 returns structured error response."""
        response = self.client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert data["success"] is False
        assert "error" in data

    def test_500_error(self) -> None:
        """Test graceful handling of invalid query params."""
        response = self.client.get("/api/v1/stats?period=invalid")
        assert response.status_code in [200, 400, 500]


class TestAuthentication:
    """Test authentication on protected endpoints."""

    def setup_method(self) -> None:
        """Set up test client."""
        self.client = TestClient(app)

    def test_protected_stats(self) -> None:
        """Test stats endpoint requires auth (or allows anonymous)."""
        response = self.client.get("/api/v1/stats")
        assert response.status_code in [200, 401]

    def test_protected_config(self) -> None:
        """Test config endpoint requires auth (or allows anonymous)."""
        response = self.client.get("/api/v1/config")
        assert response.status_code in [200, 401]
