"""
Unit tests for Query Service Health Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from fastapi.testclient import TestClient


class TestHealthRouter:
    """Test suite for health router endpoints."""
    
    @pytest.mark.unit
    def test_health_endpoint(self, client: TestClient):
        """Test health endpoint returns 200."""
        response = client.get("/health/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "healthy"]
        assert "service" in data
        assert data["service"] == "ai-query-service"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @pytest.mark.requires_db
    def test_readiness_endpoint(self, client: TestClient):
        """Test readiness endpoint returns 200."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]
        assert "service" in data
        assert "database" in data
    
    @pytest.mark.unit
    def test_liveness_endpoint(self, client: TestClient):
        """Test liveness endpoint returns 200."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "live"
        assert data["service"] == "ai-query-service"

