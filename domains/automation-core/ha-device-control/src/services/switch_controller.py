"""Switch controller service.

Simple on/off control for switch entities, ported from Sapphire's
homeassistant.py:790-800.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entity_resolver import EntityResolver
    from .ha_rest_client import HARestClient

from .light_controller import ControlResult

logger = logging.getLogger(__name__)


class SwitchController:
    """Controls switch entities (on/off)."""

    def __init__(
        self,
        ha_client: HARestClient,
        entity_resolver: EntityResolver,
    ) -> None:
        self._ha = ha_client
        self._resolver = entity_resolver

    async def set_switch(
        self,
        name_or_id: str,
        state: str,
    ) -> ControlResult:
        """Turn a switch on or off.

        Args:
            name_or_id: Entity ID or friendly name.
            state: ``"on"`` or ``"off"``.

        Returns:
            ControlResult with outcome.
        """
        entity = await self._resolver.resolve(name_or_id, domain_filter="switch")
        if not entity:
            return ControlResult(
                success=False,
                affected=[],
                message=f"Switch not found: {name_or_id}",
            )

        state_lower = state.lower().strip()
        if state_lower not in ("on", "off"):
            return ControlResult(
                success=False,
                affected=[],
                message=f"Invalid state: {state}. Must be 'on' or 'off'.",
            )

        service = "turn_on" if state_lower == "on" else "turn_off"
        eid = entity.entity_id

        try:
            await self._ha.call_service(
                "switch",
                service,
                {"entity_id": eid},
            )
            logger.info("Switch %s: %s", service.replace("_", " "), eid)
            return ControlResult(
                success=True,
                affected=[eid],
                message=f"{entity.friendly_name} turned {state_lower}",
            )
        except Exception:
            logger.exception("Failed to control switch %s", eid)
            return ControlResult(
                success=False,
                affected=[],
                message=f"Failed to control {entity.friendly_name}",
            )
