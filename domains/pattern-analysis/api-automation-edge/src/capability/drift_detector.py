"""
Drift Detection

Epic B4: Detect removed entities/services and invalidate specs
Epic 7, Story 5a: Implement get_affected_specs() to query spec registry
"""

import json
import logging
from typing import Any

from .entity_inventory import EntityInventory
from .service_inventory import ServiceInventory

logger = logging.getLogger(__name__)


class DriftDetector:
    """
    Detector for capability graph drift.

    Features:
    - Detect removed entities/services
    - Invalidate affected specs
    - Alert on capability graph changes
    """

    def __init__(
        self,
        entity_inventory: EntityInventory,
        service_inventory: ServiceInventory,
        spec_registry: Any | None = None,
    ):
        """
        Initialize drift detector.

        Args:
            entity_inventory: EntityInventory instance
            service_inventory: ServiceInventory instance
            spec_registry: Optional SpecRegistry instance for affected-spec lookups
        """
        self.entity_inventory = entity_inventory
        self.service_inventory = service_inventory
        self.spec_registry = spec_registry
        self.last_entity_snapshot: set[str] = set()
        self.last_service_snapshot: set[str] = set()

    def detect_entity_drift(
        self,
        current_entities: set[str]
    ) -> dict[str, Any]:
        """
        Detect entity drift (removed entities).

        Args:
            current_entities: Set of current entity IDs

        Returns:
            Dictionary with drift information
        """
        if not self.last_entity_snapshot:
            # First run - no drift
            self.last_entity_snapshot = current_entities.copy()
            return {
                "removed_entities": [],
                "added_entities": [],
                "has_drift": False
            }

        removed = self.last_entity_snapshot - current_entities
        added = current_entities - self.last_entity_snapshot

        has_drift = len(removed) > 0 or len(added) > 0

        if has_drift:
            logger.warning(
                f"Entity drift detected: {len(removed)} removed, {len(added)} added"
            )

            # Remove entities from inventory
            for entity_id in removed:
                self.entity_inventory.remove_entity(entity_id)

        # Update snapshot
        self.last_entity_snapshot = current_entities.copy()

        return {
            "removed_entities": list(removed),
            "added_entities": list(added),
            "has_drift": has_drift
        }

    def detect_service_drift(
        self,
        current_services: set[str]
    ) -> dict[str, Any]:
        """
        Detect service drift (removed services).

        Args:
            current_services: Set of current service keys (domain.service)

        Returns:
            Dictionary with drift information
        """
        if not self.last_service_snapshot:
            # First run - no drift
            self.last_service_snapshot = current_services.copy()
            return {
                "removed_services": [],
                "added_services": [],
                "has_drift": False
            }

        removed = self.last_service_snapshot - current_services
        added = current_services - self.last_service_snapshot

        has_drift = len(removed) > 0 or len(added) > 0

        if has_drift:
            logger.warning(
                f"Service drift detected: {len(removed)} removed, {len(added)} added"
            )

        # Update snapshot
        self.last_service_snapshot = current_services.copy()

        return {
            "removed_services": list(removed),
            "added_services": list(added),
            "has_drift": has_drift
        }

    def get_affected_specs(
        self,
        removed_entities: list[str],
        removed_services: list[str],
    ) -> list[str]:
        """
        Get list of spec IDs that would be affected by drift.

        Queries the spec registry for active specs whose actions reference
        any of the removed entities or services.

        Args:
            removed_entities: List of removed entity IDs
            removed_services: List of removed service keys

        Returns:
            List of affected spec IDs
        """
        if not removed_entities and not removed_services:
            return []

        if self.spec_registry is None:
            logger.warning(
                "No spec registry configured -- cannot determine affected specs "
                "(entities=%d, services=%d)",
                len(removed_entities), len(removed_services),
            )
            return []

        removed_entity_set = set(removed_entities)
        removed_service_set = set(removed_services)
        affected: list[str] = []

        try:
            # Scan all homes' active specs for references to removed entities/services
            # SpecRegistry stores specs as JSON; we search the content
            from ..registry.spec_registry import SpecVersion

            db = self.spec_registry.SessionLocal()
            try:
                active_versions = db.query(SpecVersion).filter(
                    SpecVersion.is_active == True  # noqa: E712
                ).all()

                for sv in active_versions:
                    spec_content = json.loads(sv.spec_content) if isinstance(sv.spec_content, str) else sv.spec_content
                    spec_id = spec_content.get("id", sv.spec_id)

                    # Check actions for entity references
                    actions = spec_content.get("actions", [])
                    for action in actions:
                        # Check resolved_entity_ids
                        entity_ids = action.get("resolved_entity_ids", [])
                        if isinstance(entity_ids, list) and removed_entity_set.intersection(entity_ids):
                            if spec_id not in affected:
                                affected.append(spec_id)
                            break

                        # Check target entity_id
                        target = action.get("target", {})
                        target_entity = target.get("entity_id")
                        if isinstance(target_entity, str) and target_entity in removed_entity_set:
                            if spec_id not in affected:
                                affected.append(spec_id)
                            break
                        if isinstance(target_entity, list) and removed_entity_set.intersection(target_entity):
                            if spec_id not in affected:
                                affected.append(spec_id)
                            break

                        # Check capability -> service mapping
                        capability = action.get("capability", "")
                        if capability in removed_service_set:
                            if spec_id not in affected:
                                affected.append(spec_id)
                            break
            finally:
                db.close()

        except Exception as e:
            logger.error("Failed to query spec registry for affected specs: %s", e)

        if affected:
            logger.warning(
                "Drift affects %d specs: %s (entities=%d, services=%d)",
                len(affected), affected, len(removed_entities), len(removed_services),
            )

        return affected
