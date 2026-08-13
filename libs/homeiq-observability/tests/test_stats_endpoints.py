"""_get_active_data_sources talks to a real client method (TAP-5994).

The original code called ``influxdb_client.query(...)`` — a method that
never existed on ``InfluxDBQueryClient`` — and a blanket except swallowed
the ``AttributeError``, returning ``[]`` silently, forever. These tests
pin the contract with a ``spec``-locked mock: renaming or removing the
client method breaks CI instead of reverting to the silent empty list.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeiq_data.influxdb_query_client import InfluxDBQueryClient
from homeiq_observability.monitoring.stats_endpoints import StatsEndpoints


def _stats_with(client: AsyncMock) -> StatsEndpoints:
    stats = StatsEndpoints()
    stats.use_influxdb = True
    stats.influxdb_client = client
    return stats


@pytest.mark.asyncio
async def test_active_data_sources_use_a_method_that_exists_on_the_client():
    """spec= makes this fail with AttributeError if the method is renamed."""
    client = AsyncMock(spec=InfluxDBQueryClient)
    client.is_connected = True
    client.list_active_measurements.return_value = [
        "home_assistant_events",
        "service_health",
    ]

    result = await _stats_with(client)._get_active_data_sources()

    assert result == ["home_assistant_events", "service_health"]
    client.list_active_measurements.assert_awaited_once()


@pytest.mark.asyncio
async def test_unreachable_influxdb_degrades_to_empty_with_a_warning(caplog):
    client = AsyncMock(spec=InfluxDBQueryClient)
    client.is_connected = True
    client.list_active_measurements.side_effect = Exception("connection refused")

    with caplog.at_level("WARNING"):
        result = await _stats_with(client)._get_active_data_sources()

    assert result == []
    assert any("degraded to []" in r.message for r in caplog.records)


@pytest.mark.asyncio
async def test_disconnected_client_short_circuits_to_empty(caplog):
    client = AsyncMock(spec=InfluxDBQueryClient)
    client.is_connected = False

    with caplog.at_level("WARNING"):
        result = await _stats_with(client)._get_active_data_sources()

    assert result == []
    client.list_active_measurements.assert_not_awaited()


def test_client_method_queries_recent_activity_not_the_schema_catalogue():
    """The Flux must be range-bounded — schema.measurements would keep
    reporting a feed that died weeks ago."""
    import inspect

    src = inspect.getsource(InfluxDBQueryClient.list_active_measurements)
    assert "range(start:" in src
    assert "schema.measurements" not in src
