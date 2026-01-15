"""
Entity Inventory

Epic B1: Build entity inventory from HA states
"""

import logging
from typing import Any, Dict, List, Optional

from ..clients.ha_rest_client import HARestClient

logger = logging.getLogger(__name__)


class EntityInventory:
    """
    Entity inventory builder from Home Assistant states.
    
    Features:
    - Boot: GET /api/states to get full state snapshot
    - Normalize: domain, device_class, supported_features, availability
    - Build entity→area/device maps using /api/states metadata
    - Store in capability graph cache
    """
    
    def __init__(self, rest_client: Optional[HARestClient] = None):
        """
        Initialize entity inventory.
        
        Args:
            rest_client: Optional HARestClient instance
        """
        self.rest_client = rest_client or HARestClient()
        self.entities: Dict[str, Dict[str, Any]] = {}
        self.entity_to_area: Dict[str, str] = {}
        self.entity_to_device: Dict[str, str] = {}
        self.area_to_entities: Dict[str, List[str]] = {}
        self.device_to_entities: Dict[str, List[str]] = {}
    
    async def refresh(self) -> Dict[str, Any]:
        """
        Refresh entity inventory from HA.
        
        Returns:
            Dictionary with refresh statistics
        """
        logger.info("Refreshing entity inventory from HA")
        
        try:
            # Get all states
            states = await self.rest_client.get_states()
            
            # Clear existing data
            self.entities.clear()
            self.entity_to_area.clear()
            self.entity_to_device.clear()
            self.area_to_entities.clear()
            self.device_to_entities.clear()
            
            # Process each state
            for state in states:
                entity_id = state.get("entity_id")
                if not entity_id:
                    continue
                
                # Normalize entity data
                entity = self._normalize_entity(state)
                self.entities[entity_id] = entity
                
                # Build mappings
                area_id = entity.get("area_id")
                device_id = entity.get("device_id")
                
                if area_id:
                    self.entity_to_area[entity_id] = area_id
                    if area_id not in self.area_to_entities:
                        self.area_to_entities[area_id] = []
                    self.area_to_entities[area_id].append(entity_id)
                
                if device_id:
                    self.entity_to_device[entity_id] = device_id
                    if device_id not in self.device_to_entities:
                        self.device_to_entities[device_id] = []
                    self.device_to_entities[device_id].append(entity_id)
            
            logger.info(
                f"Refreshed entity inventory: {len(self.entities)} entities, "
                f"{len(self.area_to_entities)} areas, {len(self.device_to_entities)} devices"
            )
            
            return {
                "entity_count": len(self.entities),
                "area_count": len(self.area_to_entities),
                "device_count": len(self.device_to_entities)
            }
            
        except Exception as e:
            logger.error(f"Failed to refresh entity inventory: {e}")
            raise
    
    def _normalize_entity(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize entity state data.
        
        Args:
            state: Raw state from HA
        
        Returns:
            Normalized entity dictionary
        """
        entity_id = state.get("entity_id", "")
        domain = entity_id.split(".")[0] if "." in entity_id else ""
        
        attributes = state.get("attributes", {})
        
        return {
            "entity_id": entity_id,
            "domain": domain,
            "device_class": attributes.get("device_class"),
            "supported_features": attributes.get("supported_features", 0),
            "state": state.get("state"),
            "last_updated": state.get("last_updated"),
            "last_changed": state.get("last_changed"),
            "friendly_name": attributes.get("friendly_name"),
            "area_id": attributes.get("area_id"),
            "device_id": attributes.get("device_id"),
            "unit_of_measurement": attributes.get("unit_of_measurement"),
            "available": state.get("state") != "unavailable",
            "attributes": attributes
        }
    
    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get entity by ID"""
        return self.entities.get(entity_id)
    
    def get_entities_by_area(self, area_id: str) -> List[Dict[str, Any]]:
        """Get all entities in an area"""
        entity_ids = self.area_to_entities.get(area_id, [])
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
    
    def get_entities_by_device(self, device_id: str) -> List[Dict[str, Any]]:
        """Get all entities for a device"""
        entity_ids = self.device_to_entities.get(device_id, [])
        return [self.entities[eid] for eid in entity_ids if eid in self.entities]
    
    def get_entities_by_domain(self, domain: str) -> List[Dict[str, Any]]:
        """Get all entities for a domain"""
        return [
            entity for entity in self.entities.values()
            if entity.get("domain") == domain
        ]
    
    def get_entities_by_device_class(self, device_class: str) -> List[Dict[str, Any]]:
        """Get all entities with a specific device class"""
        return [
            entity for entity in self.entities.values()
            if entity.get("device_class") == device_class
        ]
    
    def update_entity(self, entity_id: str, state: Dict[str, Any]):
        """
        Update entity from state_changed event.
        
        Args:
            entity_id: Entity ID
            state: New state data
        """
        if entity_id in self.entities:
            entity = self._normalize_entity(state)
            self.entities[entity_id] = entity
            logger.debug(f"Updated entity: {entity_id}")
        else:
            # New entity
            entity = self._normalize_entity(state)
            self.entities[entity_id] = entity
            
            # Update mappings
            area_id = entity.get("area_id")
            device_id = entity.get("device_id")
            
            if area_id:
                self.entity_to_area[entity_id] = area_id
                if area_id not in self.area_to_entities:
                    self.area_to_entities[area_id] = []
                if entity_id not in self.area_to_entities[area_id]:
                    self.area_to_entities[area_id].append(entity_id)
            
            if device_id:
                self.entity_to_device[entity_id] = device_id
                if device_id not in self.device_to_entities:
                    self.device_to_entities[device_id] = []
                if entity_id not in self.device_to_entities[device_id]:
                    self.device_to_entities[device_id].append(entity_id)
            
            logger.info(f"Added new entity: {entity_id}")
    
    def remove_entity(self, entity_id: str):
        """
        Remove entity (drift detection).
        
        Args:
            entity_id: Entity ID to remove
        """
        if entity_id not in self.entities:
            return
        
        entity = self.entities[entity_id]
        area_id = entity.get("area_id")
        device_id = entity.get("device_id")
        
        # Remove from mappings
        if area_id and area_id in self.area_to_entities:
            self.area_to_entities[area_id] = [
                eid for eid in self.area_to_entities[area_id] if eid != entity_id
            ]
            if not self.area_to_entities[area_id]:
                del self.area_to_entities[area_id]
        
        if device_id and device_id in self.device_to_entities:
            self.device_to_entities[device_id] = [
                eid for eid in self.device_to_entities[device_id] if eid != entity_id
            ]
            if not self.device_to_entities[device_id]:
                del self.device_to_entities[device_id]
        
        # Remove entity
        del self.entities[entity_id]
        self.entity_to_area.pop(entity_id, None)
        self.entity_to_device.pop(entity_id, None)
        
        logger.info(f"Removed entity: {entity_id}")
