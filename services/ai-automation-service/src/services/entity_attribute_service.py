"""
Entity Attribute Service

Fetches entity attributes from Home Assistant and enriches entity data
with complete attribute information for OpenAI context and entity resolution.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class EnrichedEntity:
    """Enriched entity structure with attributes and metadata."""
    
    # Core identification
    entity_id: str
    domain: str
    
    # Core attributes (4 universal)
    friendly_name: Optional[str] = None
    icon: Optional[str] = None
    device_class: Optional[str] = None
    unit_of_measurement: Optional[str] = None
    
    # State
    state: str = "unknown"
    last_changed: Optional[str] = None
    last_updated: Optional[str] = None
    
    # All attributes (raw passthrough)
    attributes: Dict[str, Any] = None
    
    # Derived metadata
    is_group: bool = False  # True if is_hue_group or other group indicators
    integration: str = "unknown"  # hue, mqtt, zigbee, etc.
    supported_features: Optional[int] = None
    
    # Device association
    device_id: Optional[str] = None
    area_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize attributes dict if None."""
        if self.attributes is None:
            self.attributes = {}


class EntityAttributeService:
    """Service for enriching entities with attributes from Home Assistant."""
    
    def __init__(self, ha_client):
        """
        Initialize the service.
        
        Args:
            ha_client: HomeAssistantClient instance for fetching entity state
        """
        self.ha_client = ha_client
    
    async def enrich_entity_with_attributes(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch entity state with attributes from HA and create enriched JSON.
        
        Args:
            entity_id: Entity ID to enrich (e.g., 'light.office')
        
        Returns:
            Dictionary with enriched entity data or None if entity not found
        """
        try:
            # Fetch entity state from Home Assistant
            state_data = await self.ha_client.get_entity_state(entity_id)
            
            if not state_data:
                logger.warning(f"Entity {entity_id} not found in Home Assistant")
                return None
            
            # Extract core attributes
            attributes = state_data.get('attributes', {})
            
            # Build enriched entity
            enriched = {
                'entity_id': entity_id,
                'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown',
                'friendly_name': attributes.get('friendly_name'),
                'icon': attributes.get('icon'),
                'device_class': attributes.get('device_class'),
                'unit_of_measurement': attributes.get('unit_of_measurement'),
                'state': state_data.get('state', 'unknown'),
                'last_changed': state_data.get('last_changed'),
                'last_updated': state_data.get('last_updated'),
                'attributes': attributes,  # All attributes passthrough
                'is_group': self._determine_is_group(entity_id, attributes),
                'integration': self._get_integration_from_attributes(attributes),
                'supported_features': attributes.get('supported_features'),
                'device_id': None,  # Could be fetched from entity registry if needed
                'area_id': attributes.get('area_id')
            }
            
            logger.debug(f"Enriched entity {entity_id}: is_group={enriched['is_group']}, "
                        f"integration={enriched['integration']}")
            
            return enriched
            
        except Exception as e:
            logger.error(f"Error enriching entity {entity_id}: {e}")
            return None
    
    async def enrich_multiple_entities(
        self, 
        entity_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch enrich multiple entities.
        
        Args:
            entity_ids: List of entity IDs to enrich
        
        Returns:
            Dictionary mapping entity_id to enriched entity data
        """
        enriched = {}
        
        # Enrich entities in parallel where possible
        for entity_id in entity_ids:
            enriched_data = await self.enrich_entity_with_attributes(entity_id)
            if enriched_data:
                enriched[entity_id] = enriched_data
        
        logger.info(f"Enriched {len(enriched)} out of {len(entity_ids)} entities")
        
        return enriched
    
    def _determine_is_group(self, entity_id: str, attributes: Dict[str, Any]) -> bool:
        """
        Determine if entity is a group entity.
        
        Args:
            entity_id: Entity ID
            attributes: Entity attributes
        
        Returns:
            True if entity is a group/room entity
        """
        # Check Hue-specific attribute
        if attributes.get('is_hue_group') is True:
            return True
        
        # Check for other group indicators
        # Could add more group detection logic here for other integrations
        
        return False
    
    def _get_integration_from_attributes(self, attributes: Dict[str, Any]) -> str:
        """
        Extract integration/platform name from attributes.
        
        Args:
            attributes: Entity attributes
        
        Returns:
            Integration name (hue, mqtt, zigbee, etc.)
        """
        # Try to detect from known attribute patterns
        if attributes.get('is_hue_group') is not None:
            return 'hue'
        
        # Check for device_id patterns to detect other integrations
        device_id = attributes.get('device_id')
        if device_id:
            # Common patterns for detecting integration
            if 'zigbee' in str(device_id).lower():
                return 'zigbee'
            elif 'mqtt' in str(device_id).lower():
                return 'mqtt'
        
        # Default to 'unknown' if we can't determine
        return 'unknown'
    
    def _determine_entity_type(self, entity_id: str, attributes: Dict[str, Any]) -> str:
        """
        Classify entity type (group, individual, scene, etc.).
        
        Args:
            entity_id: Entity ID
            attributes: Entity attributes
        
        Returns:
            Entity type classification
        """
        # Check for group indicators
        if attributes.get('is_hue_group') is True:
            return 'group'
        
        # Check for scene entities
        if entity_id.startswith('scene.'):
            return 'scene'
        
        # Default to individual
        return 'individual'
    
    def _extract_core_attributes(self, attributes: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract the 4 core universal attributes.
        
        Args:
            attributes: Full attributes dictionary
        
        Returns:
            Dictionary with core attributes
        """
        return {
            'friendly_name': attributes.get('friendly_name'),
            'icon': attributes.get('icon'),
            'device_class': attributes.get('device_class'),
            'unit_of_measurement': attributes.get('unit_of_measurement')
        }

