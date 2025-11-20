"""
Unit tests for stats endpoint data source discovery
Story 24.1: Fix Hardcoded Monitoring Metrics
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from shared.monitoring import StatsEndpoints


@pytest.mark.asyncio
async def test_get_active_data_sources_from_influxdb():
    """Test that data sources are queried from InfluxDB instead of hardcoded"""
    stats = StatsEndpoints()
    stats.use_influxdb = True

    # Mock InfluxDB client
    mock_client = AsyncMock()
    mock_client.is_connected = True
    stats.influxdb_client = mock_client

    # Mock query result
    mock_record = MagicMock()
    mock_record.values = {"_value": "home_assistant_events"}
    mock_table = MagicMock()
    mock_table.records = [mock_record]
    mock_client.query = AsyncMock(return_value=[mock_table])

    # Call the method
    result = await stats._get_active_data_sources()

    # Verify InfluxDB was queried
    mock_client.query.assert_called_once()
    query = mock_client.query.call_args[0][0]
    assert "schema.measurements" in query

    # Verify result contains discovered measurements
    assert len(result) > 0
    assert "home_assistant_events" in result


@pytest.mark.asyncio
async def test_get_active_data_sources_influxdb_error():
    """Test that errors in data source discovery are handled gracefully"""
    stats = StatsEndpoints()
    stats.use_influxdb = True

    # Mock InfluxDB client to raise error
    mock_client = AsyncMock()
    mock_client.is_connected = True
    mock_client.query = AsyncMock(side_effect=Exception("Query failed"))
    stats.influxdb_client = mock_client

    # Call the method
    result = await stats._get_active_data_sources()

    # Should return empty list on error, not hardcoded values
    assert result == []
    assert result != ["home_assistant", "weather_api", "sports_api"]


@pytest.mark.asyncio
async def test_get_active_data_sources_influxdb_disconnected():
    """Test behavior when InfluxDB is not connected"""
    stats = StatsEndpoints()
    stats.use_influxdb = False

    # Call the method
    result = await stats._get_active_data_sources()

    # Should return empty list when InfluxDB unavailable
    assert result == []


@pytest.mark.asyncio
async def test_get_active_data_sources_not_hardcoded():
    """Regression test: Ensure data sources are NOT hardcoded"""
    stats = StatsEndpoints()
    stats.use_influxdb = True

    # Mock InfluxDB client with different measurements
    mock_client = AsyncMock()
    mock_client.is_connected = True

    # Mock different measurements
    mock_records = [
        MagicMock(values={"_value": "sports_data"}),
        MagicMock(values={"_value": "weather_data"}),
        MagicMock(values={"_value": "energy_data"})
    ]
    mock_table = MagicMock()
    mock_table.records = mock_records
    mock_client.query = AsyncMock(return_value=[mock_table])
    stats.influxdb_client = mock_client

    # Call the method
    result = await stats._get_active_data_sources()

    # Should return discovered measurements, not hardcoded list
    assert result != ["home_assistant", "weather_api", "sports_api"]
    assert "sports_data" in result
    assert "weather_data" in result
    assert "energy_data" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

