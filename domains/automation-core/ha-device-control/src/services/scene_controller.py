"""Scene and script controller service.

Lists and activates HA scenes and scripts, ported from Sapphire's
homeassistant.py:459-530.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .entity_resolver import EntityResolver
    from .ha_rest_client import HARestClient

from .light_controller import ControlResult

logger = logging.getLogger(__name__)


@dataclass
class SceneInfo:
    """Scene or script info for listing."""

    entity_id: str
    friendly_name: str
    entity_type: str  # "scene" or "script"


class SceneController:
    """Lists and activates HA scenes and scripts."""

    def __init__(
        self,
        ha_client: HARestClient,
        entity_resolver: EntityResolver,
    ) -> None:
        self._ha = ha_client
        self._resolver = entity_resolver

    async def list_scenes_and_scripts(self) -> list[SceneInfo]:
        """List all available scenes and scripts.

        Returns friendly names with type annotation.
        """
        results: list[SceneInfo] = []

        for domain in ("scene", "script"):
            entities = await self._resolver.list_entities(domain_filter=domain)
            for ent in entities:
                results.append(
                    SceneInfo(
                        entity_id=ent.entity_id,
                        friendly_name=ent.friendly_name,
                        entity_type=domain,
                    )
                )

        return results

    async def activate(self, name: str) -> ControlResult:
        """Activate a scene or script by name.

        Tries to match by friendly_name, entity_id, or short name
        across both scene and script domains.

        Args:
            name: Scene/script name to activate.

        Returns:
            ControlResult with outcome.
        """
        # Try scenes first, then scripts
        for domain in ("scene", "script"):
            entity = await self._resolver.resolve(name, domain_filter=domain)
            if entity:
                return await self._activate_entity(entity.entity_id, entity.friendly_name, domain)

        return ControlResult(
            success=False,
            affected=[],
            message=f"Scene or script not found: {name}",
        )

    async def _activate_entity(
        self,
        entity_id: str,
        friendly_name: str,
        domain: str,
    ) -> ControlResult:
        """Activate a specific scene or script entity."""
        try:
            await self._ha.call_service(
                domain,
                "turn_on",
                {"entity_id": entity_id},
            )
            logger.info("Activated %s: %s", domain, entity_id)
            return ControlResult(
                success=True,
                affected=[entity_id],
                message=f"Activated {domain} '{friendly_name}'",
            )
        except Exception:
            logger.exception("Failed to activate %s %s", domain, entity_id)
            return ControlResult(
                success=False,
                affected=[],
                message=f"Failed to activate {domain} '{friendly_name}'",
            )
