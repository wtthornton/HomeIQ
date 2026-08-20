"""
Unit tests for Health Router

Epic 39, Story 39.8: Pattern Service Testing & Validation
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.database import get_db
from src.main import app


@pytest.fixture
def client(test_db: AsyncSession):
    """Create test client with database dependency override."""

    def override_get_db():
        return test_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestHealthRouter:
    """Test suite for health endpoints."""

    @pytest.mark.unit
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        # /health is StandardHealthCheck's liveness route (registered by create_app).
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in {"healthy", "degraded"}
        assert data["service"] == "ai-pattern-service"

    @pytest.mark.unit
    def test_readiness_check(self, client: TestClient):
        """Test readiness check endpoint."""
        # StandardHealthCheck's /ready is registered first and is strict: with no
        # dependency checks registered it reports 503 rather than a green it
        # cannot justify (TAP-5903).
        response = client.get("/ready")
        assert response.status_code == 503

    @pytest.mark.unit
    def test_liveness_check(self, client: TestClient):
        """Test liveness check endpoint."""
        response = client.get("/live")
        assert response.status_code == 200
        assert response.json() == {"status": "live"}

    @pytest.mark.unit
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        # Served by homeiq_resilience.create_app: service is the app title.
        assert data == {"service": "AI Pattern Service", "version": "1.0.0", "status": "running"}
