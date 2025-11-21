"""Tests for main data retention service."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.main import DataRetentionService
from src.retention_policy import RetentionPeriod


class TestDataRetentionService:
    """Test DataRetentionService."""

    @pytest.fixture
    def service(self):
        """Create DataRetentionService instance."""
        return DataRetentionService()

    def test_initialization(self, service):
        """Test service initialization."""
        assert service.policy_manager is not None
        assert service.cleanup_service is None
        assert service.storage_monitor is None
        assert service.compression_service is None
        assert service.backup_service is None
        assert service.cleanup_interval_hours == 24
        assert service.monitoring_interval_minutes == 5
        assert service.compression_interval_hours == 24
        assert service.backup_interval_hours == 24
        assert service.backup_dir == "/backups"

    @pytest.mark.asyncio
    async def test_start_stop(self, service):
        """Test starting and stopping the service."""
        # Mock services
        mock_cleanup = Mock()
        mock_cleanup.start = AsyncMock()
        mock_cleanup.stop = AsyncMock()
        mock_cleanup.schedule_cleanup = AsyncMock()

        mock_storage = Mock()
        mock_storage.start = AsyncMock()
        mock_storage.stop = AsyncMock()
        mock_storage.schedule_monitoring = AsyncMock()

        mock_compression = Mock()
        mock_compression.start = AsyncMock()
        mock_compression.stop = AsyncMock()
        mock_compression.schedule_compression = AsyncMock()

        mock_backup = Mock()
        mock_backup.start = AsyncMock()
        mock_backup.stop = AsyncMock()
        mock_backup.schedule_backups = AsyncMock()

        with patch("src.main.DataCleanupService", return_value=mock_cleanup), \
             patch("src.main.StorageMonitor", return_value=mock_storage), \
             patch("src.main.DataCompressionService", return_value=mock_compression), \
             patch("src.main.BackupRestoreService", return_value=mock_backup):

            await service.start()

            assert service.cleanup_service is not None
            assert service.storage_monitor is not None
            assert service.compression_service is not None
            assert service.backup_service is not None

            # Verify services were started
            mock_cleanup.start.assert_called_once()
            mock_storage.start.assert_called_once()
            mock_compression.start.assert_called_once()
            mock_backup.start.assert_called_once()

            # Verify periodic tasks were scheduled
            mock_cleanup.schedule_cleanup.assert_called_once_with(24)
            mock_storage.schedule_monitoring.assert_called_once_with(5)
            mock_compression.schedule_compression.assert_called_once_with(24)
            mock_backup.schedule_backups.assert_called_once_with(24)

            await service.stop()

            # Verify services were stopped
            mock_cleanup.stop.assert_called_once()
            mock_storage.stop.assert_called_once()
            mock_compression.stop.assert_called_once()
            mock_backup.stop.assert_called_once()

    def test_get_service_status(self, service):
        """Test getting service status."""
        status = service.get_service_status()

        assert status["cleanup_service"] is False
        assert status["storage_monitor"] is False
        assert status["compression_service"] is False
        assert status["backup_service"] is False
        assert status["policy_count"] >= 0  # May have default policy

    def test_get_retention_policies(self, service):
        """Test getting retention policies."""
        initial_policies = service.get_retention_policies()
        initial_count = len(initial_policies)

        # Add a policy
        policy_data = {
            "name": "test_policy",
            "description": "Test policy",
            "retention_period": 30,
            "retention_unit": RetentionPeriod.DAYS,
            "enabled": True,
        }
        service.add_retention_policy(policy_data)

        policies = service.get_retention_policies()
        assert len(policies) == initial_count + 1
        # Check that our policy is in the list
        policy_names = [p["name"] for p in policies]
        assert "test_policy" in policy_names

    def test_add_retention_policy(self, service):
        """Test adding a retention policy."""
        policy_data = {
            "name": "test_policy",
            "description": "Test policy",
            "retention_period": 30,
            "retention_unit": RetentionPeriod.DAYS,
            "enabled": True,
        }

        service.add_retention_policy(policy_data)

        policies = service.policy_manager.get_all_policies()
        # Should have at least 1 policy (the one we added, plus any defaults)
        assert len(policies) >= 1
        # Check that our policy is in the list
        policy_names = [p.name for p in policies]
        assert "test_policy" in policy_names

        # Find our specific policy
        test_policy = next(p for p in policies if p.name == "test_policy")
        assert test_policy.description == "Test policy"
        assert test_policy.retention_period == 30
        assert test_policy.retention_unit == RetentionPeriod.DAYS
        assert test_policy.enabled is True
        # Remove the old assertion since we already checked the policy exists

    def test_update_retention_policy(self, service):
        """Test updating a retention policy."""
        # Add initial policy
        policy_data = {
            "name": "test_policy",
            "description": "Test policy",
            "retention_period": 30,
            "retention_unit": RetentionPeriod.DAYS,
            "enabled": True,
        }
        service.add_retention_policy(policy_data)

        # Update policy
        updated_data = {
            "name": "test_policy",
            "description": "Updated policy",
            "retention_period": 60,
            "retention_unit": RetentionPeriod.DAYS,
            "enabled": False,
        }
        service.update_retention_policy(updated_data)

        policies = service.policy_manager.get_all_policies()
        # Should have at least 1 policy (the one we added, plus any defaults)
        assert len(policies) >= 1
        # Check that our policy is in the list
        policy_names = [p.name for p in policies]
        assert "test_policy" in policy_names
        # Find our specific policy
        test_policy = next(p for p in policies if p.name == "test_policy")
        assert test_policy.description == "Updated policy"
        assert test_policy.retention_period == 60
        assert test_policy.enabled is False

    def test_remove_retention_policy(self, service):
        """Test removing a retention policy."""
        # Add policy
        policy_data = {
            "name": "test_policy",
            "description": "Test policy",
            "retention_period": 30,
            "retention_unit": RetentionPeriod.DAYS,
            "enabled": True,
        }
        service.add_retention_policy(policy_data)

        # Remove policy
        service.remove_retention_policy("test_policy")

        policies = service.policy_manager.get_all_policies()
        # Should not have our test policy anymore
        policy_names = [p.name for p in policies]
        assert "test_policy" not in policy_names

    @pytest.mark.asyncio
    async def test_run_cleanup_not_initialized(self, service):
        """Test running cleanup when service not initialized."""
        with pytest.raises(RuntimeError, match="Cleanup service not initialized"):
            await service.run_cleanup()

    @pytest.mark.asyncio
    async def test_run_cleanup(self, service):
        """Test running cleanup."""
        # Mock cleanup service
        mock_cleanup = Mock()
        mock_result = Mock()
        mock_result.to_dict.return_value = {"policy": "test", "deleted": 100}
        mock_cleanup.run_cleanup = AsyncMock(return_value=[mock_result])

        service.cleanup_service = mock_cleanup

        results = await service.run_cleanup("test_policy")

        assert len(results) == 1
        assert results[0]["policy"] == "test"
        assert results[0]["deleted"] == 100
        mock_cleanup.run_cleanup.assert_called_once_with("test_policy")

    def test_get_storage_metrics_not_initialized(self, service):
        """Test getting storage metrics when service not initialized."""
        metrics = service.get_storage_metrics()
        assert metrics is None

    def test_get_storage_metrics(self, service):
        """Test getting storage metrics."""
        # Mock storage monitor
        mock_storage = Mock()
        mock_metrics = Mock()
        mock_metrics.to_dict.return_value = {"usage_bytes": 1000, "capacity_bytes": 5000}
        mock_storage.get_current_metrics.return_value = mock_metrics

        service.storage_monitor = mock_storage

        metrics = service.get_storage_metrics()

        assert metrics["usage_bytes"] == 1000
        assert metrics["capacity_bytes"] == 5000

    def test_get_storage_alerts_not_initialized(self, service):
        """Test getting storage alerts when service not initialized."""
        alerts = service.get_storage_alerts()
        assert alerts == []

    def test_get_storage_alerts(self, service):
        """Test getting storage alerts."""
        # Mock storage monitor
        mock_storage = Mock()
        mock_alert = Mock()
        mock_alert.to_dict.return_value = {"severity": "warning", "message": "Low space"}
        mock_storage.get_active_alerts.return_value = [mock_alert]

        service.storage_monitor = mock_storage

        alerts = service.get_storage_alerts()

        assert len(alerts) == 1
        assert alerts[0]["severity"] == "warning"
        assert alerts[0]["message"] == "Low space"

    def test_get_compression_statistics_not_initialized(self, service):
        """Test getting compression statistics when service not initialized."""
        stats = service.get_compression_statistics()
        assert stats == {}

    def test_get_compression_statistics(self, service):
        """Test getting compression statistics."""
        # Mock compression service
        mock_compression = Mock()
        mock_compression.get_compression_statistics.return_value = {
            "compression_ratio": 0.5,
            "space_saved_bytes": 1000,
        }

        service.compression_service = mock_compression

        stats = service.get_compression_statistics()

        assert stats["compression_ratio"] == 0.5
        assert stats["space_saved_bytes"] == 1000

    @pytest.mark.asyncio
    async def test_create_backup_not_initialized(self, service):
        """Test creating backup when service not initialized."""
        with pytest.raises(RuntimeError, match="Backup service not initialized"):
            await service.create_backup()

    @pytest.mark.asyncio
    async def test_create_backup(self, service):
        """Test creating backup."""
        # Mock backup service
        mock_backup = Mock()
        mock_backup_info = Mock()
        mock_backup_info.to_dict.return_value = {
            "backup_id": "test_backup",
            "backup_type": "full",
            "success": True,
        }
        mock_backup.create_backup = AsyncMock(return_value=mock_backup_info)

        service.backup_service = mock_backup

        result = await service.create_backup("full", True, True, False)

        assert result["backup_id"] == "test_backup"
        assert result["backup_type"] == "full"
        assert result["success"] is True
        mock_backup.create_backup.assert_called_once_with(
            backup_type="full",
            include_data=True,
            include_config=True,
            include_logs=False,
        )

    @pytest.mark.asyncio
    async def test_restore_backup_not_initialized(self, service):
        """Test restoring backup when service not initialized."""
        with pytest.raises(RuntimeError, match="Backup service not initialized"):
            await service.restore_backup("test_backup")

    @pytest.mark.asyncio
    async def test_restore_backup(self, service):
        """Test restoring backup."""
        # Mock backup service
        mock_backup = Mock()
        mock_backup.restore_backup = AsyncMock(return_value=True)

        service.backup_service = mock_backup

        result = await service.restore_backup("test_backup", True, True, False)

        assert result is True
        mock_backup.restore_backup.assert_called_once_with(
            backup_id="test_backup",
            restore_data=True,
            restore_config=True,
            restore_logs=False,
        )

    def test_get_backup_history_not_initialized(self, service):
        """Test getting backup history when service not initialized."""
        history = service.get_backup_history()
        assert history == []

    def test_get_backup_history(self, service):
        """Test getting backup history."""
        # Mock backup service
        mock_backup = Mock()
        mock_backup_info = Mock()
        mock_backup_info.to_dict.return_value = {
            "backup_id": "test_backup",
            "created_at": "2024-01-01T00:00:00Z",
        }
        mock_backup.get_backup_history.return_value = [mock_backup_info]

        service.backup_service = mock_backup

        history = service.get_backup_history(10)

        assert len(history) == 1
        assert history[0]["backup_id"] == "test_backup"
        mock_backup.get_backup_history.assert_called_once_with(10)

    def test_get_backup_statistics_not_initialized(self, service):
        """Test getting backup statistics when service not initialized."""
        stats = service.get_backup_statistics()
        assert stats == {}

    def test_get_backup_statistics(self, service):
        """Test getting backup statistics."""
        # Mock backup service
        mock_backup = Mock()
        mock_backup.get_backup_statistics.return_value = {
            "total_backups": 5,
            "successful_backups": 4,
            "failed_backups": 1,
        }

        service.backup_service = mock_backup

        stats = service.get_backup_statistics()

        assert stats["total_backups"] == 5
        assert stats["successful_backups"] == 4
        assert stats["failed_backups"] == 1

    def test_cleanup_old_backups_not_initialized(self, service):
        """Test cleaning up old backups when service not initialized."""
        deleted_count = service.cleanup_old_backups()
        assert deleted_count == 0

    def test_cleanup_old_backups(self, service):
        """Test cleaning up old backups."""
        # Mock backup service
        mock_backup = Mock()
        mock_backup.cleanup_old_backups.return_value = 3

        service.backup_service = mock_backup

        deleted_count = service.cleanup_old_backups(30)

        assert deleted_count == 3
        mock_backup.cleanup_old_backups.assert_called_once_with(30)

    def test_get_service_statistics(self, service):
        """Test getting comprehensive service statistics."""
        # Mock services
        mock_cleanup = Mock()
        mock_cleanup.get_cleanup_statistics.return_value = {"cleanups_run": 10}

        mock_storage = Mock()
        mock_storage.get_storage_statistics.return_value = {"total_space": 1000}

        mock_compression = Mock()
        mock_compression.get_compression_statistics.return_value = {"ratio": 0.5}

        mock_backup = Mock()
        mock_backup.get_backup_statistics.return_value = {"total_backups": 5}

        service.cleanup_service = mock_cleanup
        service.storage_monitor = mock_storage
        service.compression_service = mock_compression
        service.backup_service = mock_backup

        stats = service.get_service_statistics()

        assert "service_status" in stats
        assert "policy_statistics" in stats
        assert "cleanup_statistics" in stats
        assert "storage_statistics" in stats
        assert "compression_statistics" in stats
        assert "backup_statistics" in stats

        assert stats["cleanup_statistics"]["cleanups_run"] == 10
        assert stats["storage_statistics"]["total_space"] == 1000
        assert stats["compression_statistics"]["ratio"] == 0.5
        assert stats["backup_statistics"]["total_backups"] == 5
