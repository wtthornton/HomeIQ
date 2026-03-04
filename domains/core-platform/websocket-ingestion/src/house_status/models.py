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


class HouseStatusResponse(BaseModel):
    """Full house status snapshot returned by GET /api/status/house."""

    climate: list[ClimateStatus] = Field(default_factory=list)
    presence: list[PresenceStatus] = Field(default_factory=list)
    lights_by_area: list[AreaLightStatus] = Field(default_factory=list)
    sensors: dict[str, list[SensorStatus]] = Field(default_factory=dict)
    switches_on: list[str] = Field(default_factory=list)
    active_automations: list[str] = Field(default_factory=list)
    timestamp: str = ""
