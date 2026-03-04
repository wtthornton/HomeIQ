"""House status snapshot service.

Builds a comprehensive house status from cached HA entities,
ported from Sapphire's homeassistant.py:857-1005.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entity_resolver import EntityResolver

logger = logging.getLogger(__name__)

# Binary sensor device classes and their human-readable state mappings
_BINARY_SENSOR_LABELS: dict[str, dict[str, str]] = {
    "door": {"on": "open", "off": "closed"},
    "window": {"on": "open", "off": "closed"},
    "motion": {"on": "detected", "off": "clear"},
    "occupancy": {"on": "occupied", "off": "unoccupied"},
    "lock": {"on": "unlocked", "off": "locked"},
    "garage_door": {"on": "open", "off": "closed"},
    "opening": {"on": "open", "off": "closed"},
}


@dataclass
class AreaLightSummary:
    """Light status summary for a single area."""

    area: str
    on_count: int
    off_count: int
    lights: list[dict[str, str]]


@dataclass
class BinarySensorSummary:
    """Summary of a binary sensor with human-readable state."""

    entity_id: str
    friendly_name: str
    device_class: str
    state: str  # Human-readable: "open", "closed", "detected", etc.
    area: str


@dataclass
class ClimateSummary:
    """Climate zone summary."""

    entity_id: str
    friendly_name: str
    area: str
    current_temperature: float | None
    target_temperature: float | None
    hvac_mode: str
    unit: str


@dataclass
class HouseStatus:
    """Full house status snapshot."""

    climate: list[ClimateSummary] = field(default_factory=list)
    presence: list[dict[str, str]] = field(default_factory=list)
    lights_by_area: list[AreaLightSummary] = field(default_factory=list)
    binary_sensors: list[BinarySensorSummary] = field(default_factory=list)
    active_switches: list[dict[str, str]] = field(default_factory=list)
    active_automations: list[dict[str, str]] = field(default_factory=list)


class StatusService:
    """Builds a house status snapshot from cached HA entities."""

    def __init__(self, entity_resolver: EntityResolver) -> None:
        self._resolver = entity_resolver

    async def get_house_status(self) -> HouseStatus:
        """Build and return the full house status snapshot."""
        status = HouseStatus()

        status.climate = await self._get_climate()
        status.presence = await self._get_presence()
        status.lights_by_area = await self._get_lights_by_area()
        status.binary_sensors = await self._get_binary_sensors()
        status.active_switches = await self._get_active_switches()
        status.active_automations = await self._get_active_automations()

        return status

    async def _get_climate(self) -> list[ClimateSummary]:
        """Get climate/thermostat summaries for all zones."""
        entities = await self._resolver.list_entities(domain_filter="climate")
        results: list[ClimateSummary] = []
        for ent in entities:
            results.append(
                ClimateSummary(
                    entity_id=ent.entity_id,
                    friendly_name=ent.friendly_name,
                    area=ent.area,
                    current_temperature=ent.attributes.get("current_temperature"),
                    target_temperature=ent.attributes.get("temperature"),
                    hvac_mode=ent.state,
                    unit=ent.attributes.get("temperature_unit", "\u00b0C"),
                )
            )
        return results

    async def _get_presence(self) -> list[dict[str, str]]:
        """Get person entity states for presence tracking."""
        entities = await self._resolver.list_entities(domain_filter="person")
        return [
            {
                "entity_id": ent.entity_id,
                "name": ent.friendly_name,
                "state": ent.state,
            }
            for ent in entities
        ]

    async def _get_lights_by_area(self) -> list[AreaLightSummary]:
        """Get light on/off counts grouped by area."""
        entities = await self._resolver.list_entities(domain_filter="light")

        area_map: dict[str, list[dict[str, str]]] = {}
        for ent in entities:
            area = ent.area or "Unknown"
            if area not in area_map:
                area_map[area] = []
            area_map[area].append({
                "entity_id": ent.entity_id,
                "name": ent.friendly_name,
                "state": ent.state,
            })

        results: list[AreaLightSummary] = []
        for area, lights in sorted(area_map.items()):
            on_count = sum(1 for lt in lights if lt["state"] == "on")
            off_count = len(lights) - on_count
            results.append(
                AreaLightSummary(
                    area=area,
                    on_count=on_count,
                    off_count=off_count,
                    lights=lights,
                )
            )
        return results

    async def _get_binary_sensors(self) -> list[BinarySensorSummary]:
        """Get binary sensors with human-readable states."""
        entities = await self._resolver.list_entities(domain_filter="binary_sensor")
        results: list[BinarySensorSummary] = []

        for ent in entities:
            device_class = ent.attributes.get("device_class", "")
            if device_class not in _BINARY_SENSOR_LABELS:
                continue

            label_map = _BINARY_SENSOR_LABELS[device_class]
            human_state = label_map.get(ent.state, ent.state)

            results.append(
                BinarySensorSummary(
                    entity_id=ent.entity_id,
                    friendly_name=ent.friendly_name,
                    device_class=device_class,
                    state=human_state,
                    area=ent.area,
                )
            )

        return results

    async def _get_active_switches(self) -> list[dict[str, str]]:
        """Get switches that are currently on."""
        entities = await self._resolver.list_entities(domain_filter="switch")
        return [
            {
                "entity_id": ent.entity_id,
                "name": ent.friendly_name,
                "area": ent.area,
            }
            for ent in entities
            if ent.state == "on"
        ]

    async def _get_active_automations(self) -> list[dict[str, str]]:
        """Get automations that are currently enabled/on."""
        entities = await self._resolver.list_entities(domain_filter="automation")
        return [
            {
                "entity_id": ent.entity_id,
                "name": ent.friendly_name,
                "state": ent.state,
            }
            for ent in entities
            if ent.state == "on"
        ]
