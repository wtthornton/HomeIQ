"""Unit tests for HouseStatusAggregator's presence-sensor room roll-up.

TAP-7585: presence-capable binary sensors (motion, occupancy, presence) must
roll up to a per-area RoomOccupancy state. The distinction that matters:
an area whose sensors are all clear reports ``clear``; an area with no
presence-capable sensor at all reports ``unknown``. Collapsing those two into
one value is the failure this file exists to catch.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from src.house_status.aggregator import (
    _PRESENCE_DEVICE_CLASSES,
    HouseStatusAggregator,
)
from src.house_status.models import RoomOccupancy


def make_discovery(entity_to_area: dict[str, str] | None = None) -> Any:
    """A minimal stand-in exposing only what _resolve_area reads."""
    return SimpleNamespace(
        entity_to_area=dict(entity_to_area or {}),
        entity_to_device={},
        device_to_area={},
    )


def binary_sensor_state(device_class: str, raw_state: str) -> dict[str, Any]:
    return {
        "state": raw_state,
        "attributes": {"device_class": device_class, "friendly_name": "test sensor"},
    }


async def test_sensors_section_is_additive_and_unchanged() -> None:
    """A non-presence binary sensor still populates the flat sensors dict.

    This is the baseline the room roll-up must not disturb: it passes
    identically on unmodified origin/master and after the roll-up is added.
    """
    aggregator = HouseStatusAggregator()

    delta = await aggregator.process_state_change(
        "binary_sensor.front_door",
        binary_sensor_state("door", "on"),
        None,
    )

    assert delta == {
        "section": "sensors",
        "data": {"name": "test sensor", "state": "open", "device_class": "door"},
    }

    snapshot = await aggregator.get_snapshot()
    assert snapshot.sensors["door"][0].state == "open"


async def test_two_clear_presence_sensors_report_clear() -> None:
    """An area with two presence sensors, both clear, reports 'clear'."""
    discovery = make_discovery(
        {
            "binary_sensor.office_motion": "office",
            "binary_sensor.office_occupancy": "office",
        }
    )
    aggregator = HouseStatusAggregator(discovery_service=discovery)

    await aggregator.process_state_change(
        "binary_sensor.office_motion", binary_sensor_state("motion", "off"), None
    )
    await aggregator.process_state_change(
        "binary_sensor.office_occupancy", binary_sensor_state("occupancy", "off"), None
    )

    room = aggregator._resolve_room_occupancy("office")
    assert room.state == "clear"
    assert set(room.contributing_entity_ids) == {
        "binary_sensor.office_motion",
        "binary_sensor.office_occupancy",
    }


async def test_area_with_no_presence_sensor_reports_unknown() -> None:
    """An area that has never seen a presence-capable sensor reports 'unknown'."""
    aggregator = HouseStatusAggregator(discovery_service=make_discovery())

    room = aggregator._resolve_room_occupancy("guest_room")

    assert room.state == "unknown"
    assert room.contributing_entity_ids == []


async def test_clear_and_unknown_are_distinct_values() -> None:
    """The story's own acceptance box: clear and unknown must not collapse."""
    discovery = make_discovery({"binary_sensor.office_motion": "office"})
    aggregator = HouseStatusAggregator(discovery_service=discovery)

    await aggregator.process_state_change(
        "binary_sensor.office_motion", binary_sensor_state("motion", "off"), None
    )

    clear_room = aggregator._resolve_room_occupancy("office")
    unknown_room = aggregator._resolve_room_occupancy("empty_room")

    assert clear_room.state == "clear"
    assert unknown_room.state == "unknown"
    assert clear_room.state != unknown_room.state


async def test_any_detected_sensor_marks_area_detected() -> None:
    """One sensor tripped among several is enough to report 'detected'."""
    discovery = make_discovery(
        {
            "binary_sensor.office_motion": "office",
            "binary_sensor.office_occupancy": "office",
        }
    )
    aggregator = HouseStatusAggregator(discovery_service=discovery)

    await aggregator.process_state_change(
        "binary_sensor.office_motion", binary_sensor_state("motion", "off"), None
    )
    await aggregator.process_state_change(
        "binary_sensor.office_occupancy", binary_sensor_state("occupancy", "on"), None
    )

    room = aggregator._resolve_room_occupancy("office")
    assert room.state == "detected"


async def test_unresolvable_area_lands_in_explicit_unknown_area_not_dropped() -> None:
    """An entity whose area can't be resolved is counted, never skipped."""
    aggregator = HouseStatusAggregator(discovery_service=make_discovery())

    await aggregator.process_state_change(
        "binary_sensor.mystery_motion", binary_sensor_state("motion", "on"), None
    )

    room = aggregator._resolve_room_occupancy("unknown")
    assert room.contributing_entity_ids == ["binary_sensor.mystery_motion"]
    assert room.state == "detected"


async def test_snapshot_includes_room_occupancy_for_seen_areas() -> None:
    """The full process_state_change -> get_snapshot path wires the roll-up in."""
    discovery = make_discovery({"binary_sensor.office_motion": "office"})
    aggregator = HouseStatusAggregator(discovery_service=discovery)

    await aggregator.process_state_change(
        "binary_sensor.office_motion", binary_sensor_state("motion", "off"), None
    )

    snapshot = await aggregator.get_snapshot()
    rooms = {r.area_id: r for r in snapshot.room_occupancy}
    assert rooms["office"].state == "clear"
    assert rooms["office"].contributing_entity_ids == ["binary_sensor.office_motion"]


def test_presence_device_classes_constant_contains_required_members() -> None:
    """VAL-4: motion, occupancy and presence live in one named constant."""
    assert frozenset({"motion", "occupancy", "presence"}) == _PRESENCE_DEVICE_CLASSES


def test_room_occupancy_model_fields() -> None:
    room = RoomOccupancy(
        area_id="office",
        state="clear",
        contributing_entity_ids=["binary_sensor.office_motion"],
        last_changed="2026-09-14T00:00:00+00:00",
    )
    assert room.area_id == "office"
    assert room.state == "clear"
    assert room.contributing_entity_ids == ["binary_sensor.office_motion"]
    assert room.last_changed == "2026-09-14T00:00:00+00:00"


class _FakeBatchWriter:
    """Records every room-occupancy write instead of touching InfluxDB."""

    def __init__(self) -> None:
        self.room_occupancy_writes: list[tuple[str, str, int]] = []

    async def write_room_occupancy(
        self, area_id: str, state: str, contributing_entity_count: int
    ) -> bool:
        self.room_occupancy_writes.append((area_id, state, contributing_entity_count))
        return True


async def test_state_transition_writes_exactly_one_point_per_change() -> None:
    """TAP-7586 VAL-0/VAL-2: a real transition writes one point; the same
    transition observed again (same resolved state) writes zero more.

    office: unknown -> detected (motion on)         => +1 point
            detected -> detected (occupancy also on) => +0 (state unchanged)
            detected -> clear (both sensors off)      => +1 point
            clear -> clear (motion off again)         => +0 (state unchanged)
    """
    discovery = make_discovery(
        {
            "binary_sensor.office_motion": "office",
            "binary_sensor.office_occupancy": "office",
        }
    )
    writer = _FakeBatchWriter()
    aggregator = HouseStatusAggregator(discovery_service=discovery, influxdb_batch_writer=writer)

    await aggregator.process_state_change(
        "binary_sensor.office_motion", binary_sensor_state("motion", "on"), None
    )
    await aggregator.process_state_change(
        "binary_sensor.office_occupancy", binary_sensor_state("occupancy", "on"), None
    )
    await aggregator.process_state_change(
        "binary_sensor.office_motion", binary_sensor_state("motion", "off"), None
    )
    await aggregator.process_state_change(
        "binary_sensor.office_occupancy", binary_sensor_state("occupancy", "off"), None
    )
    await aggregator.process_state_change(
        "binary_sensor.office_motion", binary_sensor_state("motion", "off"), None
    )

    assert len(writer.room_occupancy_writes) == 2
    assert writer.room_occupancy_writes[0] == ("office", "detected", 1)
    assert writer.room_occupancy_writes[1] == ("office", "clear", 2)
