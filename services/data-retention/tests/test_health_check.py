"""Tests for health check endpoints."""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from aiohttp import web, ClientSession
from aiohttp.test_utils import make_mocked_request

from src.health_check import (
    health_check, get_statistics, get_policies, add_policy,
    update_policy, delete_policy, run_cleanup, create_backup,
    restore_backup, get_backup_history, get_backup_statistics,
    cleanup_old_backups, create_app
)


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
            "success": True
        })
        service.restore_backup = AsyncMock(return_value=True)
        service.get_backup_history.return_value = [
            {"backup_id": "test_backup", "created_at": "2024-01-01T00:00:00Z"}
        ]
        service.get_backup_statistics.return_value = {
            "total_backups": 5,
            "successful_backups": 4
        }
        service.cleanup_old_backups.return_value = 3
        
        return service
    
    @pytest.fixture
    def app(self):
        """Create web application."""
        return create_app()
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_service):
        """Test successful health check."""
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/health')
            response = await health_check(request)
            
            assert response.status == 200
            # For web.json_response, we need to check the body
            assert response.body is not None
    
    @pytest.mark.asyncio
    async def test_health_check_with_alerts(self, mock_service):
        """Test health check with storage alerts."""
        mock_service.get_storage_alerts.return_value = [
            {"severity": "critical", "message": "Disk full"}
        ]
        
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/health')
            response = await health_check(request)
            
            assert response.status == 200
            assert response.body is not None
    
    @pytest.mark.asyncio
    async def test_health_check_error(self, mock_service):
        """Test health check with error."""
        mock_service.get_service_status.side_effect = Exception("Test error")
        
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/health')
            response = await health_check(request)
            
            assert response.status == 500
            assert response.body is not None
    
    @pytest.mark.asyncio
    async def test_get_statistics_success(self, mock_service):
        """Test successful statistics request."""
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/stats')
            response = await get_statistics(request)
            
            assert response.status == 200
            assert response.body is not None
    
    @pytest.mark.asyncio
    async def test_get_statistics_error(self, mock_service):
        """Test statistics request with error."""
        mock_service.get_service_statistics.side_effect = Exception("Test error")

        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/stats')
            response = await get_statistics(request)

            assert response.status == 500
            assert response.body is not None

            data = json.loads(response.body)
            data = json.loads(response.body)
            assert data["error"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_get_policies_success(self, mock_service):
        """Test successful policies request."""
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/policies')
            response = await get_policies(request)

            assert response.status == 200
            assert response.body is not None

            data = json.loads(response.body)
            assert "policies" in data
            assert len(data["policies"]) == 1
            assert data["policies"][0]["name"] == "test_policy"
    
    @pytest.mark.asyncio
    async def test_add_policy_success(self, mock_service):
        """Test successful policy addition."""
        with patch('src.health_check.data_retention_service', mock_service):
            policy_data = {
                "name": "new_policy",
                "description": "New policy",
                "retention_period": 60,
                "retention_unit": "DAYS",
                "enabled": True
            }
            
            request = make_mocked_request('POST', '/policies')
            request.json = AsyncMock(return_value=policy_data)
            response = await add_policy(request)
            
            assert response.status == 201
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["message"] == "Policy added successfully"
            mock_service.add_retention_policy.assert_called_once_with(policy_data)
    
    @pytest.mark.asyncio
    async def test_add_policy_error(self, mock_service):
        """Test policy addition with error."""
        mock_service.add_retention_policy.side_effect = Exception("Test error")
        
        with patch('src.health_check.data_retention_service', mock_service):
            policy_data = {"name": "test_policy"}
            
            request = make_mocked_request('POST', '/policies')
            request.json = AsyncMock(return_value=policy_data)
            response = await add_policy(request)
            
            assert response.status == 400
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["error"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_update_policy_success(self, mock_service):
        """Test successful policy update."""
        with patch('src.health_check.data_retention_service', mock_service):
            policy_data = {
                "name": "test_policy",
                "description": "Updated policy",
                "retention_period": 90,
                "retention_unit": "DAYS",
                "enabled": False
            }
            
            request = make_mocked_request('PUT', '/policies')
            request.json = AsyncMock(return_value=policy_data)
            response = await update_policy(request)
            
            assert response.status == 200
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["message"] == "Policy updated successfully"
            mock_service.update_retention_policy.assert_called_once_with(policy_data)
    
    @pytest.mark.asyncio
    async def test_delete_policy_success(self, mock_service):
        """Test successful policy deletion."""
        with patch('src.health_check.data_retention_service', mock_service):
            # Create a mock request with proper match_info
            request = Mock()
            request.match_info = {'policy_name': 'test_policy'}
            response = await delete_policy(request)
            
            assert response.status == 200
            assert response.body is not None
            mock_service.remove_retention_policy.assert_called_once_with("test_policy")
    
    @pytest.mark.asyncio
    async def test_run_cleanup_success(self, mock_service):
        """Test successful cleanup run."""
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('POST', '/cleanup?policy_name=test_policy')
            response = await run_cleanup(request)
            
            assert response.status == 200
            assert response.body is not None
            
            data = json.loads(response.body)
            assert "results" in data
            assert len(data["results"]) == 1
            assert data["results"][0]["policy"] == "test"
            mock_service.run_cleanup.assert_called_once_with("test_policy")
    
    @pytest.mark.asyncio
    async def test_run_cleanup_error(self, mock_service):
        """Test cleanup run with error."""
        mock_service.run_cleanup.side_effect = Exception("Test error")
        
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('POST', '/cleanup')
            response = await run_cleanup(request)
            
            assert response.status == 500
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["error"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_create_backup_success(self, mock_service):
        """Test successful backup creation."""
        with patch('src.health_check.data_retention_service', mock_service):
            backup_data = {
                "backup_type": "full",
                "include_data": True,
                "include_config": True,
                "include_logs": False
            }
            
            request = make_mocked_request('POST', '/backup')
            request.json = AsyncMock(return_value=backup_data)
            response = await create_backup(request)
            
            assert response.status == 201
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["backup_id"] == "test_backup"
            assert data["success"] is True
            mock_service.create_backup.assert_called_once_with(
                backup_type="full",
                include_data=True,
                include_config=True,
                include_logs=False
            )
    
    @pytest.mark.asyncio
    async def test_create_backup_error(self, mock_service):
        """Test backup creation with error."""
        mock_service.create_backup.side_effect = Exception("Test error")
        
        with patch('src.health_check.data_retention_service', mock_service):
            backup_data = {"backup_type": "full"}
            
            request = make_mocked_request('POST', '/backup')
            request.json = AsyncMock(return_value=backup_data)
            response = await create_backup(request)
            
            assert response.status == 500
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["error"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_restore_backup_success(self, mock_service):
        """Test successful backup restore."""
        with patch('src.health_check.data_retention_service', mock_service):
            restore_data = {
                "backup_id": "test_backup",
                "restore_data": True,
                "restore_config": True,
                "restore_logs": False
            }
            
            request = make_mocked_request('POST', '/restore')
            request.json = AsyncMock(return_value=restore_data)
            response = await restore_backup(request)
            
            assert response.status == 200
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["message"] == "Backup restored successfully"
            mock_service.restore_backup.assert_called_once_with(
                backup_id="test_backup",
                restore_data=True,
                restore_config=True,
                restore_logs=False
            )
    
    @pytest.mark.asyncio
    async def test_restore_backup_missing_id(self, mock_service):
        """Test backup restore with missing backup ID."""
        with patch('src.health_check.data_retention_service', mock_service):
            restore_data = {"restore_data": True}
            
            request = make_mocked_request('POST', '/restore')
            request.json = AsyncMock(return_value=restore_data)
            response = await restore_backup(request)
            
            assert response.status == 400
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["error"] == "backup_id is required"
    
    @pytest.mark.asyncio
    async def test_restore_backup_failed(self, mock_service):
        """Test failed backup restore."""
        mock_service.restore_backup.return_value = False
        
        with patch('src.health_check.data_retention_service', mock_service):
            restore_data = {"backup_id": "test_backup"}
            
            request = make_mocked_request('POST', '/restore')
            request.json = AsyncMock(return_value=restore_data)
            response = await restore_backup(request)
            
            assert response.status == 500
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["error"] == "Backup restore failed"
    
    @pytest.mark.asyncio
    async def test_get_backup_history_success(self, mock_service):
        """Test successful backup history request."""
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/backups?limit=10')
            response = await get_backup_history(request)
            
            assert response.status == 200
            assert response.body is not None
            
            data = json.loads(response.body)
            assert "backups" in data
            assert len(data["backups"]) == 1
            assert data["backups"][0]["backup_id"] == "test_backup"
            mock_service.get_backup_history.assert_called_once_with(10)
    
    @pytest.mark.asyncio
    async def test_get_backup_statistics_success(self, mock_service):
        """Test successful backup statistics request."""
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('GET', '/backup-stats')
            response = await get_backup_statistics(request)
            
            assert response.status == 200
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["total_backups"] == 5
            assert data["successful_backups"] == 4
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups_success(self, mock_service):
        """Test successful old backups cleanup."""
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('DELETE', '/backups/cleanup?days_to_keep=30')
            response = await cleanup_old_backups(request)
            
            assert response.status == 200
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["message"] == "Cleaned up 3 old backup files"
            assert data["deleted_count"] == 3
            mock_service.cleanup_old_backups.assert_called_once_with(30)
    
    @pytest.mark.asyncio
    async def test_cleanup_old_backups_error(self, mock_service):
        """Test old backups cleanup with error."""
        mock_service.cleanup_old_backups.side_effect = Exception("Test error")
        
        with patch('src.health_check.data_retention_service', mock_service):
            request = make_mocked_request('DELETE', '/backups/cleanup')
            response = await cleanup_old_backups(request)
            
            assert response.status == 500
            assert response.body is not None
            
            data = json.loads(response.body)
            assert data["error"] == "Test error"
    
    def test_create_app_routes(self, app):
        """Test that all routes are properly configured."""
        routes = [route.resource for route in app.router.routes()]
        
        # Check that all expected routes exist
        route_paths = [route._path for route in routes if hasattr(route, '_path')]
        
        assert '/health' in route_paths
        assert '/stats' in route_paths
        assert '/policies' in route_paths
        assert '/cleanup' in route_paths
        assert '/backup' in route_paths
        assert '/restore' in route_paths
        assert '/backups' in route_paths
        assert '/backup-stats' in route_paths
        assert '/backups/cleanup' in route_paths
