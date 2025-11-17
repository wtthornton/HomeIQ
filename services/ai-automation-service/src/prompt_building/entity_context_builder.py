"""
Entity Context Builder

Builds comprehensive JSON context for OpenAI prompts with complete
entity information including attributes, capabilities, and metadata.
"""

import logging
from typing import Dict, List, Any
import json
import pandas as pd

logger = logging.getLogger(__name__)


class EntityContextBuilder:
    """Builds enriched JSON context for OpenAI entity understanding."""
    
    def __init__(self):
        """Initialize the context builder."""
        pass
    
    def _extract_capabilities(self, attributes: Dict[str, Any], domain: str) -> List[str]:
        """
        Extract entity capabilities from attributes.
        
        Args:
            attributes: Entity attributes
            domain: Entity domain (light, switch, etc.)
        
        Returns:
            List of capability strings
        """
        capabilities = []
        supported_features = attributes.get('supported_features', 0)
        
        if domain == 'light':
            if supported_features & 1:  # SUPPORT_BRIGHTNESS
                capabilities.append('brightness')
            if supported_features & 2:  # SUPPORT_COLOR_TEMP
                capabilities.append('color_temp')
            if supported_features & 4:  # SUPPORT_COLOR
                capabilities.append('rgb_color')
            if supported_features & 8:  # SUPPORT_WHITE_VALUE
                capabilities.append('white_value')
            if supported_features & 16:  # SUPPORT_TRANSITION
                capabilities.append('transition')
            if supported_features & 32:  # SUPPORT_FLASH
                capabilities.append('flash')
            if supported_features & 64:  # SUPPORT_EFFECT
                capabilities.append('effect')
        
        elif domain == 'climate':
            if supported_features & 1:  # SUPPORT_TARGET_TEMPERATURE
                capabilities.append('target_temperature')
            if supported_features & 2:  # SUPPORT_TARGET_TEMPERATURE_RANGE
                capabilities.append('temperature_range')
            if supported_features & 4:  # SUPPORT_TARGET_HUMIDITY
                capabilities.append('target_humidity')
            if supported_features & 8:  # SUPPORT_FAN_MODE
                capabilities.append('fan_mode')
            if supported_features & 16:  # SUPPORT_PRESET_MODE
                capabilities.append('preset_mode')
            if supported_features & 32:  # SUPPORT_SWING_MODE
                capabilities.append('swing_mode')
            if supported_features & 64:  # SUPPORT_AUX_HEAT
                capabilities.append('aux_heat')
        
        elif domain in ['cover', 'blind', 'shutter']:
            if supported_features & 1:  # SUPPORT_OPEN
                capabilities.append('open')
            if supported_features & 2:  # SUPPORT_CLOSE
                capabilities.append('close')
            if supported_features & 4:  # SUPPORT_SET_POSITION
                capabilities.append('set_position')
            if supported_features & 8:  # SUPPORT_STOP
                capabilities.append('stop')
            if supported_features & 16:  # SUPPORT_OPEN_TILT
                capabilities.append('open_tilt')
            if supported_features & 32:  # SUPPORT_CLOSE_TILT
                capabilities.append('close_tilt')
            if supported_features & 64:  # SUPPORT_SET_TILT_POSITION
                capabilities.append('set_tilt_position')
        
        # Add generic capabilities based on attributes
        if attributes.get('brightness') is not None:
            capabilities.append('brightness')
        if attributes.get('color_temp') is not None:
            capabilities.append('color_temp')
        if attributes.get('rgb_color') is not None:
            capabilities.append('rgb_color')
        if attributes.get('temperature') is not None:
            capabilities.append('temperature')
        if attributes.get('humidity') is not None:
            capabilities.append('humidity')
        
        return list(set(capabilities))  # Remove duplicates
    
    def _generate_human_readable_description(self, entity: Dict[str, Any]) -> str:
        """
        Generate human-readable description for entity.
        
        Args:
            entity: Entity data
        
        Returns:
            Human-readable description
        """
        friendly_name = entity.get('friendly_name', entity.get('entity_id', 'Unknown'))
        entity_type = entity.get('type', 'entity')
        is_group = entity.get('is_hue_group', False)
        
        if is_group:
            return f"controls all {friendly_name.lower()} lights/devices as a group"
        elif entity_type == 'scene':
            return f"activates the {friendly_name.lower()} scene"
        elif entity_type == 'individual':
            return f"controls individual device: {friendly_name}"
        
        return friendly_name
    
    async def build_entity_context_json(
        self,
        entities: List[Dict[str, Any]],
        enriched_data: Dict[str, Dict[str, Any]],
        db_session = None
    ) -> str:
        """
        Create JSON string with complete entity information for OpenAI.
        
        Args:
            entities: List of base entity dictionaries (from entity_validator)
            enriched_data: Dictionary mapping entity_id to enriched data
            db_session: Optional database session for database-first lookup
        
        Returns:
            JSON string with complete entity context
        """
        enriched_entities = []
        
        for entity in entities:
            entity_id = entity.get('entity_id')
            if not entity_id:
                continue
            
            enriched = enriched_data.get(entity_id, {})
            
            # Extract domain
            domain = entity_id.split('.')[0] if '.' in entity_id else 'unknown'
            
            # Database-first lookup for entity information
            friendly_name = None
            name = None
            name_by_user = None
            original_name = None
            capabilities = []
            available_services = []
            supported_features = None
            icon = None
            device_class = None
            unit_of_measurement = None
            device_metadata = {}
            
            # Database-first lookup using DataAPIClient
            try:
                from ...clients.data_api_client import DataAPIClient
                data_api_client = DataAPIClient()
                
                # Fetch entity metadata from data-api
                entity_metadata = await data_api_client.get_entity_metadata(entity_id)
                
                if entity_metadata:
                    # Use database fields first
                    friendly_name = entity_metadata.get('friendly_name') or entity_metadata.get('name') or entity_metadata.get('original_name')
                    name = entity_metadata.get('name')
                    name_by_user = entity_metadata.get('name_by_user')
                    original_name = entity_metadata.get('original_name')
                    capabilities = entity_metadata.get('capabilities', [])
                    if not isinstance(capabilities, list):
                        capabilities = []
                    available_services = entity_metadata.get('available_services', [])
                    if not isinstance(available_services, list):
                        available_services = []
                    supported_features = entity_metadata.get('supported_features')
                    icon = entity_metadata.get('icon')
                    device_class = entity_metadata.get('device_class')
                    unit_of_measurement = entity_metadata.get('unit_of_measurement')
                    
                    # Get device metadata if available
                    device_id = entity_metadata.get('device_id')
                    if device_id:
                        try:
                            devices_result = await data_api_client.fetch_devices(limit=1000)
                            if isinstance(devices_result, pd.DataFrame) and not devices_result.empty:
                                device_row = devices_result[devices_result['device_id'] == device_id]
                                if not device_row.empty:
                                    device = device_row.iloc[0]
                                    device_metadata = {
                                        'manufacturer': device.get('manufacturer', 'Unknown'),
                                        'model': device.get('model', 'Unknown'),
                                        'sw_version': device.get('sw_version', 'Unknown')
                                    }
                            elif isinstance(devices_result, list):
                                device = next((d for d in devices_result if d.get('device_id') == device_id), None)
                                if device:
                                    device_metadata = {
                                        'manufacturer': device.get('manufacturer', 'Unknown'),
                                        'model': device.get('model', 'Unknown'),
                                        'sw_version': device.get('sw_version', 'Unknown')
                                    }
                        except Exception as e:
                            logger.debug(f"Device lookup failed for {device_id}: {e}")
            except Exception as e:
                logger.debug(f"Data API lookup failed for {entity_id}: {e}, using enriched data")
            
            # Fallback to enriched data if database lookup failed or not available
            if not friendly_name:
                friendly_name = enriched.get('friendly_name') or entity.get('friendly_name')
            if not capabilities:
                attributes = enriched.get('attributes', {})
                capabilities = self._extract_capabilities(attributes, domain)
            if not available_services:
                available_services = enriched.get('available_services', [])
            if not supported_features:
                attributes = enriched.get('attributes', {})
                supported_features = attributes.get('supported_features')
            if not icon:
                icon = enriched.get('icon')
            if not device_class:
                attributes = enriched.get('attributes', {})
                device_class = attributes.get('device_class')
            if not unit_of_measurement:
                attributes = enriched.get('attributes', {})
                unit_of_measurement = attributes.get('unit_of_measurement')
            
            # Get attributes from enriched data (for full passthrough)
            attributes = enriched.get('attributes', {})
            
            # Build entity entry
            entity_entry = {
                'entity_id': entity_id,
                'friendly_name': friendly_name,
                'name': name,  # NEW: Entity Registry name
                'name_by_user': name_by_user,  # NEW: User-customized name
                'original_name': original_name,  # NEW: Original name
                'domain': domain,
                'type': self._determine_type(enriched),
                'state': enriched.get('state', 'unknown'),
                'description': self._generate_human_readable_description({
                    'friendly_name': friendly_name,
                    'type': self._determine_type(enriched),
                    'is_hue_group': enriched.get('is_group', False)
                }),
                'capabilities': capabilities,  # From database first
                'supported_features': supported_features,  # NEW
                'available_services': available_services,  # NEW
                'icon': icon,  # NEW
                'device_class': device_class,  # NEW
                'unit_of_measurement': unit_of_measurement,  # NEW
                'attributes': attributes,  # Full passthrough of all attributes
                'is_group': enriched.get('is_group', False),
                'integration': enriched.get('integration', 'unknown')
            }
            
            # Add device metadata if available
            if device_metadata:
                entity_entry['device'] = device_metadata
            
            # Add specific attributes that might be useful
            if 'brightness' in attributes:
                entity_entry['brightness'] = attributes['brightness']
            if 'color_temp' in attributes:
                entity_entry['color_temp'] = attributes['color_temp']
            if 'rgb_color' in attributes:
                entity_entry['rgb_color'] = attributes['rgb_color']
            if 'temperature' in attributes:
                entity_entry['temperature'] = attributes['temperature']
            if 'humidity' in attributes:
                entity_entry['humidity'] = attributes['humidity']
            
            # ✅ ADD EFFECT SUPPORT: Extract effect and effect_list for lights with effects (WLED, Hue, etc.)
            if 'effect' in attributes:
                entity_entry['current_effect'] = attributes['effect']
            if 'effect_list' in attributes:
                entity_entry['available_effects'] = attributes['effect_list']
                logger.debug(f"📋 Entity {entity_id} has {len(attributes['effect_list'])} available effects")
            
            # Add supported_color_modes for better color control understanding
            if 'supported_color_modes' in attributes:
                entity_entry['supported_color_modes'] = attributes['supported_color_modes']
            
            enriched_entities.append(entity_entry)
        
        # Build final context JSON
        context = {
            'entities': enriched_entities,
            'summary': {
                'total_entities': len(enriched_entities),
                'group_entities': sum(1 for e in enriched_entities if e.get('is_group')),
                'individual_entities': sum(1 for e in enriched_entities if not e.get('is_group'))
            }
        }
        
        # Convert to formatted JSON string
        json_str = json.dumps(context, indent=2)
        
        logger.debug(f"Built entity context JSON with {len(enriched_entities)} entities")
        
        return json_str
    
    def _determine_type(self, enriched: Dict[str, Any]) -> str:
        """
        Determine entity type from enriched data.
        
        Args:
            enriched: Enriched entity data
        
        Returns:
            Entity type string
        """
        if enriched.get('is_group'):
            return 'group'
        
        entity_id = enriched.get('entity_id', '')
        if entity_id.startswith('scene.'):
            return 'scene'
        
        return 'individual'

