"""
Unit tests for Automation Service Suggestion Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from httpx import AsyncClient


class TestSuggestionRouter:
    """Test suite for suggestion router endpoints."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_generate_suggestions_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test suggestion generation endpoint (foundation)."""
        response = await client.post("/api/suggestions/generate", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "foundation_ready"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_suggestions_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test list suggestions endpoint (foundation)."""
        response = await client.get("/api/suggestions/list", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert "total" in data
        assert isinstance(data["suggestions"], list)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_suggestions_with_params(self, client: AsyncClient, auth_headers: dict):
        """Test list suggestions with query parameters."""
        response = await client.get("/api/suggestions/list?limit=10&offset=0", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_usage_stats_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test usage stats endpoint (foundation)."""
        response = await client.get("/api/suggestions/usage/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "stats" in data
        assert "message" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_suggestions_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test refresh suggestions endpoint (foundation)."""
        response = await client.post("/api/suggestions/refresh", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_refresh_status_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test refresh status endpoint (foundation)."""
        response = await client.get("/api/suggestions/refresh/status", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data

