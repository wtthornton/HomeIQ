"""
Automation Validation Service

Validates external data patterns against Home Assistant automations.
Only external data entities used in automations are considered valid.

Based on recommendations from EXTERNAL_DATA_AUTOMATION_VALIDATION_RECOMMENDATIONS.md
"""

import json
import logging
from typing import Any, Set

from ..pattern_analyzer.filters import EventFilter

logger = logging.getLogger(__name__)


class AutomationValidator:
    """
    Validates external data patterns against Home Assistant automations.
    
    External data patterns should only be valid if the entity is used in an automation.
    """
    
    def __init__(self, ha_client: Any | None = None):
        """
        Initialize automation validator.
        
        Args:
            ha_client: Optional Home Assistant client for fetching automations
        """
        self.ha_client = ha_client
        self._external_entities_in_automations: Set[str] = set()
        self._automations_cache: list[dict[str, Any]] | None = None
        logger.info("AutomationValidator initialized")
    
    async def load_automation_entities(self) -> Set[str]:
        """
        Load external data entities from Home Assistant automations.
        
        Returns:
            Set of external entity IDs that are used in automations
        """
        if not self.ha_client:
            logger.debug("No HA client available, returning empty set")
            return set()
        
        if self._external_entities_in_automations:
            logger.debug("Using cached external entities from automations")
            return self._external_entities_in_automations
        
        logger.info("Loading external entities from Home Assistant automations...")
        
        try:
            # Get automations from HA client
            automations = await self.ha_client.get_automations()
            self._automations_cache = automations
            
            if not automations:
                logger.info("No automations found")
                return set()
            
            # Extract external entities from automations
            external_entities = set()
            for automation in automations:
                entities = self._extract_entities_from_automation(automation)
                for entity_id in entities:
                    if EventFilter.is_external_data_entity(entity_id):
                        external_entities.add(entity_id)
            
            self._external_entities_in_automations = external_entities
            logger.info(
                f"Found {len(external_entities)} external entities used in "
                f"{len(automations)} automations"
            )
            
            return external_entities
            
        except Exception as e:
            logger.error(f"Failed to load automation entities: {e}", exc_info=True)
            return set()
    
    def is_external_data_valid(self, entity_id: str) -> bool:
        """
        Check if external data entity is valid (used in automation).
        
        Args:
            entity_id: Entity ID to check
            
        Returns:
            True if entity is not external data, or if it's external data and used in automation
            False if external data and not used in automation
        """
        # If not external data, always valid
        if not EventFilter.is_external_data_entity(entity_id):
            return True
        
        # If external data, check if it's in automations
        return entity_id in self._external_entities_in_automations
    
    def validate_pattern(self, pattern: dict[str, Any]) -> dict[str, Any]:
        """
        Validate a pattern and add validation flags.
        
        Args:
            pattern: Pattern dictionary
            
        Returns:
            Pattern dictionary with validation flags added
        """
        # Extract entities from pattern
        pattern_entities = self._extract_pattern_entities(pattern)
        
        # Check if any external entity in pattern is used in automation
        validated_by_automation = False
        automation_ids = []
        
        for entity_id in pattern_entities:
            if EventFilter.is_external_data_entity(entity_id):
                if entity_id in self._external_entities_in_automations:
                    validated_by_automation = True
                    # Find which automations use this entity
                    if self._automations_cache:
                        for automation in self._automations_cache:
                            auto_entities = self._extract_entities_from_automation(automation)
                            if entity_id in auto_entities:
                                auto_id = automation.get('id') or automation.get('alias', '')
                                if auto_id and auto_id not in automation_ids:
                                    automation_ids.append(auto_id)
                else:
                    # External data not in automation - pattern is invalid
                    validated_by_automation = False
                    break
        
        # Add validation flags to pattern
        pattern['validated_by_automation'] = validated_by_automation
        pattern['automation_ids'] = json.dumps(automation_ids) if automation_ids else None
        
        return pattern
    
    def _extract_entities_from_automation(self, automation: dict[str, Any]) -> Set[str]:
        """
        Extract all entity IDs from an automation.
        
        Args:
            automation: Automation dictionary from Home Assistant
            
        Returns:
            Set of entity IDs found in automation
        """
        entities = set()
        self._traverse_and_extract(automation, entities)
        return entities
    
    def _traverse_and_extract(self, data: Any, entities: Set[str]) -> None:
        """
        Recursively traverse automation structure and extract entity IDs.
        
        Args:
            data: Data structure to traverse (dict, list, or value)
            entities: Set to add entity IDs to
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'entity_id':
                    if isinstance(value, str):
                        entities.add(value)
                    elif isinstance(value, list):
                        entities.update(value)
                elif key == 'target' and isinstance(value, dict) and 'entity_id' in value:
                    target_entity_id = value['entity_id']
                    if isinstance(target_entity_id, str):
                        entities.add(target_entity_id)
                    elif isinstance(target_entity_id, list):
                        entities.update(target_entity_id)
                else:
                    self._traverse_and_extract(value, entities)
        elif isinstance(data, list):
            for item in data:
                self._traverse_and_extract(item, entities)
    
    def _extract_pattern_entities(self, pattern: dict[str, Any]) -> Set[str]:
        """
        Extract entity IDs from a pattern dictionary.
        
        Args:
            pattern: Pattern dictionary
            
        Returns:
            Set of entity IDs in the pattern
        """
        entities = set()
        
        # Check for device_id field
        if 'device_id' in pattern:
            device_id = pattern['device_id']
            if device_id:
                # Handle co-occurrence patterns with '+' separator
                entities.update(device_id.split('+'))
        
        # Check for entities field
        if 'entities' in pattern:
            entities_list = pattern['entities']
            if isinstance(entities_list, list):
                entities.update(entities_list)
            elif isinstance(entities_list, str):
                try:
                    parsed = json.loads(entities_list)
                    if isinstance(parsed, list):
                        entities.update(parsed)
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Check for device1/device2 fields (co-occurrence patterns)
        if 'device1' in pattern:
            entities.add(pattern['device1'])
        if 'device2' in pattern:
            entities.add(pattern['device2'])
        
        return entities
