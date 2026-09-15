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
