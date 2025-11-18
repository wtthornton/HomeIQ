"""
Unified Entity Enricher

Consolidates entity enrichment from multiple sources:
- ComprehensiveEntityEnrichment (primary)
- EntityAttributeService
- EntityCapabilityEnrichment
- Device Intelligence

Created: Phase 2 - Core Service Refactoring
"""

import logging
from typing import Dict, List, Optional, Any, Set
from ...services.comprehensive_entity_enrichment import enrich_entities_comprehensively
from ...clients.ha_client import HomeAssistantClient
from ...clients.device_intelligence_client import DeviceIntelligenceClient
from ...clients.data_api_client import DataAPIClient

logger = logging.getLogger(__name__)


class EntityEnricher:
    """
    Unified entity enricher that consolidates all enrichment methods.
    
    Enriches entities with comprehensive data from all available sources:
    - Device Intelligence (capabilities, health, manufacturer, model)
    - Entity Attributes (friendly_name, state, attributes)
    - Historical patterns (usage data)
    - Enrichment context (weather, carbon, energy, air quality)
    """
    
    def __init__(
        self,
        ha_client: Optional[HomeAssistantClient] = None,
        device_intelligence_client: Optional[DeviceIntelligenceClient] = None,
        data_api_client: Optional[DataAPIClient] = None
    ):
        """
        Initialize unified entity enricher.
        
        Args:
            ha_client: Home Assistant client
            device_intelligence_client: Device Intelligence client
            data_api_client: Data API client
        """
        self.ha_client = ha_client
        self.device_intelligence_client = device_intelligence_client
        self.data_api_client = data_api_client
        
        logger.info("EntityEnricher initialized")
    
    async def enrich(
        self,
        entity_ids: List[str],
        include_historical: bool = False,
        enrichment_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Enrich entities with comprehensive data.
        
        Args:
            entity_ids: List of entity IDs to enrich
            include_historical: Whether to include historical usage patterns
            enrichment_context: Optional enrichment data (weather, carbon, etc.)
        
        Returns:
            Dictionary mapping entity_id to enriched data
        """
        if not entity_ids:
            return {}
        
        try:
            # Use comprehensive enrichment function
            enriched = await enrich_entities_comprehensively(
                entity_ids=set(entity_ids),
                ha_client=self.ha_client,
                device_intelligence_client=self.device_intelligence_client,
                data_api_client=self.data_api_client,
                include_historical=include_historical,
                enrichment_context=enrichment_context
            )
            
            logger.info(f"✅ Enriched {len(enriched)}/{len(entity_ids)} entities")
            return enriched
            
        except Exception as e:
            logger.error(f"❌ Entity enrichment failed: {e}", exc_info=True)
            return {}

