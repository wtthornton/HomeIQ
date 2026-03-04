"""Climate controller service.

Multi-zone thermostat get/set, ported from Sapphire's
homeassistant.py:670-724 with HomeIQ enhancement for multiple zones.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .entity_resolver import EntityResolver
    from .ha_rest_client import HARestClient

from .light_controller import ControlResult

logger = logging.getLogger(__name__)


@dataclass
class ClimateState:
    """Current state of a climate entity."""

    entity_id: str
    friendly_name: str
    area: str
    current_temperature: float | None
    target_temperature: float | None
    hvac_mode: str
    hvac_modes: list[str]
    unit: str


class ClimateController:
    """Controls climate/thermostat entities with multi-zone support."""

    def __init__(
        self,
        ha_client: HARestClient,
        entity_resolver: EntityResolver,
    ) -> None:
        self._ha = ha_client
        self._resolver = entity_resolver

    async def get_climate_entities(self) -> list[ClimateState]:
        """List all climate entities with their current state.

        Unlike Sapphire (which only returns the first thermostat),
        this returns all climate entities for multi-zone support.
        """
        entities = await self._resolver.list_entities(domain_filter="climate")
        results: list[ClimateState] = []

        for ent in entities:
            results.append(
                ClimateState(
                    entity_id=ent.entity_id,
                    friendly_name=ent.friendly_name,
                    area=ent.area,
                    current_temperature=ent.attributes.get("current_temperature"),
                    target_temperature=ent.attributes.get("temperature"),
                    hvac_mode=ent.state,
                    hvac_modes=ent.attributes.get("hvac_modes", []),
                    unit=ent.attributes.get("temperature_unit", "°C"),
                )
            )

        return results

    async def set_climate(
        self,
        entity_id: str,
        temperature: float,
        hvac_mode: str | None = None,
    ) -> ControlResult:
        """Set temperature (and optionally HVAC mode) on a climate entity.

        Args:
            entity_id: The climate entity ID.
            temperature: Target temperature.
            hvac_mode: Optional HVAC mode (e.g. ``heat``, ``cool``, ``auto``).

        Returns:
            ControlResult with outcome.
        """
        entity = await self._resolver.resolve(entity_id, domain_filter="climate")
        if not entity:
            return ControlResult(
                success=False,
                affected=[],
                message=f"Climate entity not found: {entity_id}",
            )

        eid = entity.entity_id

        try:
            # Set temperature
            service_data: dict[str, Any] = {
                "entity_id": eid,
                "temperature": temperature,
            }
            await self._ha.call_service("climate", "set_temperature", service_data)
            logger.info("Climate %s: temperature set to %s", eid, temperature)

            # Set HVAC mode if provided
            if hvac_mode:
                valid_modes = entity.attributes.get("hvac_modes", [])
                if hvac_mode in valid_modes:
                    await self._ha.call_service(
                        "climate",
                        "set_hvac_mode",
                        {"entity_id": eid, "hvac_mode": hvac_mode},
                    )
                    logger.info("Climate %s: HVAC mode set to %s", eid, hvac_mode)
                else:
                    logger.warning(
                        "HVAC mode '%s' not valid for %s (valid: %s)",
                        hvac_mode,
                        eid,
                        valid_modes,
                    )

            # Fetch updated state
            try:
                updated = await self._ha.get_state(eid)
                attrs = updated.get("attributes", {})
                target = attrs.get("temperature", temperature)
                current = attrs.get("current_temperature", "unknown")
                mode = updated.get("state", "unknown")
                msg = (
                    f"{entity.friendly_name}: target {target}°, "
                    f"current {current}°, mode {mode}"
                )
            except Exception:
                msg = f"{entity.friendly_name}: temperature set to {temperature}°"

            return ControlResult(
                success=True,
                affected=[eid],
                message=msg,
            )

        except Exception:
            logger.exception("Failed to control climate %s", eid)
            return ControlResult(
                success=False,
                affected=[],
                message=f"Failed to control {entity.friendly_name}",
            )
