"""
Drift Detection

Epic B4: Detect removed entities/services and invalidate specs
"""

import logging
from typing import Any, Dict, List, Set

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
        service_inventory: ServiceInventory
    ):
        """
        Initialize drift detector.
        
        Args:
            entity_inventory: EntityInventory instance
            service_inventory: ServiceInventory instance
        """
        self.entity_inventory = entity_inventory
        self.service_inventory = service_inventory
        self.last_entity_snapshot: Set[str] = set()
        self.last_service_snapshot: Set[str] = set()
    
    def detect_entity_drift(
        self,
        current_entities: Set[str]
    ) -> Dict[str, Any]:
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
        current_services: Set[str]
    ) -> Dict[str, Any]:
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
        removed_entities: List[str],
        removed_services: List[str]
    ) -> List[str]:
        """
        Get list of spec IDs that would be affected by drift.
        
        Args:
            removed_entities: List of removed entity IDs
            removed_services: List of removed service keys
        
        Returns:
            List of affected spec IDs (placeholder - would need spec registry)
        """
        # TODO: Query spec registry for specs using removed entities/services
        # For now, return empty list
        affected = []
        
        if removed_entities or removed_services:
            logger.warning(
                f"Drift would affect specs using: "
                f"{len(removed_entities)} entities, {len(removed_services)} services"
            )
        
        return affected
