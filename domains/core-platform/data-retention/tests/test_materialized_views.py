"""Tests for MaterializedViewManager event-loop hygiene.

InfluxDBClient3.query/write are synchronous HTTP/gRPC round-trips. Every
async method on the manager must offload them to an executor thread —
calling them inline blocks the service's single event loop for the full
query duration (audit round-2 HIGH finding).

The tests capture the thread each client call runs on and assert it is
never the event-loop thread. Without the offload the calls run inline on
the loop thread and these tests fail.
"""

import asyncio
import sys
import threading
import types
from unittest.mock import MagicMock

import pytest
from src.materialized_views import MaterializedViewManager


class _FakeFrame:
    """Minimal stand-in for the pandas DataFrame returned by mode='pandas'."""

    def __init__(self, rows):
        self._rows = rows

    @property
    def empty(self):
        return not self._rows

    def __len__(self):
        return len(self._rows)

    def iterrows(self):
        return iter(enumerate(self._rows))

    def to_dict(self, _orient):
        return list(self._rows)


class _ChainingPoint:
    """Stand-in for influxdb_client_3.Point with the same fluent interface."""

    def __init__(self, measurement):
        self.measurement = measurement

    def tag(self, *_args):
        return self

    def field(self, *_args):
        return self

    def time(self, *_args):
        return self


@pytest.fixture
def stub_point_module(monkeypatch):
    """Provide influxdb_client_3.Point when the real package is absent.

    The create-view methods do ``from influxdb_client_3 import Point``
    lazily inside the write path.
    """
    if "influxdb_client_3" in sys.modules:
        yield
        return
    module = types.ModuleType("influxdb_client_3")
    module.Point = _ChainingPoint
    monkeypatch.setitem(sys.modules, "influxdb_client_3", module)
    yield


def _recording_client(query_result):
    """Return (client, call_threads) where each call records its thread."""
    call_threads = {"query": [], "write": []}
    client = MagicMock()

    def record_query(*_args, **_kwargs):
        call_threads["query"].append(threading.current_thread())
        return query_result

    def record_write(*_args, **_kwargs):
        call_threads["write"].append(threading.current_thread())

    client.query.side_effect = record_query
    client.write.side_effect = record_write
    return client, call_threads


def _enabled_manager(client):
    manager = MaterializedViewManager()
    manager.client = client
    manager.enabled = True
    return manager


_VIEW_CASES = [
    (
        "create_daily_energy_view",
        {
            "entity_id": "sensor.dryer",
            "total_kwh": 1.5,
            "avg_power": 120.0,
            "peak_power": 900.0,
            "cost_usd": 0.18,
            "day": "2026-07-30",
        },
    ),
    (
        "create_hourly_room_activity_view",
        {
            "area": "kitchen",
            "hour": 7,
            "day_of_week": 4,
            "motion_count": 12,
            "occupancy_rate": 0.4,
        },
    ),
    (
        "create_daily_carbon_summary_view",
        {
            "avg_carbon": 250.0,
            "min_carbon": 100.0,
            "max_carbon": 400.0,
            "avg_renewable": 35.0,
            "day": "2026-07-30",
        },
    ),
]


class TestBlockingCallsOffloaded:
    """query/write must never run on the event-loop thread."""

    @pytest.mark.parametrize(("method_name", "row"), _VIEW_CASES)
    def test_create_view_offloads_query_and_write(self, stub_point_module, method_name, row):
        client, call_threads = _recording_client(_FakeFrame([row]))
        manager = _enabled_manager(client)

        async def run():
            loop_thread = threading.current_thread()
            await getattr(manager, method_name)()
            return loop_thread

        loop_thread = asyncio.run(run())

        assert call_threads["query"], "client.query was never called"
        assert all(t is not loop_thread for t in call_threads["query"]), (
            f"{method_name} ran client.query on the event-loop thread"
        )
        assert call_threads["write"], "client.write was never called"
        assert all(t is not loop_thread for t in call_threads["write"]), (
            f"{method_name} ran client.write on the event-loop thread"
        )

    def test_query_view_offloads_query(self):
        client, call_threads = _recording_client(_FakeFrame([]))
        manager = _enabled_manager(client)

        async def run():
            loop_thread = threading.current_thread()
            result = await manager.query_view("mv_daily_energy_by_device")
            return loop_thread, result

        loop_thread, result = asyncio.run(run())

        assert result == []
        assert call_threads["query"], "client.query was never called"
        assert all(t is not loop_thread for t in call_threads["query"]), (
            "query_view ran client.query on the event-loop thread"
        )

    def test_benchmark_performance_offloads_query(self):
        client, call_threads = _recording_client(_FakeFrame([]))
        manager = _enabled_manager(client)

        async def run():
            loop_thread = threading.current_thread()
            await manager.benchmark_performance()
            return loop_thread

        loop_thread = asyncio.run(run())

        assert len(call_threads["query"]) == 2, (
            "benchmark should run the original query plus the view query"
        )
        assert all(t is not loop_thread for t in call_threads["query"]), (
            "benchmark_performance ran client.query on the event-loop thread"
        )

    def test_refresh_all_views_offloads_every_call(self, stub_point_module):
        rows = dict(_VIEW_CASES)
        frames = iter(
            [
                _FakeFrame([rows["create_daily_energy_view"]]),
                _FakeFrame([rows["create_hourly_room_activity_view"]]),
                _FakeFrame([rows["create_daily_carbon_summary_view"]]),
            ]
        )
        call_threads = {"query": [], "write": []}
        client = MagicMock()

        def record_query(*_args, **_kwargs):
            call_threads["query"].append(threading.current_thread())
            return next(frames)

        def record_write(*_args, **_kwargs):
            call_threads["write"].append(threading.current_thread())

        client.query.side_effect = record_query
        client.write.side_effect = record_write
        manager = _enabled_manager(client)

        async def run():
            loop_thread = threading.current_thread()
            result = await manager.refresh_all_views()
            return loop_thread, result

        loop_thread, result = asyncio.run(run())

        assert result["status"] == "success"
        assert result["views_refreshed"] == 3
        assert len(call_threads["query"]) == 3
        offloaded = call_threads["query"] + call_threads["write"]
        assert all(t is not loop_thread for t in offloaded), (
            "refresh_all_views ran a blocking InfluxDB call on the event-loop thread"
        )


class TestDisabledPaths:
    """Disabled manager must not touch the client at all."""

    @pytest.mark.parametrize(("method_name", "_row"), _VIEW_CASES)
    def test_create_view_disabled_skips_client(self, method_name, _row):
        client = MagicMock()
        manager = MaterializedViewManager()
        manager.client = client
        manager.enabled = False

        result = asyncio.run(getattr(manager, method_name)())

        assert result == {"status": "disabled", "reason": "InfluxDB 3.0+ required"}
        client.query.assert_not_called()
        client.write.assert_not_called()

    def test_query_view_disabled_returns_empty(self):
        manager = MaterializedViewManager()
        manager.enabled = False

        assert asyncio.run(manager.query_view("mv_daily_energy_by_device")) == []
