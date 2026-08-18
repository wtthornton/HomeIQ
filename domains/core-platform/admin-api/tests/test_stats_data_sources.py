"""
Unit tests for stats endpoint data source discovery
Story 24.1: Fix Hardcoded Monitoring Metrics
TAP-5994: the old code mocked a `query` method that never existed on the
real client, so these tests passed while production returned [] forever.
Mocks are now spec-locked to InfluxDBQueryClient and exercise the real
`list_active_measurements` contract.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent / ".."))

from homeiq_data.influxdb_query_client import InfluxDBQueryClient
from homeiq_observability.monitoring import StatsEndpoints


def _stats_with_client(**client_attrs) -> StatsEndpoints:
    stats = StatsEndpoints()
    stats.use_influxdb = True
    # spec= pins the real client surface: a renamed/removed method makes
    # these tests error instead of green-lighting a phantom call again.
    client = AsyncMock(spec=InfluxDBQueryClient)
    client.is_connected = True
    for name, value in client_attrs.items():
        setattr(client, name, value)
    stats.influxdb_client = client
    return stats


@pytest.mark.asyncio
async def test_get_active_data_sources_from_influxdb():
    """Data sources come from the client's real measurement listing."""
    stats = _stats_with_client()
    stats.influxdb_client.list_active_measurements.return_value = ["home_assistant_events"]

    result = await stats._get_active_data_sources()

    stats.influxdb_client.list_active_measurements.assert_awaited_once()
    assert result == ["home_assistant_events"]


@pytest.mark.asyncio
async def test_get_active_data_sources_influxdb_error():
    """Errors degrade to [] (with a warning), never hardcoded values."""
    stats = _stats_with_client()
    stats.influxdb_client.list_active_measurements.side_effect = Exception("Query failed")

    result = await stats._get_active_data_sources()

    assert result == []
    assert result != ["home_assistant", "weather_api", "sports_api"]


@pytest.mark.asyncio
async def test_get_active_data_sources_influxdb_disconnected():
    """Test behavior when InfluxDB is not connected"""
    stats = StatsEndpoints()
    stats.use_influxdb = False

    result = await stats._get_active_data_sources()

    assert result == []


@pytest.mark.asyncio
async def test_get_active_data_sources_not_hardcoded():
    """Regression test: Ensure data sources are NOT hardcoded"""
    stats = _stats_with_client()
    stats.influxdb_client.list_active_measurements.return_value = [
        "energy_data",
        "sports_data",
        "weather_data",
    ]

    result = await stats._get_active_data_sources()

    assert result != ["home_assistant", "weather_api", "sports_api"]
    assert "sports_data" in result
    assert "weather_data" in result
    assert "energy_data" in result
