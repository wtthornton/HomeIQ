"""
Unit tests for Automation Service Suggestion Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from fastapi.testclient import TestClient


class TestSuggestionRouter:
    """Test suite for suggestion router endpoints."""
    
    @pytest.mark.unit
    def test_generate_suggestions_endpoint(self, client: TestClient):
        """Test suggestion generation endpoint (foundation)."""
        response = client.post("/api/suggestions/generate")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "foundation_ready"
    
    @pytest.mark.unit
    def test_list_suggestions_endpoint(self, client: TestClient):
        """Test list suggestions endpoint (foundation)."""
        response = client.get("/api/suggestions/list")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "total" in data
        assert isinstance(data["suggestions"], list)
    
    @pytest.mark.unit
    def test_list_suggestions_with_params(self, client: TestClient):
        """Test list suggestions with query parameters."""
        response = client.get("/api/suggestions/list?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    @pytest.mark.unit
    def test_usage_stats_endpoint(self, client: TestClient):
        """Test usage stats endpoint (foundation)."""
        response = client.get("/api/suggestions/usage/stats")
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "message" in data
    
    @pytest.mark.unit
    def test_refresh_suggestions_endpoint(self, client: TestClient):
        """Test refresh suggestions endpoint (foundation)."""
        response = client.post("/api/suggestions/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
    
    @pytest.mark.unit
    def test_refresh_status_endpoint(self, client: TestClient):
        """Test refresh status endpoint (foundation)."""
        response = client.get("/api/suggestions/refresh/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

