"""
Unit tests for Health Router

Epic 39, Story 39.4: Training Service Testing & Validation
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.main import app
from src.database import get_db


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
    
    def test_health_check(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "database" in data
    
    def test_readiness_check(self, client: TestClient):
        """Test readiness check endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
    
    def test_liveness_check(self, client: TestClient):
        """Test liveness check endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "live"
    
    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ai-training-service"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"

