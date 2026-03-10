"""Tests for StorageAnalytics (Epic 46: enabled guard in log_retention_operation)."""

from unittest.mock import MagicMock, patch

import pytest

from src.storage_analytics import StorageAnalytics


@pytest.mark.asyncio
async def test_log_retention_operation_disabled_no_op():
    """When enabled is False, log_retention_operation returns without calling client.write."""
    analytics = StorageAnalytics()
    analytics.enabled = False
    analytics.client = None  # as in InfluxDB 2.7 default

    # Should not raise; must not access self.client
    await analytics.log_retention_operation(
        operation_type="cleanup",
        records_processed=100,
        storage_freed_mb=1.5,
        duration_seconds=2.0,
        errors=0,
    )


@pytest.mark.asyncio
async def test_log_retention_operation_disabled_client_not_called():
    """When enabled is False, client.write is never called."""
    analytics = StorageAnalytics()
    analytics.enabled = False
    mock_client = MagicMock()
    analytics.client = mock_client

    await analytics.log_retention_operation(
        operation_type="cleanup",
        records_processed=100,
        storage_freed_mb=1.5,
        duration_seconds=2.0,
        errors=0,
    )

    mock_client.write.assert_not_called()


@pytest.mark.asyncio
async def test_log_retention_operation_enabled_calls_write():
    """When enabled is True, log_retention_operation calls client.write (if client available)."""
    mock_point = MagicMock()
    mock_point.tag.return_value = mock_point
    mock_point.field.return_value = mock_point
    mock_point.time.return_value = mock_point

    with patch("src.storage_analytics.Point", return_value=mock_point):
        analytics = StorageAnalytics()
        analytics.enabled = True
        mock_client = MagicMock()
        analytics.client = mock_client

        await analytics.log_retention_operation(
            operation_type="cleanup",
            records_processed=100,
            storage_freed_mb=1.5,
            duration_seconds=2.0,
            errors=0,
        )

        mock_client.write.assert_called_once()
        mock_client.write.assert_called_with(mock_point)
