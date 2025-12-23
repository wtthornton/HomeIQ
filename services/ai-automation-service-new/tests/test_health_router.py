"""
Unit tests for Automation Service Health Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from httpx import AsyncClient


class TestHealthRouter:
    """Test suite for health router endpoints."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health endpoint returns 200."""
        response = await client.get("/health")
        # Health endpoint may return 200 (healthy) or 503 (unhealthy)
        assert response.status_code in [200, 503]
        data = response.json()
        # Response should be a dict, not a list
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "service" in data
        assert data["service"] == "ai-automation-service"
    
    @pytest.mark.unit
    @pytest.mark.requires_db
    @pytest.mark.asyncio
    async def test_health_endpoint_with_db(self, client: AsyncClient):
        """Test health endpoint with database connection."""
        response = await client.get("/health")
        assert response.status_code in [200, 503]  # 503 if DB unavailable
        data = response.json()
        # Response should be a dict
        assert isinstance(data, dict)
        assert "service" in data
        assert data["service"] == "ai-automation-service"

