"""In-memory house status aggregator.

Listens to ``state_changed`` events from the existing event processing
pipeline and maintains categorised snapshots that are served via REST
and pushed over WebSocket.

Thread-safe via ``asyncio.Lock``.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from .models import (
    AreaLightStatus,
    ClimateStatus,
    HouseStatusResponse,
    PresenceStatus,
    RoomOccupancy,
    SensorStatus,
)

logger = logging.getLogger(__name__)

# Binary-sensor device classes that map to human-readable labels.
_BINARY_SENSOR_LABELS: dict[str, tuple[str, str]] = {
    "door": ("open", "closed"),
    "window": ("open", "closed"),
    "motion": ("detected", "clear"),
    "occupancy": ("detected", "clear"),
    "presence": ("detected", "clear"),
    "garage_door": ("open", "closed"),
    "opening": ("open", "closed"),
    "lock": ("unlocked", "locked"),
}

# Device classes that indicate a sensor can speak to whether a room is
# occupied. TAP-7585: the room roll-up must key off this single constant,
# never an inlined device-class literal at a call site.
_PRESENCE_DEVICE_CLASSES: frozenset[str] = frozenset({"motion", "occupancy", "presence"})


class HouseStatusAggregator:
    """Maintains current house state derived from HA events.

    Parameters
    ----------
    discovery_service:
        Optional ``DiscoveryService`` used to resolve entity-to-area
        mappings.  When *None* lights are grouped under ``"unknown"``.
    influxdb_batch_writer:
        Optional ``InfluxDBBatchWriter`` (duck-typed via ``write_room_occupancy``)
        used to persist room-occupancy state transitions. When *None* the
        roll-up is still maintained in memory but nothing is written.
    """

    def __init__(
        self,
        discovery_service: Any | None = None,
        influxdb_batch_writer: Any | None = None,
    ) -> None:
        self._lock = asyncio.Lock()
        self._discovery = discovery_service
        self._batch_writer = influxdb_batch_writer

        # Category caches keyed by entity_id unless noted otherwise.
        self._climate: dict[str, dict[str, Any]] = {}
        self._presence: dict[str, dict[str, Any]] = {}
        # lights: entity_id -> {state, area}
        self._lights: dict[str, dict[str, Any]] = {}
        # binary_sensors: entity_id -> {name, state, device_class}
        self._binary_sensors: dict[str, dict[str, Any]] = {}
        # room occupancy roll-up, keyed by area_id (including "unknown" for
        # entities whose area can't be resolved):
        # area_id -> {entities: {entity_id: raw_state}, last_changed}
        self._room_occupancy: dict[str, dict[str, Any]] = {}
        # area_id -> last resolved state persisted to InfluxDB. Used to
        # detect a transition; a repeated identical resolved state must
        # never enqueue another point (cardinality bound).
        self._room_occupancy_last_written_state: dict[str, str] = {}
        self._switches: dict[str, str] = {}  # entity_id -> state
        self._automations: dict[str, str] = {}  # entity_id -> state

        self._ready = False
        logger.info("HouseStatusAggregator initialised")

    # -- public API -----------------------------------------------------------

    @property
    def ready(self) -> bool:
        """Return ``True`` once at least one event has been processed."""
        return self._ready

    async def process_state_change(
        self,
        entity_id: str,
        new_state: dict[str, Any],
        old_state: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Process a state-change event and return a delta dict, or *None*.

        The returned delta has the shape ``{"section": "<name>", "data": ...}``
        suitable for broadcast via WebSocket.
        """
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        handler = self._DOMAIN_HANDLERS.get(domain)
        if handler is None:
            return None

        async with self._lock:
            self._ready = True
            return await handler(self, entity_id, new_state, old_state)

    async def get_snapshot(self) -> HouseStatusResponse:
        """Return a full snapshot of the current house status."""
        async with self._lock:
            return self._build_snapshot()

    # -- private handlers per domain ------------------------------------------

    async def _handle_climate(
        self,
        entity_id: str,
        new_state: dict[str, Any],
        _old_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        attrs = new_state.get("attributes") or {}
        self._climate[entity_id] = {
            "entity_id": entity_id,
            "friendly_name": attrs.get("friendly_name", entity_id),
            "current_temperature": attrs.get("current_temperature"),
            "target_temperature": attrs.get("temperature"),
            "hvac_mode": new_state.get("state", "off"),
            "unit": attrs.get("temperature_unit", "C"),
        }
        return {"section": "climate", "data": self._climate[entity_id]}

    async def _handle_person(
        self,
        entity_id: str,
        new_state: dict[str, Any],
        _old_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        attrs = new_state.get("attributes") or {}
        name = attrs.get("friendly_name", entity_id)
        state = new_state.get("state", "unknown")
        self._presence[entity_id] = {"name": name, "state": state}
        return {"section": "presence", "data": self._presence[entity_id]}

    async def _handle_light(
        self,
        entity_id: str,
        new_state: dict[str, Any],
        _old_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        area = self._resolve_area(entity_id)
        self._lights[entity_id] = {
            "state": new_state.get("state", "off"),
            "area": area,
        }
        # Return aggregated area counts.
        area_counts = self._aggregate_lights()
        return {"section": "lights_by_area", "data": area_counts}

    async def _handle_binary_sensor(
        self,
        entity_id: str,
        new_state: dict[str, Any],
        _old_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        attrs = new_state.get("attributes") or {}
        device_class = attrs.get("device_class", "")
        name = attrs.get("friendly_name", entity_id)
        raw_state = new_state.get("state", "off")
        human = self._humanise_binary(device_class, raw_state)
        self._binary_sensors[entity_id] = {
            "name": name,
            "state": human,
            "device_class": device_class,
        }
        if device_class in _PRESENCE_DEVICE_CLASSES:
            area_id = self._resolve_area(entity_id)
            await self._update_room_occupancy(area_id, entity_id, raw_state)
        return {"section": "sensors", "data": self._binary_sensors[entity_id]}

    async def _handle_switch(
        self,
        entity_id: str,
        new_state: dict[str, Any],
        _old_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        self._switches[entity_id] = new_state.get("state", "off")
        switches_on = [eid for eid, st in self._switches.items() if st == "on"]
        return {"section": "switches_on", "data": switches_on}

    async def _handle_automation(
        self,
        entity_id: str,
        new_state: dict[str, Any],
        _old_state: dict[str, Any] | None,
    ) -> dict[str, Any]:
        self._automations[entity_id] = new_state.get("state", "off")
        active = [eid for eid, st in self._automations.items() if st == "on"]
        return {"section": "active_automations", "data": active}

    # Handler dispatch table (avoids long if/elif chains).
    _DOMAIN_HANDLERS: dict[str, Any] = {
        "climate": _handle_climate,
        "person": _handle_person,
        "light": _handle_light,
        "binary_sensor": _handle_binary_sensor,
        "switch": _handle_switch,
        "automation": _handle_automation,
    }

    # -- helpers --------------------------------------------------------------

    def _resolve_area(self, entity_id: str) -> str:
        """Best-effort entity-to-area lookup via the discovery service."""
        if not self._discovery:
            return "unknown"
        area = self._discovery.entity_to_area.get(entity_id)
        if area:
            return area
        device_id = self._discovery.entity_to_device.get(entity_id)
        if device_id:
            return self._discovery.device_to_area.get(device_id, "unknown")
        return "unknown"

    async def _update_room_occupancy(self, area_id: str, entity_id: str, raw_state: str) -> None:
        """Record a presence-capable sensor's latest state under its area.

        Persists a point to InfluxDB only when the area's rolled-up state
        actually transitions (TAP-7586) — a point per inbound event would
        blow up cardinality, so a repeated identical resolved state writes
        nothing.
        """
        room = self._room_occupancy.setdefault(area_id, {"entities": {}, "last_changed": ""})
        room["entities"][entity_id] = raw_state
        room["last_changed"] = datetime.now(UTC).isoformat()

        resolved = self._resolve_room_occupancy(area_id)
        if self._room_occupancy_last_written_state.get(area_id) == resolved.state:
            return

        self._room_occupancy_last_written_state[area_id] = resolved.state
        if self._batch_writer is not None:
            await self._batch_writer.write_room_occupancy(
                area_id=area_id,
                state=resolved.state,
                contributing_entity_count=len(resolved.contributing_entity_ids),
            )

    def _resolve_room_occupancy(self, area_id: str) -> RoomOccupancy:
        """Return the roll-up for one area.

        An area with no presence-capable sensor reports ``"unknown"`` — it
        must never be indistinguishable from an area whose sensors are all
        clear.
        """
        room = self._room_occupancy.get(area_id)
        if not room or not room["entities"]:
            return RoomOccupancy(area_id=area_id, state="unknown")
        state = "detected" if any(s == "on" for s in room["entities"].values()) else "clear"
        return RoomOccupancy(
            area_id=area_id,
            state=state,
            contributing_entity_ids=sorted(room["entities"]),
            last_changed=room["last_changed"],
        )

    def _aggregate_lights(self) -> list[dict[str, Any]]:
        """Aggregate light on/off counts by area."""
        areas: dict[str, dict[str, int]] = {}
        for info in self._lights.values():
            area = info.get("area", "unknown")
            if area not in areas:
                areas[area] = {"on": 0, "off": 0}
            if info.get("state") == "on":
                areas[area]["on"] += 1
            else:
                areas[area]["off"] += 1
        return [
            {"area": a, "on_count": c["on"], "off_count": c["off"]}
            for a, c in sorted(areas.items())
        ]

    @staticmethod
    def _humanise_binary(device_class: str, raw_state: str) -> str:
        """Translate a binary-sensor state to human-readable text."""
        labels = _BINARY_SENSOR_LABELS.get(device_class)
        if labels:
            return labels[0] if raw_state == "on" else labels[1]
        return raw_state

    def _build_snapshot(self) -> HouseStatusResponse:
        """Build a full ``HouseStatusResponse`` from internal caches."""
        # Climate
        climate = [ClimateStatus(**v) for v in self._climate.values()]

        # Presence
        presence = [PresenceStatus(**v) for v in self._presence.values()]

        # Lights by area
        lights_by_area = [AreaLightStatus(**a) for a in self._aggregate_lights()]

        # Sensors grouped by device_class
        sensor_groups: dict[str, list[SensorStatus]] = {}
        for info in self._binary_sensors.values():
            dc = info.get("device_class", "other")
            if dc not in sensor_groups:
                sensor_groups[dc] = []
            sensor_groups[dc].append(SensorStatus(**info))

        # Room occupancy roll-up, for every area a presence sensor has been seen in
        room_occupancy = [
            self._resolve_room_occupancy(area_id) for area_id in sorted(self._room_occupancy)
        ]

        # Switches currently on
        switches_on = [eid for eid, st in self._switches.items() if st == "on"]

        # Active automations
        active_automations = [eid for eid, st in self._automations.items() if st == "on"]

        return HouseStatusResponse(
            climate=climate,
            presence=presence,
            lights_by_area=lights_by_area,
            sensors=sensor_groups,
            room_occupancy=room_occupancy,
            switches_on=switches_on,
            active_automations=active_automations,
            timestamp=datetime.now(UTC).isoformat(),
        )
