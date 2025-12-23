"""
Unit tests for Automation Service Deployment Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from httpx import AsyncClient


class TestDeploymentRouter:
    """Test suite for deployment router endpoints."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_deploy_suggestion_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test deploy suggestion endpoint (foundation)."""
        response = await client.post("/api/deploy/1", json={"skip_validation": False}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "suggestion_id" in data
        assert data["suggestion_id"] == 1
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_batch_deploy_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test batch deploy endpoint (foundation)."""
        response = await client.post("/api/deploy/batch", json={"suggestion_ids": [1, 2, 3]}, headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "suggestion_ids" in data
        assert "status" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_list_automations_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test list automations endpoint (foundation)."""
        response = await client.get("/api/deploy/automations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "automations" in data
        assert isinstance(data["automations"], list)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_automation_status_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test get automation status endpoint (foundation)."""
        response = await client.get("/api/deploy/automations/test-automation-123", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert data["automation_id"] == "test-automation-123"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_enable_automation_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test enable automation endpoint (foundation)."""
        response = await client.post("/api/deploy/automations/test-automation-123/enable", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_disable_automation_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test disable automation endpoint (foundation)."""
        response = await client.post("/api/deploy/automations/test-automation-123/disable", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_test_connection_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test HA connection endpoint (foundation)."""
        response = await client.get("/api/deploy/test-connection", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_rollback_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test rollback endpoint (foundation)."""
        response = await client.post("/api/deploy/test-automation-123/rollback", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_get_versions_endpoint(self, client: AsyncClient, auth_headers: dict):
        """Test get versions endpoint (foundation)."""
        response = await client.get("/api/deploy/test-automation-123/versions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "versions" in data
        assert isinstance(data["versions"], list)

