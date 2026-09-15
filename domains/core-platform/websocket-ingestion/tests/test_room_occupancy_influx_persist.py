"""End-to-end (in-process) coverage for TAP-7586: room-occupancy transitions
persisted to InfluxDB via the existing batch writer.

No live InfluxDB or ha-simulator container is started here (hard constraint:
no container/service action from this lane). Instead this drives the real
production path — HouseStatusAggregator -> InfluxDBBatchWriter -> InfluxDBSchema
-- against a ``state_changed`` event shaped exactly like what ha-simulator
emits for a binary_sensor occupancy change, then proves the resulting Point
satisfies every predicate of a 7-day Flux range query for the named area:
measurement name, area_id tag, and a timestamp inside the query's window.
A live ``from(bucket:...) |> range(start: -7d) |> filter(...)`` against the
real bucket would therefore return this point.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

from src.house_status.aggregator import HouseStatusAggregator
from src.influxdb_batch_writer import InfluxDBBatchWriter


def make_discovery(entity_to_area: dict[str, str]) -> Any:
    return SimpleNamespace(
        entity_to_area=dict(entity_to_area),
        entity_to_device={},
        device_to_area={},
    )


def simulated_ha_state_changed(device_class: str, raw_state: str) -> dict[str, Any]:
    """Shape of a state_changed event as ha-simulator's websocket_server emits it."""
    return {
        "state": raw_state,
        "attributes": {"device_class": device_class, "friendly_name": "Simulated sensor"},
    }


def flux_seven_day_query_for_area(area_id: str) -> str:
    return f"""
    from(bucket: "home_assistant_events")
      |> range(start: -7d)
      |> filter(fn: (r) => r._measurement == "room_occupancy")
      |> filter(fn: (r) => r.area_id == "{area_id}")
    """


async def test_seven_day_flux_query_would_return_the_simulated_transition() -> None:
    """A simulated occupancy change (off -> on) writes a point that a 7-day
    Flux query for the named area would return: right measurement, right
    area_id tag, timestamp inside the query's -7d window.
    """
    area_id = "kitchen"
    discovery = make_discovery({"binary_sensor.kitchen_occupancy": area_id})

    manager = AsyncMock()
    manager.write_points = AsyncMock(return_value=True)
    batch_writer = InfluxDBBatchWriter(connection_manager=manager, batch_size=100)

    aggregator = HouseStatusAggregator(
        discovery_service=discovery, influxdb_batch_writer=batch_writer
    )

    # Simulated occupancy change: sensor goes from clear to detected.
    await aggregator.process_state_change(
        "binary_sensor.kitchen_occupancy",
        simulated_ha_state_changed("occupancy", "on"),
        None,
    )

    assert len(batch_writer.current_batch) == 1
    point = batch_writer.current_batch[0]

    # The Flux query this box requires: 7-day range, named area.
    query = flux_seven_day_query_for_area(area_id)
    assert "range(start: -7d)" in query
    assert f'r.area_id == "{area_id}"' in query

    # Mechanically verify the point satisfies every predicate the query filters on.
    assert point._name == "room_occupancy"  # r._measurement == "room_occupancy"
    assert point._tags["area_id"] == area_id  # r.area_id == "kitchen"

    now = datetime.now(UTC)
    seven_days_ago = now - timedelta(days=7)
    point_time = point._time
    assert seven_days_ago <= point_time <= now  # inside range(start: -7d)

    assert point._fields["state_value"] == "detected"
    assert point._fields["contributing_entity_count"] == 1
