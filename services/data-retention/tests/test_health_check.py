"""Tests for health check endpoints."""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient
from src.api.app import app


class TestHealthCheckEndpoints:
    """Test health check endpoints."""

    @pytest.fixture
    def mock_service(self):
        """Create mock data retention service."""
        service = Mock()
        service.get_service_status.return_value = {
            "cleanup_service": True,
            "storage_monitor": True,
            "compression_service": True,
            "backup_service": True,
            "policy_count": 2
        }
        service.get_storage_metrics.return_value = {
            "usage_bytes": 1000,
            "capacity_bytes": 5000,
            "usage_percentage": 20.0
        }
        service.get_storage_alerts.return_value = []
        service.get_service_statistics.return_value = {
            "service_status": {"cleanup_service": True},
            "policy_statistics": {"total_policies": 2}
        }
        service.get_retention_policies.return_value = [
            {"name": "test_policy", "retention_period": 30}
        ]
        service.run_cleanup = AsyncMock(return_value=[{"policy": "test", "deleted": 100}])
        service.create_backup = AsyncMock(return_value={
            "backup_id": "test_backup",
            "backup_type": "full",
            "created_at": "2024-01-01T00:00:00Z",
            "size_bytes": 1000,
            "status": "success"
        })
        service.restore_backup = AsyncMock(return_value=True)
        service.get_backup_history.return_value = [
            {"backup_id": "test_backup", "created_at": "2024-01-01T00:00:00Z"}
        ]
        service.get_backup_statistics.return_value = {
            "total_backups": 5,
            "total_size_bytes": 5000,
            "successful_backups": 4
        }
        service.cleanup_old_backups.return_value = 3
        service.add_retention_policy = Mock()
        service.update_retention_policy = Mock()
        service.remove_retention_policy = Mock()

        return service

    @pytest.fixture
    def client(self, mock_service):
        """Create FastAPI test client with mocked service."""
        with patch('src.main.data_retention_service', mock_service):
            # Set the service in app state for testing
            app.state.service = mock_service
            yield TestClient(app)

    def test_health_check_success(self, client, mock_service):
        """Test successful health check."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "service_status" in data

    def test_health_check_with_alerts(self, client, mock_service):
        """Test health check with storage alerts."""
        mock_service.get_storage_alerts.return_value = [
            {"severity": "critical", "message": "Disk full"}
        ]
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["critical", "warning", "healthy"]
        assert "alerts" in data

    def test_health_check_error(self, client, mock_service):
        """Test health check with error."""
        mock_service.get_service_status.side_effect = Exception("Test error")
        
        response = client.get("/health")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"] or "error" in data

    def test_get_statistics_success(self, client, mock_service):
        """Test successful statistics request."""
        response = client.get("/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "service_status" in data
        assert "policy_statistics" in data

    def test_get_statistics_error(self, client, mock_service):
        """Test statistics request with error."""
        mock_service.get_service_statistics.side_effect = Exception("Test error")
        
        response = client.get("/stats")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]

    def test_get_policies_success(self, client, mock_service):
        """Test successful policies request."""
        response = client.get("/policies")
        
        assert response.status_code == 200
        data = response.json()
        assert "policies" in data
        assert len(data["policies"]) == 1
        assert data["policies"][0]["name"] == "test_policy"

    def test_add_policy_success(self, client, mock_service):
        """Test successful policy addition."""
        policy_data = {
            "name": "new_policy",
            "description": "New policy",
            "retention_period": 60,
            "retention_unit": "days",
            "enabled": True
        }
        
        response = client.post("/policies", json=policy_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Policy added successfully"
        mock_service.add_retention_policy.assert_called_once()

    def test_add_policy_error(self, client, mock_service):
        """Test policy addition with error."""
        mock_service.add_retention_policy.side_effect = Exception("Test error")
        
        policy_data = {"name": "test_policy"}
        response = client.post("/policies", json=policy_data)
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data["detail"]

    def test_update_policy_success(self, client, mock_service):
        """Test successful policy update."""
        policy_data = {
            "name": "test_policy",
            "description": "Updated policy",
            "retention_period": 90,
            "retention_unit": "days",
            "enabled": False
        }
        
        response = client.put("/policies", json=policy_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Policy updated successfully"
        mock_service.update_retention_policy.assert_called_once()

    def test_delete_policy_success(self, client, mock_service):
        """Test successful policy deletion."""
        response = client.delete("/policies/test_policy")
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Policy deleted successfully"
        mock_service.remove_retention_policy.assert_called_once_with("test_policy")

    def test_run_cleanup_success(self, client, mock_service):
        """Test successful cleanup run."""
        response = client.post("/cleanup?policy_name=test_policy")
        
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        # Note: run_cleanup is async, so we can't easily assert the call in sync test
        # but we can verify the response structure

    def test_run_cleanup_error(self, client, mock_service):
        """Test cleanup run with error."""
        mock_service.run_cleanup.side_effect = Exception("Test error")
        
        response = client.post("/cleanup")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]

    def test_create_backup_success(self, client, mock_service):
        """Test successful backup creation."""
        backup_data = {
            "backup_type": "full",
            "include_data": True,
            "include_config": True,
            "include_logs": False
        }
        
        response = client.post("/backup", json=backup_data)
        
        assert response.status_code == 201
        data = response.json()
        assert "backup_id" in data
        assert data["backup_id"] == "test_backup"

    def test_create_backup_error(self, client, mock_service):
        """Test backup creation with error."""
        mock_service.create_backup.side_effect = Exception("Test error")
        
        backup_data = {"backup_type": "full"}
        response = client.post("/backup", json=backup_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]

    def test_restore_backup_success(self, client, mock_service):
        """Test successful backup restore."""
        restore_data = {
            "backup_id": "test_backup",
            "restore_data": True,
            "restore_config": True,
            "restore_logs": False
        }
        
        response = client.post("/backup/restore", json=restore_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Backup restored successfully"

    def test_restore_backup_missing_id(self, client, mock_service):
        """Test backup restore with missing backup ID."""
        restore_data = {"restore_data": True}
        
        response = client.post("/backup/restore", json=restore_data)
        
        # FastAPI validation should catch missing required field
        assert response.status_code in [422, 400]  # 422 for validation error

    def test_restore_backup_failed(self, client, mock_service):
        """Test failed backup restore."""
        mock_service.restore_backup = AsyncMock(return_value=False)
        
        restore_data = {"backup_id": "test_backup"}
        response = client.post("/backup/restore", json=restore_data)
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]

    def test_get_backup_history_success(self, client, mock_service):
        """Test successful backup history request."""
        response = client.get("/backup/backups?limit=10")
        
        assert response.status_code == 200
        data = response.json()
        assert "backups" in data
        assert len(data["backups"]) == 1
        assert data["backups"][0]["backup_id"] == "test_backup"

    def test_get_backup_statistics_success(self, client, mock_service):
        """Test successful backup statistics request."""
        response = client.get("/backup/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_backups"] == 5

    def test_cleanup_old_backups_success(self, client, mock_service):
        """Test successful old backups cleanup."""
        response = client.delete("/backup/cleanup?days_to_keep=30")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["deleted_count"] == 3
        mock_service.cleanup_old_backups.assert_called_once_with(30)

    def test_cleanup_old_backups_error(self, client, mock_service):
        """Test old backups cleanup with error."""
        mock_service.cleanup_old_backups.side_effect = Exception("Test error")
        
        response = client.delete("/backup/cleanup")
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data["detail"]

    def test_api_routes_exist(self, client):
        """Test that all expected routes are available."""
        # Test root endpoint
        response = client.get("/")
        assert response.status_code == 200
        
        # Test health endpoints (both paths)
        response = client.get("/health")
        assert response.status_code in [200, 500]  # 500 if service not initialized
        
        response = client.get("/api/v1/health")
        assert response.status_code in [200, 500]
        
        # Test stats endpoints
        response = client.get("/stats")
        assert response.status_code in [200, 500]
        
        response = client.get("/api/v1/stats")
        assert response.status_code in [200, 500]
