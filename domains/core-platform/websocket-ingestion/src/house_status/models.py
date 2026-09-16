"""Pydantic models for house status sections.

All models use ``from __future__ import annotations`` for PEP 604 unions
and are kept lightweight for fast serialisation to WebSocket clients.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ClimateStatus(BaseModel):
    """State snapshot of a single climate entity."""

    entity_id: str
    friendly_name: str = ""
    current_temperature: float | None = None
    target_temperature: float | None = None
    hvac_mode: str = "off"
    unit: str = "C"


class PresenceStatus(BaseModel):
    """Presence state for a person entity."""

    name: str
    state: str = "unknown"  # home, not_home, unknown


class AreaLightStatus(BaseModel):
    """Aggregated light counts for a single area."""

    area: str
    on_count: int = 0
    off_count: int = 0


class SensorStatus(BaseModel):
    """Human-readable state for a binary sensor."""

    name: str
    state: str  # open/closed, detected/clear
    device_class: str = ""


class RoomOccupancy(BaseModel):
    """Presence roll-up for a single area.

    ``state`` is ``"detected"`` when any contributing sensor is tripped,
    ``"clear"`` when all are clear, and ``"unknown"`` when the area has no
    presence-capable sensor at all — never conflated with ``"clear"``.
    """

    area_id: str
    state: str = "unknown"  # detected, clear, unknown
    contributing_entity_ids: list[str] = Field(default_factory=list)
    last_changed: str = ""


class HouseStatusResponse(BaseModel):
    """Full house status snapshot returned by GET /api/status/house.

    ``room_occupancy`` is unchanged since TAP-7585/7586: areas a presence
    sensor has reported for, only. ``rooms`` (TAP-7587) is additive — the
    same roll-up unioned with every area known to data-api, so a
    zero-sensor area appears as ``unknown`` instead of being omitted. It
    defaults to the same content as ``room_occupancy`` until a caller with
    access to the known-area set (see ``house_status.known_areas``)
    supplies the richer version.
    """

    climate: list[ClimateStatus] = Field(default_factory=list)
    presence: list[PresenceStatus] = Field(default_factory=list)
    lights_by_area: list[AreaLightStatus] = Field(default_factory=list)
    sensors: dict[str, list[SensorStatus]] = Field(default_factory=dict)
    room_occupancy: list[RoomOccupancy] = Field(default_factory=list)
    rooms: list[RoomOccupancy] = Field(default_factory=list)
    switches_on: list[str] = Field(default_factory=list)
    active_automations: list[str] = Field(default_factory=list)
    timestamp: str = ""


class RoomsResponse(BaseModel):
    """Response body for GET /api/status/rooms (TAP-7587)."""

    rooms: list[RoomOccupancy] = Field(default_factory=list)
