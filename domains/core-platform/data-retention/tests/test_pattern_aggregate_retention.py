"""Tests for pattern aggregate retention manager."""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, create_autospec

import pytest
from influxdb_client import InfluxDBClient
from influxdb_client.client.delete_api import DeleteApi
from src.pattern_aggregate_retention import (
    PatternAggregateRetention,
    RetentionConfig,
    run_pattern_aggregate_retention,
)


def _mock_influx_client():
    """Return ``(client, delete_api)`` where delete is bound to the real signature.

    ``create_autospec(DeleteApi)`` is deliberate: a bare ``MagicMock`` accepts any
    call shape, which is how ``client.delete(...)`` -- a method InfluxDBClient does
    not have, missing the required ``predicate`` -- passed this suite while being
    broken against the real library.
    """
    delete_api = create_autospec(DeleteApi, instance=True)
    client = MagicMock()
    client.delete_api.return_value = delete_api
    return client, delete_api


class TestRetentionConfig:
    """Test RetentionConfig dataclass."""

    def test_config_creation(self):
        """Test creating a retention config."""
        config = RetentionConfig(
            bucket_name="test_bucket",
            retention_days=90,
            cleanup_enabled=True,
            description="Test retention config"
        )

        assert config.bucket_name == "test_bucket"
        assert config.retention_days == 90
        assert config.cleanup_enabled is True
        assert config.description == "Test retention config"

    def test_config_defaults(self):
        """Test retention config defaults."""
        config = RetentionConfig(
            bucket_name="test_bucket",
            retention_days=90
        )

        assert config.cleanup_enabled is True
        assert config.description == ""


class TestPatternAggregateRetention:
    """Test PatternAggregateRetention manager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = PatternAggregateRetention()

        assert manager.influxdb_client is None
        assert len(manager.retention_policies) == 2
        assert "pattern_aggregates_daily" in manager.retention_policies
        assert "pattern_aggregates_weekly" in manager.retention_policies

        daily = manager.retention_policies["pattern_aggregates_daily"]
        assert daily.bucket_name == "pattern_aggregates_daily"
        assert daily.retention_days == 90
        assert daily.cleanup_enabled is True

        weekly = manager.retention_policies["pattern_aggregates_weekly"]
        assert weekly.bucket_name == "pattern_aggregates_weekly"
        assert weekly.retention_days == 365
        assert weekly.cleanup_enabled is True

    def test_initialization_with_client(self):
        """Test manager initialization with InfluxDB client."""
        mock_client = MagicMock()
        manager = PatternAggregateRetention(influxdb_client=mock_client)

        assert manager.influxdb_client is mock_client

    def test_influxdb_client_has_no_delete_method(self):
        """Deletes must go through delete_api(), not the client.

        The old code called ``influxdb_client.delete(bucket=, start=, stop=)``.
        InfluxDBClient has no ``delete``, and DeleteApi.delete requires a
        ``predicate``, so that call could only ever work against a bare
        MagicMock -- which is exactly what the suite used.
        """
        assert not hasattr(InfluxDBClient, "delete")

        autospecced = create_autospec(DeleteApi, instance=True)
        with pytest.raises(TypeError):
            autospecced.delete(
                bucket="pattern_aggregates_daily",
                start="1970-01-01T00:00:00Z",
                stop="2026-01-01T00:00:00Z",
            )

    @pytest.mark.asyncio
    async def test_cleanup_without_client_reports_failure(self):
        """A pass that deletes nothing must not report success.

        Regression: this returned ``success: True`` with a 'Mock operation' note,
        so a deployment with no InfluxDB credentials looked like it was enforcing
        the 90/365-day policy while never removing a single record.
        """
        manager = PatternAggregateRetention()
        config = manager.retention_policies["pattern_aggregates_daily"]

        result = await manager._cleanup_bucket(config)

        assert result["success"] is False
        assert result["records_deleted"] == 0
        assert result["error"] == "No InfluxDB client configured"
        assert "cutoff_date" in result

    @pytest.mark.asyncio
    async def test_cleanup_with_real_client(self):
        """Test cleanup with mocked InfluxDB client."""
        mock_client, delete_api = _mock_influx_client()
        manager = PatternAggregateRetention(
            influxdb_client=mock_client, influxdb_org="homeiq"
        )
        config = manager.retention_policies["pattern_aggregates_daily"]

        result = await manager._cleanup_bucket(config)

        assert result["success"] is True
        assert result["bucket"] == "pattern_aggregates_daily"
        assert "cutoff_date" in result
        assert result["records_deleted"] is None  # InfluxDB delete API doesn't return count

        # Verify delete was called with correct parameters
        delete_api.delete.assert_called_once()
        call_args = delete_api.delete.call_args

        assert call_args.kwargs["bucket"] == "pattern_aggregates_daily"
        assert call_args.kwargs["start"] == "1970-01-01T00:00:00Z"
        assert call_args.kwargs["org"] == "homeiq"
        # Empty predicate means "every series in the range" -- required by the API.
        assert call_args.kwargs["predicate"] == ""
        # Stop date should be 90 days ago
        assert "stop" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_cleanup_cutoff_date_calculation(self):
        """Test that cutoff dates are calculated correctly."""
        mock_client, _ = _mock_influx_client()
        manager = PatternAggregateRetention(influxdb_client=mock_client)

        # Test daily (90 days)
        daily_config = manager.retention_policies["pattern_aggregates_daily"]
        result_daily = await manager._cleanup_bucket(daily_config)

        cutoff_daily = datetime.fromisoformat(result_daily["cutoff_date"])
        now = datetime.now()
        expected_cutoff_daily = now - timedelta(days=90)

        # Allow 1 minute tolerance for test execution time
        assert abs((cutoff_daily - expected_cutoff_daily).total_seconds()) < 60

        # Test weekly (365 days)
        weekly_config = manager.retention_policies["pattern_aggregates_weekly"]
        result_weekly = await manager._cleanup_bucket(weekly_config)

        cutoff_weekly = datetime.fromisoformat(result_weekly["cutoff_date"])
        expected_cutoff_weekly = now - timedelta(days=365)

        # Allow 1 minute tolerance for test execution time
        assert abs((cutoff_weekly - expected_cutoff_weekly).total_seconds()) < 60

    @pytest.mark.asyncio
    async def test_cleanup_error_handling(self):
        """Test error handling during cleanup."""
        mock_client, delete_api = _mock_influx_client()
        delete_api.delete.side_effect = Exception("InfluxDB connection failed")

        manager = PatternAggregateRetention(influxdb_client=mock_client)
        config = manager.retention_policies["pattern_aggregates_daily"]

        result = await manager._cleanup_bucket(config)

        assert result["success"] is False
        assert "error" in result
        assert "connection failed" in result["error"]

    @pytest.mark.asyncio
    async def test_run_cleanup_all_buckets(self):
        """Test running cleanup for all buckets."""
        mock_client, delete_api = _mock_influx_client()
        manager = PatternAggregateRetention(influxdb_client=mock_client)

        result = await manager.run_cleanup()

        assert result["success"] is True
        assert "duration_seconds" in result
        assert "results" in result
        assert len(result["results"]) == 2
        assert "pattern_aggregates_daily" in result["results"]
        assert "pattern_aggregates_weekly" in result["results"]

        # Both should succeed
        assert result["results"]["pattern_aggregates_daily"]["success"] is True
        assert result["results"]["pattern_aggregates_weekly"]["success"] is True

        # Verify delete was called twice
        assert delete_api.delete.call_count == 2

    @pytest.mark.asyncio
    async def test_run_cleanup_with_disabled_policy(self):
        """Test run_cleanup skips disabled policies."""
        mock_client, delete_api = _mock_influx_client()
        manager = PatternAggregateRetention(influxdb_client=mock_client)

        # Disable the weekly policy
        manager.retention_policies["pattern_aggregates_weekly"].cleanup_enabled = False

        result = await manager.run_cleanup()

        assert result["success"] is True
        # Should only have one result
        assert len(result["results"]) == 1
        assert "pattern_aggregates_daily" in result["results"]

        # delete should be called only once
        assert delete_api.delete.call_count == 1

    @pytest.mark.asyncio
    async def test_run_cleanup_partial_failure(self):
        """One failed bucket must fail the whole pass.

        This previously asserted overall success stayed True on a partial
        failure, which is the behaviour that let a half-broken retention run
        report clean.
        """
        mock_client, delete_api = _mock_influx_client()
        delete_api.delete.side_effect = [
            None,  # First call succeeds
            Exception("Weekly bucket error")  # Second call fails
        ]

        manager = PatternAggregateRetention(influxdb_client=mock_client)
        result = await manager.run_cleanup()

        assert result["success"] is False
        assert result["results"]["pattern_aggregates_daily"]["success"] is True
        assert result["results"]["pattern_aggregates_weekly"]["success"] is False

    def test_get_retention_summary(self):
        """Test getting retention policy summary."""
        manager = PatternAggregateRetention()
        summary = manager.get_retention_summary()

        assert summary["total_buckets"] == 2
        assert summary["total_retention_days"] == 90 + 365
        assert "policies" in summary
        assert "pattern_aggregates_daily" in summary["policies"]
        assert "pattern_aggregates_weekly" in summary["policies"]

        daily_policy = summary["policies"]["pattern_aggregates_daily"]
        assert daily_policy["retention_days"] == 90
        assert daily_policy["enabled"] is True

    @pytest.mark.asyncio
    async def test_run_pattern_aggregate_retention_function(self):
        """Test the top-level async function."""
        mock_client, _ = _mock_influx_client()
        result = await run_pattern_aggregate_retention(influxdb_client=mock_client)

        assert result["success"] is True
        assert "duration_seconds" in result
        assert len(result["results"]) == 2

    @pytest.mark.asyncio
    async def test_cleanup_bucket_date_range_boundaries(self):
        """Test that deletion uses correct date range boundaries."""
        mock_client, delete_api = _mock_influx_client()
        manager = PatternAggregateRetention(influxdb_client=mock_client)
        config = manager.retention_policies["pattern_aggregates_daily"]

        await manager._cleanup_bucket(config)

        # Verify the parameters passed to delete
        call_kwargs = delete_api.delete.call_args.kwargs

        # Start should always be Unix epoch
        assert call_kwargs["start"] == "1970-01-01T00:00:00Z"

        # Stop should be 90 days ago
        stop_date = datetime.fromisoformat(call_kwargs["stop"])
        now = datetime.now()
        expected_stop = now - timedelta(days=90)

        # Allow 1 minute tolerance
        assert abs((stop_date - expected_stop).total_seconds()) < 60


class TestIntegration:
    """Integration tests for pattern aggregate retention."""

    @pytest.mark.asyncio
    async def test_full_cleanup_workflow(self):
        """Test the full cleanup workflow with a mock client."""
        # Create a mock client
        mock_client, delete_api = _mock_influx_client()
        call_history = []

        def track_delete(**kwargs):
            call_history.append(kwargs)

        delete_api.delete.side_effect = track_delete

        # Initialize and run
        manager = PatternAggregateRetention(influxdb_client=mock_client)
        result = await manager.run_cleanup()

        # Verify overall success
        assert result["success"] is True

        # Verify both buckets were targeted
        assert len(call_history) == 2

        buckets_targeted = {delete_call["bucket"] for delete_call in call_history}
        assert "pattern_aggregates_daily" in buckets_targeted
        assert "pattern_aggregates_weekly" in buckets_targeted

        # Verify all calls have correct start date
        for delete_call in call_history:
            assert delete_call["start"] == "1970-01-01T00:00:00Z"
            # Stop date should be in the past
            stop_date = datetime.fromisoformat(delete_call["stop"])
            assert stop_date < datetime.now()
