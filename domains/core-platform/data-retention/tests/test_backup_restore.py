"""Tests for backup and restore functionality."""

import asyncio
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.backup_restore import BackupInfo, BackupRestoreService


class TestBackupInfo:
    """Test BackupInfo dataclass."""

    def test_backup_info_creation(self):
        """Test creating BackupInfo."""
        backup_info = BackupInfo(
            backup_id="test_backup",
            backup_type="full",
            created_at=datetime.utcnow(),
            size_bytes=1024,
            file_path="/backups/test_backup.tar.gz",
            metadata={"test": "data"}
        )

        assert backup_info.backup_id == "test_backup"
        assert backup_info.backup_type == "full"
        assert backup_info.size_bytes == 1024
        assert backup_info.success is True
        assert backup_info.error_message is None

    def test_backup_info_to_dict(self):
        """Test converting BackupInfo to dictionary."""
        now = datetime.utcnow()
        backup_info = BackupInfo(
            backup_id="test_backup",
            backup_type="full",
            created_at=now,
            size_bytes=1024,
            file_path="/backups/test_backup.tar.gz",
            metadata={"test": "data"}
        )

        result = backup_info.to_dict()

        assert result["backup_id"] == "test_backup"
        assert result["backup_type"] == "full"
        assert result["created_at"] == now.isoformat()
        assert result["size_bytes"] == 1024
        assert result["success"] is True


class TestBackupRestoreService:
    """Test BackupRestoreService."""

    @pytest.fixture
    def service(self):
        """Create BackupRestoreService instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            service = BackupRestoreService(backup_dir=temp_dir)
            yield service

    @pytest.mark.asyncio
    async def test_start_stop(self, service):
        """Test starting and stopping the service."""
        assert not service.is_running

        await service.start()
        assert service.is_running

        await service.stop()
        assert not service.is_running

    @pytest.mark.asyncio
    async def test_start_already_running(self, service):
        """Test starting service when already running."""
        await service.start()
        assert service.is_running

        # Should not raise exception
        await service.start()
        assert service.is_running

    @pytest.mark.asyncio
    async def test_create_backup_full(self, service):
        """Test creating a full backup."""
        backup_info = await service.create_backup(
            backup_type="full",
            include_data=True,
            include_config=True,
            include_logs=False
        )

        assert backup_info.backup_id.startswith("full_")
        assert backup_info.backup_type == "full"
        assert backup_info.success is True
        assert backup_info.size_bytes > 0
        assert backup_info.error_message is None

        # Check backup file exists
        backup_file = Path(service.backup_dir) / f"{backup_info.backup_id}.tar.gz"
        assert backup_file.exists()

    @pytest.mark.asyncio
    async def test_create_backup_config_only(self, service):
        """Test creating a config-only backup."""
        backup_info = await service.create_backup(
            backup_type="config",
            include_data=False,
            include_config=True,
            include_logs=False
        )

        assert backup_info.backup_type == "config"
        assert backup_info.success is True
        assert backup_info.metadata["include_data"] is False
        assert backup_info.metadata["include_config"] is True

    @pytest.mark.asyncio
    async def test_create_backup_with_logs(self, service):
        """Test creating a backup with logs."""
        backup_info = await service.create_backup(
            backup_type="full",
            include_data=True,
            include_config=True,
            include_logs=True
        )

        assert backup_info.success is True
        assert backup_info.metadata["include_logs"] is True

    @pytest.mark.asyncio
    async def test_backup_data_mock(self, service):
        """Test backing up data with mock implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            metadata = {}

            await service._backup_data(temp_path, metadata)

            # Check data file was created
            data_file = temp_path / "data_export.json"
            assert data_file.exists()

            # Check data content
            with open(data_file) as f:
                data = json.load(f)

            assert "events" in data
            assert len(data["events"]) == 2
            assert metadata["data_records"] == 2

    @pytest.mark.asyncio
    async def test_backup_data_with_influxdb(self, service):
        """Test backing up data with InfluxDB client."""
        # Mock InfluxDB client
        mock_client = Mock()
        mock_record = Mock()
        mock_record.get_time.return_value = datetime.utcnow()
        mock_record.get_measurement.return_value = "home_assistant_event"
        mock_record.get_field.return_value = "temperature"
        mock_record.get_value.return_value = 20.5
        mock_record.values = {"entity_id": "sensor.temp"}

        mock_table = Mock()
        mock_table.records = [mock_record]

        mock_result = [mock_table]
        mock_client.query = AsyncMock(return_value=mock_result)

        service.influxdb_client = mock_client

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            metadata = {}

            await service._backup_data(temp_path, metadata)

            # Check data file was created
            data_file = temp_path / "data_export.json"
            assert data_file.exists()

            # Check data content
            with open(data_file) as f:
                data = json.load(f)

            assert "events" in data
            assert len(data["events"]) == 1
            assert data["events"][0]["measurement"] == "home_assistant_event"
            assert data["events"][0]["field"] == "temperature"
            assert data["events"][0]["value"] == 20.5

    @pytest.mark.asyncio
    async def test_backup_config(self, service):
        """Test backing up configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            metadata = {}

            # Create mock config files
            config_file = temp_path / "test_config.yaml"
            config_file.write_text("test: config")

            with patch('os.path.exists', return_value=True):
                with patch('shutil.copy2') as mock_copy:
                    await service._backup_config(temp_path, metadata)

                    assert "config_files" in metadata
                    mock_copy.assert_called()

    @pytest.mark.asyncio
    async def test_backup_logs(self, service):
        """Test backing up logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            metadata = {}

            # Create mock log files
            log_file = temp_path / "test.log"
            log_file.write_text("test log content")

            with patch('os.path.exists', return_value=True):
                with patch('os.walk', return_value=[(str(temp_path), [], ["test.log"])]):
                    with patch('shutil.copy2') as mock_copy:
                        await service._backup_logs(temp_path, metadata)

                        assert "log_files" in metadata
                        mock_copy.assert_called()

    @pytest.mark.asyncio
    async def test_restore_backup_success(self, service):
        """Test successful backup restore."""
        # Create a backup first
        backup_info = await service.create_backup("full")
        assert backup_info.success

        # Restore the backup
        result = await service.restore_backup(backup_info.backup_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_restore_backup_not_found(self, service):
        """Test restoring non-existent backup."""
        result = await service.restore_backup("nonexistent_backup")
        assert result is False

    @pytest.mark.asyncio
    async def test_restore_data_mock(self, service):
        """Test restoring data with mock implementation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock data file
            data_file = temp_path / "data_export.json"
            mock_data = {
                "events": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "measurement": "home_assistant_event",
                        "field": "temperature",
                        "value": 20.5,
                        "tags": {"entity_id": "sensor.temp"}
                    }
                ]
            }

            with open(data_file, 'w') as f:
                json.dump(mock_data, f)

            # Should not raise exception with mock implementation
            await service._restore_data(temp_path)

    @pytest.mark.asyncio
    async def test_restore_data_with_influxdb(self, service):
        """Test restoring data with InfluxDB client."""
        # Mock InfluxDB client
        mock_write_api = Mock()
        mock_client = Mock()
        mock_client.write_api.return_value = mock_write_api
        service.influxdb_client = mock_client

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock data file
            data_file = temp_path / "data_export.json"
            mock_data = {
                "events": [
                    {
                        "timestamp": "2024-01-01T00:00:00Z",
                        "measurement": "home_assistant_event",
                        "field": "temperature",
                        "value": 20.5,
                        "tags": {"entity_id": "sensor.temp"}
                    }
                ]
            }

            with open(data_file, 'w') as f:
                json.dump(mock_data, f)

            await service._restore_data(temp_path)

            # Verify write API was called
            mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_restore_config(self, service):
        """Test restoring configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock config directory
            config_dir = temp_path / "config"
            config_dir.mkdir()
            config_file = config_dir / "test_config.yaml"
            config_file.write_text("test: config")

            with patch('shutil.copy2') as mock_copy:
                await service._restore_config(temp_path)
                mock_copy.assert_called()

    @pytest.mark.asyncio
    async def test_restore_logs(self, service):
        """Test restoring logs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create mock logs directory
            logs_dir = temp_path / "logs"
            logs_dir.mkdir()
            log_file = logs_dir / "test.log"
            log_file.write_text("test log content")

            with patch('shutil.copy2') as mock_copy:
                await service._restore_logs(temp_path)
                mock_copy.assert_called()

    @pytest.mark.asyncio
    async def test_schedule_backups(self, service):
        """Test scheduling backups."""
        await service.start()

        # Schedule backups every 1 second for testing
        await service.schedule_backups(interval_hours=0.001, backup_type="full")

        # Wait a bit for backup to complete
        await asyncio.sleep(0.1)

        # Check backup task is running
        assert service.backup_task is not None
        assert not service.backup_task.done()

        await service.stop()

    @pytest.mark.asyncio
    async def test_schedule_backups_already_running(self, service):
        """Test scheduling backups when already running."""
        await service.start()

        # Schedule first backup task
        await service.schedule_backups(interval_hours=1)
        first_task = service.backup_task

        # Try to schedule another backup task
        await service.schedule_backups(interval_hours=1)

        # Should still be the same task
        assert service.backup_task is first_task

        await service.stop()

    def test_get_backup_history(self, service):
        """Test getting backup history."""
        # Add some mock backup history
        service.backup_history = [
            BackupInfo("backup1", "full", datetime.utcnow(), 1000, "/path1", {}),
            BackupInfo("backup2", "config", datetime.utcnow(), 500, "/path2", {}),
            BackupInfo("backup3", "full", datetime.utcnow(), 1500, "/path3", {})
        ]

        history = service.get_backup_history(limit=2)
        assert len(history) == 2
        assert history[0].backup_id == "backup2"
        assert history[1].backup_id == "backup3"

    def test_get_backup_statistics(self, service):
        """Test getting backup statistics."""
        # Add mock backup history
        service.backup_history = [
            BackupInfo("backup1", "full", datetime.utcnow(), 1000, "/path1", {}, True),
            BackupInfo("backup2", "config", datetime.utcnow(), 500, "/path2", {}, True),
            BackupInfo("backup3", "full", datetime.utcnow(), 1500, "/path3", {}, False, "Error")
        ]

        stats = service.get_backup_statistics()

        assert stats["total_backups"] == 3
        assert stats["successful_backups"] == 2
        assert stats["failed_backups"] == 1
        assert stats["total_size_bytes"] == 1500
        assert stats["average_size_bytes"] == 750
        assert stats["success_rate"] == 2/3
        assert stats["last_backup"] is not None

    def test_get_backup_statistics_empty(self, service):
        """Test getting backup statistics with no backups."""
        stats = service.get_backup_statistics()

        assert stats["total_backups"] == 0
        assert stats["successful_backups"] == 0
        assert stats["failed_backups"] == 0
        assert stats["total_size_bytes"] == 0
        assert stats["average_size_bytes"] == 0
        assert stats["success_rate"] == 0
        assert stats["last_backup"] is None

    def test_cleanup_old_backups(self, service):
        """Test cleaning up old backups."""
        # Create mock backup files
        backup_dir = Path(service.backup_dir)

        # Create old backup file
        old_backup = backup_dir / "old_backup.tar.gz"
        old_backup.write_bytes(b"test")

        # Create recent backup file
        recent_backup = backup_dir / "recent_backup.tar.gz"
        recent_backup.write_bytes(b"test")

        # Mock file modification time
        old_time = (datetime.utcnow() - timedelta(days=35)).timestamp()
        recent_time = (datetime.utcnow() - timedelta(days=5)).timestamp()

        # Mock the Path.stat method
        with patch('pathlib.Path.stat') as mock_stat:
            def stat_side_effect():
                mock_stat_result = Mock()
                # Get the path from the calling context
                import inspect
                frame = inspect.currentframe()
                while frame:
                    if 'backup_file' in frame.f_locals:
                        path_str = str(frame.f_locals['backup_file'])
                        if 'old_backup' in path_str:
                            mock_stat_result.st_mtime = old_time
                        else:
                            mock_stat_result.st_mtime = recent_time
                        break
                    frame = frame.f_back
                else:
                    mock_stat_result.st_mtime = recent_time
                return mock_stat_result

            mock_stat.side_effect = stat_side_effect

            deleted_count = service.cleanup_old_backups(days_to_keep=30)

            assert deleted_count == 1
            assert not old_backup.exists()
            assert recent_backup.exists()

    @pytest.mark.asyncio
    async def test_backup_error_handling(self, service):
        """Test backup error handling."""
        with patch('tarfile.open', side_effect=Exception("Test error")):
            backup_info = await service.create_backup("full")

            assert backup_info.success is False
            assert backup_info.error_message == "Test error"
            assert backup_info.size_bytes == 0

    @pytest.mark.asyncio
    async def test_restore_error_handling(self, service):
        """Test restore error handling."""
        # Create a backup first
        backup_info = await service.create_backup("full")
        assert backup_info.success

        # Mock restore to fail
        with patch.object(service, '_restore_data', side_effect=Exception("Test error")):
            result = await service.restore_backup(backup_info.backup_id)
            assert result is False
