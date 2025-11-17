"""
Entity Attribute Service

Fetches entity attributes from Home Assistant and enriches entity data
with complete attribute information for OpenAI context and entity resolution.
"""

import logging
import time
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
        self._entity_registry_cache: Optional[Dict[str, Dict[str, Any]]] = None
        self._registry_cache_loaded = False
        self._registry_cache_timestamp: Optional[float] = None
        self._cache_ttl_seconds = 300  # 5 minutes cache TTL
    
    async def _get_entity_registry(self, force_refresh: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Get entity registry with caching and TTL-based refresh.
        
        Args:
            force_refresh: If True, force refresh the cache even if it's still valid
        
        Returns:
            Dictionary mapping entity_id -> entity registry data
        """
        # Check if cache needs refresh (expired or forced)
        needs_refresh = force_refresh or not self._registry_cache_loaded
        if not needs_refresh and self._registry_cache_timestamp:
            cache_age = time.time() - self._registry_cache_timestamp
            if cache_age > self._cache_ttl_seconds:
                logger.info(f"🔄 Entity Registry cache expired ({cache_age:.0f}s old), refreshing...")
                needs_refresh = True
        
        if needs_refresh:
            try:
                logger.info("🔍 Loading Entity Registry cache...")
                self._entity_registry_cache = await self.ha_client.get_entity_registry()
                self._registry_cache_loaded = True
                self._registry_cache_timestamp = time.time()
                entity_count = len(self._entity_registry_cache or {})
                logger.info(f"✅ Loaded Entity Registry cache with {entity_count} entities")
                if entity_count == 0:
                    logger.warning("⚠️ Entity Registry cache is empty - friendly names may not be available")
            except Exception as e:
                logger.error(f"❌ Failed to load Entity Registry: {e}", exc_info=True)
                self._entity_registry_cache = {}
                self._registry_cache_loaded = True  # Mark as loaded to avoid repeated failures
                self._registry_cache_timestamp = time.time()
        
        return self._entity_registry_cache or {}
    
    async def refresh_entity_registry_cache(self):
        """
        Force refresh the Entity Registry cache.
        
        Useful when entity names are updated in Home Assistant and we need fresh data.
        """
        logger.info("🔄 Forcing Entity Registry cache refresh...")
        self._registry_cache_loaded = False
        self._registry_cache_timestamp = None
        await self._get_entity_registry(force_refresh=True)
    
    def _get_friendly_name_from_registry(self, entity_id: str, registry: Dict[str, Dict[str, Any]]) -> Optional[str]:
        """
        Get friendly name from Entity Registry (source of truth for HA UI names).
        
        Priority:
        1. Entity Registry 'name' field (what shows in HA UI)
        2. Entity Registry 'original_name' field (if name is None)
        3. None (fallback to state API)
        
        Args:
            entity_id: Entity ID to lookup
            registry: Entity registry dictionary
            
        Returns:
            Friendly name from registry, or None if not found
        """
        entity_data = registry.get(entity_id)
        if not entity_data:
            return None
        
        # Priority 1: Use 'name' field (what shows in HA UI)
        name = entity_data.get('name')
        if name:
            return name
        
        # Priority 2: Use 'original_name' if name is None
        original_name = entity_data.get('original_name')
        if original_name:
            return original_name
        
        return None
    
    async def enrich_entity_with_attributes(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch entity state with attributes from HA and create enriched JSON.
        
        Uses Entity Registry for friendly names (source of truth for HA UI names).
        Falls back to State API friendly_name if Entity Registry unavailable.
        
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
            
            # Get Entity Registry for accurate friendly names
            registry = await self._get_entity_registry()
            
            # Get friendly name with priority: Entity Registry > State API > derived
            friendly_name = self._get_friendly_name_from_registry(entity_id, registry)
            source = "Entity Registry"
            
            if not friendly_name:
                # Fallback to State API friendly_name
                friendly_name = attributes.get('friendly_name')
                source = "State API"
            
            if not friendly_name:
                # Last resort: derive from entity_id
                friendly_name = entity_id.split('.')[-1].replace('_', ' ').title()
                source = "derived"
            
            if source == "derived":
                logger.debug(f"⚠️ Entity {entity_id}: Using derived friendly_name '{friendly_name}' (not in Entity Registry or State API)")
            
            # Get additional data from registry if available
            entity_registry_data = registry.get(entity_id, {})
            device_id = entity_registry_data.get('device_id') or attributes.get('device_id')
            area_id = entity_registry_data.get('area_id') or attributes.get('area_id')
            
            # Build enriched entity
            enriched = {
                'entity_id': entity_id,
                'domain': entity_id.split('.')[0] if '.' in entity_id else 'unknown',
                'friendly_name': friendly_name,  # Now uses Entity Registry as primary source
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
                'device_id': device_id,
                'area_id': area_id
            }
            
            logger.debug(f"Enriched entity {entity_id}: friendly_name='{friendly_name}', "
                        f"is_group={enriched['is_group']}, integration={enriched['integration']}")
            
            return enriched
            
        except Exception as e:
            logger.error(f"Error enriching entity {entity_id}: {e}")
            return None
    
    async def enrich_multiple_entities(
        self, 
        entity_ids: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Batch enrich multiple entities IN PARALLEL for performance.
        
        Args:
            entity_ids: List of entity IDs to enrich
        
        Returns:
            Dictionary mapping entity_id to enriched entity data
        """
        enriched = {}
        
        # Enrich entities in parallel (major performance improvement)
        import asyncio
        
        async def enrich_one(entity_id: str) -> tuple:
            """Enrich a single entity"""
            try:
                enriched_data = await self.enrich_entity_with_attributes(entity_id)
                return (entity_id, enriched_data)
            except Exception as e:
                logger.debug(f"Error enriching {entity_id}: {e}")
                return (entity_id, None)
        
        # Execute all enrichment tasks in parallel
        if entity_ids:
            tasks = [enrich_one(entity_id) for entity_id in entity_ids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.debug(f"Entity enrichment error: {result}")
                    continue
                entity_id, enriched_data = result
                if enriched_data:
                    enriched[entity_id] = enriched_data
        
        logger.info(f"Enriched {len(enriched)} out of {len(entity_ids)} entities (parallel)")
        
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

