"""
Unit tests for Query Service Health Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from httpx import AsyncClient


class TestHealthRouter:
    """Test suite for health router endpoints."""
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_endpoint(self, client: AsyncClient):
        """Test health endpoint returns 200."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "healthy"]
        assert "service" in data
        assert data["service"] == "ai-query-service"
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    @pytest.mark.requires_db
    async def test_readiness_endpoint(self, client: AsyncClient):
        """Test readiness endpoint returns 200."""
        response = await client.get("/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ready", "not_ready"]
        assert "service" in data
        assert "database" in data
    
    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_liveness_endpoint(self, client: AsyncClient):
        """Test liveness endpoint returns 200."""
        response = await client.get("/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "live"
        assert data["service"] == "ai-query-service"

