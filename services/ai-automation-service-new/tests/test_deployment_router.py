"""
Unit tests for Automation Service Deployment Router

Epic 39, Story 39.12: Query & Automation Service Testing
"""

import pytest
from fastapi.testclient import TestClient


class TestDeploymentRouter:
    """Test suite for deployment router endpoints."""
    
    @pytest.mark.unit
    def test_deploy_suggestion_endpoint(self, client: TestClient):
        """Test deploy suggestion endpoint (foundation)."""
        response = client.post("/api/deploy/1", json={"skip_validation": False})
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "suggestion_id" in data
        assert data["suggestion_id"] == 1
    
    @pytest.mark.unit
    def test_batch_deploy_endpoint(self, client: TestClient):
        """Test batch deploy endpoint (foundation)."""
        response = client.post("/api/deploy/batch", json={"suggestion_ids": [1, 2, 3]})
        assert response.status_code == 200
        data = response.json()
        assert "suggestion_ids" in data
        assert "status" in data
    
    @pytest.mark.unit
    def test_list_automations_endpoint(self, client: TestClient):
        """Test list automations endpoint (foundation)."""
        response = client.get("/api/deploy/automations")
        assert response.status_code == 200
        data = response.json()
        assert "automations" in data
        assert isinstance(data["automations"], list)
    
    @pytest.mark.unit
    def test_get_automation_status_endpoint(self, client: TestClient):
        """Test get automation status endpoint (foundation)."""
        response = client.get("/api/deploy/automations/test-automation-123")
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert data["automation_id"] == "test-automation-123"
    
    @pytest.mark.unit
    def test_enable_automation_endpoint(self, client: TestClient):
        """Test enable automation endpoint (foundation)."""
        response = client.post("/api/deploy/automations/test-automation-123/enable")
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data
    
    @pytest.mark.unit
    def test_disable_automation_endpoint(self, client: TestClient):
        """Test disable automation endpoint (foundation)."""
        response = client.post("/api/deploy/automations/test-automation-123/disable")
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data
    
    @pytest.mark.unit
    def test_test_connection_endpoint(self, client: TestClient):
        """Test HA connection endpoint (foundation)."""
        response = client.get("/api/deploy/test-connection")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "message" in data
    
    @pytest.mark.unit
    def test_rollback_endpoint(self, client: TestClient):
        """Test rollback endpoint (foundation)."""
        response = client.post("/api/deploy/test-automation-123/rollback")
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "status" in data
    
    @pytest.mark.unit
    def test_get_versions_endpoint(self, client: TestClient):
        """Test get versions endpoint (foundation)."""
        response = client.get("/api/deploy/test-automation-123/versions")
        assert response.status_code == 200
        data = response.json()
        assert "automation_id" in data
        assert "versions" in data
        assert isinstance(data["versions"], list)

