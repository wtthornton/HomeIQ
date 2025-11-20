"""
Enhanced Entity Extraction with Device Intelligence Integration

Combines pattern matching with rich device intelligence data for better context.
"""

import logging
from typing import Any

from ..clients.device_intelligence_client import DeviceIntelligenceClient
from .pattern_extractor import extract_entities_from_query

logger = logging.getLogger(__name__)

class EnhancedEntityExtractor:
    """Enhanced entity extractor with device intelligence integration"""

    def __init__(self, device_intelligence_client: DeviceIntelligenceClient):
        self.device_intel_client = device_intelligence_client

    async def extract_entities_with_intelligence(self, query: str) -> list[dict[str, Any]]:
        """
        Extract entities using both pattern matching and device intelligence.
        
        Flow:
        1. Basic pattern extraction (safe, no side effects)
        2. Area-based device discovery from device intelligence
        3. Capability enhancement for each device
        4. Health score filtering
        
        Args:
            query: Natural language query string
            
        Returns:
            List of enhanced entities with rich device data
        """
        logger.info(f"🔍 Enhanced entity extraction for: {query}")

        # Step 1: Basic pattern extraction (safe)
        basic_entities = extract_entities_from_query(query)
        logger.debug(f"Basic entities extracted: {len(basic_entities)}")

        # Step 2: Enhance with device intelligence
        enhanced_entities = []

        for entity in basic_entities:
            if self._is_area_entity(entity):
                # Get all devices in this area
                area_devices = await self.device_intel_client.get_devices_by_area(entity['name'])
                logger.info(f"Found {len(area_devices)} devices in {entity['name']}")

                for device in area_devices:
                    enhanced_entity = await self._enhance_device_entity(device, entity)
                    if enhanced_entity:
                        enhanced_entities.append(enhanced_entity)
            else:
                # Keep basic entity for non-area references
                enhanced_entities.append(entity)

        logger.info(f"✅ Enhanced entity extraction complete: {len(enhanced_entities)} entities")
        return enhanced_entities

    def _is_area_entity(self, entity: dict[str, Any]) -> bool:
        """Check if entity represents an area/room"""
        area_names = ['office', 'living room', 'bedroom', 'kitchen', 'garage', 'front', 'back']
        return entity['name'].lower() in area_names

    async def _enhance_device_entity(self, device: dict[str, Any], area_entity: dict[str, Any]) -> dict[str, Any] | None:
        """Enhance device with rich intelligence data"""
        try:
            # Get device details with capabilities
            device_details = await self.device_intel_client.get_device_details(device['id'])
            if not device_details:
                logger.debug(f"No device details found for {device['name']}")
                return None

            # Filter by health score (avoid unhealthy devices)
            health_score = device_details.get('health_score', 100)
            if health_score < 50:  # Skip devices with poor health
                logger.debug(f"Skipping device {device['name']} due to low health score: {health_score}")
                return None

            # Build enhanced entity
            enhanced_entity = {
                'name': device_details['name'],
                'entity_id': device_details['entities'][0]['entity_id'] if device_details['entities'] else None,
                'domain': device_details['entities'][0]['domain'] if device_details['entities'] else 'unknown',
                'area': device_details['area_name'],
                'manufacturer': device_details['manufacturer'],
                'model': device_details['model'],
                'integration': device_details.get('integration', 'Unknown'),
                'capabilities': device_details.get('capabilities', []),
                'health_score': health_score,
                'state': device_details['entities'][0]['state'] if device_details['entities'] else 'unknown',
                'attributes': device_details['entities'][0].get('attributes', {}) if device_details['entities'] else {},
                'last_seen': device_details.get('last_seen'),
                'extraction_method': 'device_intelligence'
            }

            logger.debug(f"Enhanced entity: {enhanced_entity['name']} with {len(enhanced_entity['capabilities'])} capabilities")
            return enhanced_entity

        except Exception as e:
            logger.error(f"Error enhancing device entity {device['name']}: {e}")
            return None

    async def get_area_devices_summary(self, area_name: str) -> dict[str, Any]:
        """Get summary of all devices in an area"""
        try:
            devices = await self.device_intel_client.get_devices_by_area(area_name)

            summary = {
                'area_name': area_name,
                'total_devices': len(devices),
                'device_types': {},
                'capabilities_available': set(),
                'health_scores': []
            }

            for device in devices:
                device_details = await self.device_intel_client.get_device_details(device['id'])
                if device_details:
                    # Count device types
                    integration = device_details.get('integration', 'unknown')
                    summary['device_types'][integration] = summary['device_types'].get(integration, 0) + 1

                    # Collect capabilities
                    capabilities = device_details.get('capabilities', [])
                    for cap in capabilities:
                        if cap.get('supported'):
                            summary['capabilities_available'].add(cap['feature'])

                    # Collect health scores
                    health_score = device_details.get('health_score', 100)
                    summary['health_scores'].append(health_score)

            # Convert set to list for JSON serialization
            summary['capabilities_available'] = list(summary['capabilities_available'])

            return summary

        except Exception as e:
            logger.error(f"Error getting area devices summary for {area_name}: {e}")
            return {
                'area_name': area_name,
                'total_devices': 0,
                'device_types': {},
                'capabilities_available': [],
                'health_scores': []
            }
