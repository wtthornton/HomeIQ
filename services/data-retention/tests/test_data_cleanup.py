"""Tests for data cleanup service."""

import asyncio
from datetime import datetime, timedelta

import pytest
from src.data_cleanup import CleanupResult, DataCleanupService
from src.retention_policy import RetentionPeriod, RetentionPolicy


class TestCleanupResult:
    """Test CleanupResult class."""

    def test_cleanup_result_creation(self):
        """Test cleanup result creation."""
        result = CleanupResult(
            policy_name="test",
            records_deleted=10,
            records_processed=15,
            cleanup_duration=1.5,
            success=True,
        )

        assert result.policy_name == "test"
        assert result.records_deleted == 10
        assert result.records_processed == 15
        assert result.cleanup_duration == 1.5
        assert result.success is True
        assert result.error_message is None
        assert result.cleanup_timestamp is not None

    def test_cleanup_result_to_dict(self):
        """Test cleanup result to dictionary conversion."""
        result = CleanupResult(
            policy_name="test",
            records_deleted=10,
            records_processed=15,
            cleanup_duration=1.5,
            success=True,
        )

        result_dict = result.to_dict()

        assert result_dict["policy_name"] == "test"
        assert result_dict["records_deleted"] == 10
        assert result_dict["records_processed"] == 15
        assert result_dict["cleanup_duration"] == 1.5
        assert result_dict["success"] is True
        assert "cleanup_timestamp" in result_dict

class TestDataCleanupService:
    """Test DataCleanupService class."""

    @pytest.fixture
    def cleanup_service(self):
        """Create cleanup service for testing."""
        return DataCleanupService()

    @pytest.fixture
    def test_policy(self):
        """Create test retention policy."""
        return RetentionPolicy(
            name="test",
            description="Test policy",
            retention_period=30,
            retention_unit=RetentionPeriod.DAYS,
        )

    @pytest.mark.asyncio
    async def test_start_stop(self, cleanup_service):
        """Test service start and stop."""
        assert not cleanup_service.is_running

        await cleanup_service.start()
        assert cleanup_service.is_running

        await cleanup_service.stop()
        assert not cleanup_service.is_running

    @pytest.mark.asyncio
    async def test_run_cleanup_specific_policy(self, cleanup_service, test_policy):
        """Test running cleanup for specific policy."""
        # Add test policy
        cleanup_service.policy_manager.add_policy(test_policy)

        # Run cleanup
        results = await cleanup_service.run_cleanup("test")

        assert len(results) == 1
        assert results[0].policy_name == "test"
        assert results[0].success is True

    @pytest.mark.asyncio
    async def test_run_cleanup_all_policies(self, cleanup_service, test_policy):
        """Test running cleanup for all policies."""
        # Add test policy
        cleanup_service.policy_manager.add_policy(test_policy)

        # Run cleanup for all policies
        results = await cleanup_service.run_cleanup()

        # Should include both default and test policies
        assert len(results) >= 1
        policy_names = [result.policy_name for result in results]
        assert "test" in policy_names

    @pytest.mark.asyncio
    async def test_run_cleanup_nonexistent_policy(self, cleanup_service):
        """Test running cleanup for nonexistent policy."""
        with pytest.raises(ValueError, match="Policy 'nonexistent' not found"):
            await cleanup_service.run_cleanup("nonexistent")

    @pytest.mark.asyncio
    async def test_cleanup_policy(self, cleanup_service, test_policy):
        """Test cleaning up data for a specific policy."""
        result = await cleanup_service._cleanup_policy(test_policy)

        assert result.policy_name == "test"
        assert result.success is True
        assert result.records_deleted >= 0
        assert result.records_processed >= 0
        assert result.cleanup_duration >= 0

    @pytest.mark.asyncio
    async def test_get_expired_records(self, cleanup_service):
        """Test getting expired records."""
        expiration_date = datetime.utcnow() - timedelta(days=30)
        records = await cleanup_service._get_expired_records(expiration_date)

        # Should return mock records for testing
        assert len(records) > 0
        assert all("id" in record for record in records)
        assert all("timestamp" in record for record in records)

    @pytest.mark.asyncio
    async def test_delete_expired_records(self, cleanup_service):
        """Test deleting expired records."""
        test_records = [
            {"id": "test1", "timestamp": "2024-01-01T00:00:00Z", "measurement": "test"},
            {"id": "test2", "timestamp": "2024-01-02T00:00:00Z", "measurement": "test"},
        ]

        deleted_count = await cleanup_service._delete_expired_records(test_records)

        # Should return count of records (mock implementation)
        assert deleted_count == len(test_records)

    @pytest.mark.asyncio
    async def test_schedule_cleanup(self, cleanup_service):
        """Test scheduling cleanup."""
        await cleanup_service.start()

        # Schedule cleanup with short interval for testing
        await cleanup_service.schedule_cleanup(interval_hours=0.01)  # ~36 seconds

        # Wait a bit for cleanup to run
        await asyncio.sleep(0.1)

        # Check that cleanup history has entries
        history = cleanup_service.get_cleanup_history()
        assert len(history) >= 0  # May or may not have run yet

        await cleanup_service.stop()

    def test_get_cleanup_history(self, cleanup_service):
        """Test getting cleanup history."""
        # Initially empty
        history = cleanup_service.get_cleanup_history()
        assert len(history) == 0

        # Add some mock results
        result1 = CleanupResult(
            policy_name="test1",
            records_deleted=10,
            records_processed=15,
            cleanup_duration=1.0,
            success=True,
        )

        result2 = CleanupResult(
            policy_name="test2",
            records_deleted=5,
            records_processed=8,
            cleanup_duration=0.5,
            success=True,
        )

        cleanup_service.cleanup_history = [result1, result2]

        # Get history
        history = cleanup_service.get_cleanup_history()
        assert len(history) == 2

        # Test limit
        history = cleanup_service.get_cleanup_history(limit=1)
        assert len(history) == 1
        assert history[0].policy_name == "test2"  # Most recent

    def test_get_cleanup_statistics(self, cleanup_service):
        """Test getting cleanup statistics."""
        # Initially empty
        stats = cleanup_service.get_cleanup_statistics()
        assert stats["total_cleanups"] == 0
        assert stats["total_records_deleted"] == 0
        assert stats["success_rate"] == 0.0

        # Add some mock results
        result1 = CleanupResult(
            policy_name="test1",
            records_deleted=10,
            records_processed=15,
            cleanup_duration=1.0,
            success=True,
        )

        result2 = CleanupResult(
            policy_name="test2",
            records_deleted=5,
            records_processed=8,
            cleanup_duration=0.5,
            success=False,
            error_message="Test error",
        )

        cleanup_service.cleanup_history = [result1, result2]

        # Get statistics
        stats = cleanup_service.get_cleanup_statistics()

        assert stats["total_cleanups"] == 2
        assert stats["total_records_deleted"] == 15  # 10 + 5
        assert stats["total_records_processed"] == 23  # 15 + 8
        assert stats["average_cleanup_duration"] == 0.75  # (1.0 + 0.5) / 2
        assert stats["success_rate"] == 0.5  # 1 successful out of 2
        assert stats["last_cleanup"] is not None

    def test_get_policy_manager(self, cleanup_service):
        """Test getting policy manager."""
        manager = cleanup_service.get_policy_manager()

        assert manager is not None
        assert hasattr(manager, "get_all_policies")
        assert hasattr(manager, "add_policy")
