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
        assert self.service.cfg.service_name == "admin-api"
        assert self.service.cfg.api_title == "Home Assistant Ingestor Admin API"
        assert self.service.cfg.api_version == "1.0.0"
        assert self.service.cfg.allow_anonymous is False

    def test_init_builds_collaborators(self) -> None:
        """Every endpoint group and the auth/rate-limit stack is constructed."""
        assert self.service.auth_manager is not None
        assert self.service.rate_limiter is not None
        assert self.service.health_endpoints is not None
        assert self.service.stats_endpoints is not None
        assert self.service.config_endpoints is not None
        assert self.service.docker_endpoints is not None
        assert self.service.monitoring_endpoints is not None

    def test_setup_app_registers_routes(self) -> None:
        """setup_app wires routers onto a bare FastAPI app."""
        target = FastAPI()
        before = len(target.routes)

        self.service.setup_app(target)

        assert len(target.routes) > before
        paths = {getattr(r, "path", None) for r in target.routes}
        assert "/api/v1/health" in paths

    def test_setup_app_registers_exception_handlers(self) -> None:
        """setup_app installs the structured error handlers."""
        target = FastAPI()
        self.service.setup_app(target)

        assert target.exception_handlers


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
        assert data["status"] == "running"
        assert data["service"] == "Home Assistant Ingestor Admin API"
        assert data["version"] == "1.0.0"

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
        """Test CORS headers are present on a preflight request.

        A bare OPTIONS is 405; CORSMiddleware only answers when the request
        carries Origin and Access-Control-Request-Method.
        """
        response = self.client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
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
        """Test an unknown path returns FastAPI's 404 detail payload."""
        response = self.client.get("/nonexistent")
        assert response.status_code == 404
        assert response.json()["detail"] == "Not Found"

    def test_protected_endpoint_requires_auth(self) -> None:
        """The stats router is behind auth, so an anonymous call is rejected."""
        response = self.client.get("/api/v1/stats?period=invalid")
        assert response.status_code == 401


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
