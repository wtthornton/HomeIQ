"""Light controller service.

Handles individual and area-wide light control including brightness
and RGB color, ported from Sapphire's homeassistant.py:561-787.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .entity_resolver import EntityResolver, ResolvedEntity
    from .ha_rest_client import HARestClient

logger = logging.getLogger(__name__)


@dataclass
class ControlResult:
    """Standard result from a control operation."""

    success: bool
    affected: list[str]
    message: str


class LightController:
    """Controls individual lights and area-wide light groups."""

    def __init__(
        self,
        ha_client: HARestClient,
        entity_resolver: EntityResolver,
    ) -> None:
        self._ha = ha_client
        self._resolver = entity_resolver

    async def set_light(
        self,
        name_or_id: str,
        brightness: int,
        rgb: list[int] | None = None,
    ) -> ControlResult:
        """Control a single light by name or entity ID.

        Args:
            name_or_id: Entity ID or friendly name.
            brightness: 0 (off) to 100 (full).
            rgb: Optional [R, G, B] each 0-255.

        Returns:
            ControlResult with outcome.
        """
        entity = await self._resolver.resolve(name_or_id, domain_filter="light")
        if not entity:
            return ControlResult(
                success=False,
                affected=[],
                message=f"Light not found: {name_or_id}",
            )

        return await self._apply_light(entity, brightness, rgb)

    async def set_area_lights(
        self,
        area: str,
        brightness: int,
        rgb: list[int] | None = None,
    ) -> ControlResult:
        """Control all lights in an area.

        Args:
            area: Area name (case-insensitive).
            brightness: 0 (off) to 100 (full).
            rgb: Optional [R, G, B] each 0-255.

        Returns:
            ControlResult with combined outcome.
        """
        entities = await self._resolver.resolve_by_area(area, domain_filter="light")
        if not entities:
            return ControlResult(
                success=False,
                affected=[],
                message=f"No lights found in area: {area}",
            )

        affected: list[str] = []
        errors: list[str] = []

        for entity in entities:
            result = await self._apply_light(entity, brightness, rgb)
            if result.success:
                affected.extend(result.affected)
            else:
                errors.append(result.message)

        if not affected:
            return ControlResult(
                success=False,
                affected=[],
                message=f"Failed to control lights in {area}: {'; '.join(errors)}",
            )

        action = "turned off" if brightness == 0 else f"set to {brightness}%"
        return ControlResult(
            success=True,
            affected=affected,
            message=f"{len(affected)} light(s) in {area} {action}",
        )

    async def _apply_light(
        self,
        entity: ResolvedEntity,
        brightness: int,
        rgb: list[int] | None = None,
    ) -> ControlResult:
        """Apply brightness and optional color to a single light entity."""
        brightness = max(0, min(100, brightness))
        eid = entity.entity_id

        try:
            if brightness == 0:
                # Turn off
                await self._ha.call_service(
                    "light",
                    "turn_off",
                    {"entity_id": eid},
                )
                logger.info("Light turned off: %s", eid)
                return ControlResult(
                    success=True,
                    affected=[eid],
                    message=f"{entity.friendly_name} turned off",
                )

            # Turn on with brightness (0-100 -> 0-255)
            service_data: dict[str, Any] = {
                "entity_id": eid,
                "brightness": round(brightness * 255 / 100),
            }

            # Add color if supported and requested
            if rgb and self._supports_color(entity):
                service_data["rgb_color"] = rgb

            await self._ha.call_service("light", "turn_on", service_data)
            logger.info("Light set: %s brightness=%d rgb=%s", eid, brightness, rgb)
            return ControlResult(
                success=True,
                affected=[eid],
                message=f"{entity.friendly_name} set to {brightness}%",
            )

        except Exception:
            logger.exception("Failed to control light %s", eid)
            return ControlResult(
                success=False,
                affected=[],
                message=f"Failed to control {entity.friendly_name}",
            )

    @staticmethod
    def _supports_color(entity: ResolvedEntity) -> bool:
        """Check if the light supports RGB color mode."""
        modes = entity.attributes.get("supported_color_modes", [])
        color_modes = {"rgb", "hs", "xy", "rgbw", "rgbww"}
        return bool(set(modes) & color_modes)
