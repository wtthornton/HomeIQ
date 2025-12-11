"""
Unit tests for Automation Service Health Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthRouter:
    """Test suite for health router endpoints."""
    
    @pytest.mark.unit
    def test_health_endpoint(self, client: TestClient):
        """Test health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "service" in data
        assert data["service"] == "ai-automation-service"
    
    @pytest.mark.unit
    @pytest.mark.requires_db
    def test_health_endpoint_with_db(self, client: TestClient):
        """Test health endpoint with database connection."""
        response = client.get("/health")
        assert response.status_code in [200, 503]  # 503 if DB unavailable
        data = response.json()
        assert "service" in data
        assert data["service"] == "ai-automation-service"

