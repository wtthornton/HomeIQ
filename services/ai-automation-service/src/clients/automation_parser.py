"""
Automation Configuration Parser

Story AI4.2: Automation Parser
Parses Home Assistant automation configurations to extract device relationships
"""

import logging
from typing import Dict, List, Set, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class EntityRelationship:
    """
    Represents a relationship between entities in an automation.
    
    Story AI4.2 AC3: Stores relationship metadata for efficient querying.
    """
    automation_id: str
    automation_alias: str
    trigger_entities: Set[str]
    action_entities: Set[str]
    automation_type: str  # trigger, state, time, event, etc.
    conditions: Optional[List[Dict]] = None
    description: Optional[str] = None
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_entity_pairs(self) -> List[Tuple[str, str]]:
        """
        Get all trigger → action entity pairs in this automation.
        
        Returns:
            List of (trigger_entity, action_entity) tuples
        """
        pairs = []
        for trigger_entity in self.trigger_entities:
            for action_entity in self.action_entities:
                pairs.append((trigger_entity, action_entity))
        return pairs
    
    def involves_entities(self, entity1: str, entity2: str) -> bool:
        """
        Check if this automation involves both entities (bidirectional).
        
        Args:
            entity1: First entity ID
            entity2: Second entity ID
        
        Returns:
            True if automation connects these entities in any direction
        """
        entities = self.trigger_entities | self.action_entities
        return entity1 in entities and entity2 in entities


class AutomationParser:
    """
    Parses Home Assistant automation configurations and extracts device relationships.
    
    Story AI4.2: Implements configuration parsing, relationship extraction, and efficient lookup.
    """
    
    def __init__(self):
        """Initialize automation parser."""
        self._relationships: Dict[str, EntityRelationship] = {}
        self._entity_pair_index: Dict[Tuple[str, str], Set[str]] = {}
        self._last_parse_time: Optional[datetime] = None
    
    def parse_automations(self, automations: List[Dict]) -> int:
        """
        Parse automation configurations and extract relationships.
        
        Story AI4.2 AC1, AC2: Parse automation data and extract entity relationships.
        
        Args:
            automations: List of automation configuration dictionaries from HA
        
        Returns:
            Number of relationships extracted
        """
        # Handle None or empty input
        if not automations:
            logger.warning("⚠️ No automations provided to parse")
            return 0
        
        logger.info(f"🔍 Parsing {len(automations)} automations...")
        
        self._relationships.clear()
        self._entity_pair_index.clear()
        
        for automation in automations:
            try:
                relationship = self._parse_automation(automation)
                if relationship:
                    self._relationships[relationship.automation_id] = relationship
                    self._index_relationship(relationship)
            except Exception as e:
                automation_id = automation.get('id', automation.get('alias', 'unknown'))
                logger.warning(f"⚠️ Failed to parse automation {automation_id}: {e}")
                continue
        
        self._last_parse_time = datetime.now(timezone.utc)
        
        logger.info(
            f"✅ Parsed {len(self._relationships)} automations, "
            f"indexed {len(self._entity_pair_index)} entity pairs"
        )
        
        return len(self._relationships)
    
    def _parse_automation(self, automation: Dict) -> Optional[EntityRelationship]:
        """
        Parse a single automation configuration.
        
        Story AI4.2 AC2: Extract trigger and action entities from automation config.
        
        Args:
            automation: Automation configuration dictionary
        
        Returns:
            EntityRelationship object or None if parsing fails
        """
        automation_id = automation.get('id', automation.get('alias', 'unknown'))
        automation_alias = automation.get('alias', automation_id)
        
        # Extract trigger entities
        trigger_entities = self._extract_trigger_entities(automation)
        
        # Extract action entities
        action_entities = self._extract_action_entities(automation)
        
        # Skip if no meaningful relationships found
        if not trigger_entities and not action_entities:
            logger.debug(f"⏭️  Skipping automation {automation_id}: no entities found")
            return None
        
        # Determine automation type
        automation_type = self._determine_automation_type(automation)
        
        # Extract conditions if present
        conditions = automation.get('condition', automation.get('conditions'))
        
        # Get description
        description = automation.get('description', '')
        
        relationship = EntityRelationship(
            automation_id=automation_id,
            automation_alias=automation_alias,
            trigger_entities=trigger_entities,
            action_entities=action_entities,
            automation_type=automation_type,
            conditions=conditions if isinstance(conditions, list) else ([conditions] if conditions else None),
            description=description
        )
        
        logger.debug(
            f"📋 Parsed {automation_id}: "
            f"{len(trigger_entities)} triggers → {len(action_entities)} actions"
        )
        
        return relationship
    
    def _extract_trigger_entities(self, automation: Dict) -> Set[str]:
        """
        Extract entity IDs from automation triggers.
        
        Story AI4.2 AC2: Parse trigger conditions and extract entity IDs.
        
        Args:
            automation: Automation configuration
        
        Returns:
            Set of entity IDs found in triggers
        """
        entities = set()
        
        # Get triggers (can be 'trigger' or 'triggers')
        triggers = automation.get('trigger', automation.get('triggers', []))
        if not isinstance(triggers, list):
            triggers = [triggers]
        
        for trigger in triggers:
            if not isinstance(trigger, dict):
                continue
            
            # State triggers
            if trigger.get('platform') == 'state':
                entity_id = trigger.get('entity_id')
                if entity_id:
                    if isinstance(entity_id, list):
                        entities.update(entity_id)
                    else:
                        entities.add(entity_id)
            
            # Numeric state triggers
            elif trigger.get('platform') == 'numeric_state':
                entity_id = trigger.get('entity_id')
                if entity_id:
                    if isinstance(entity_id, list):
                        entities.update(entity_id)
                    else:
                        entities.add(entity_id)
            
            # Zone triggers
            elif trigger.get('platform') == 'zone':
                entity_id = trigger.get('entity_id')
                if entity_id:
                    if isinstance(entity_id, list):
                        entities.update(entity_id)
                    else:
                        entities.add(entity_id)
            
            # Template triggers (may reference entities)
            elif trigger.get('platform') == 'template':
                # Template triggers are complex - could parse template for entities
                # For now, skip template entity extraction
                pass
        
        return entities
    
    def _extract_action_entities(self, automation: Dict) -> Set[str]:
        """
        Extract entity IDs from automation actions.
        
        Story AI4.2 AC2: Parse action entities and service calls.
        
        Args:
            automation: Automation configuration
        
        Returns:
            Set of entity IDs found in actions
        """
        entities = set()
        
        # Get actions (can be 'action' or 'actions')
        actions = automation.get('action', automation.get('actions', []))
        if not isinstance(actions, list):
            actions = [actions]
        
        for action in actions:
            if not isinstance(action, dict):
                continue
            
            # Service calls
            if 'service' in action:
                # Check for entity_id in action
                entity_id = action.get('entity_id')
                if entity_id:
                    if isinstance(entity_id, list):
                        entities.update(entity_id)
                    else:
                        entities.add(entity_id)
                
                # Check for target with entity_id
                target = action.get('target', {})
                if isinstance(target, dict):
                    target_entity_id = target.get('entity_id')
                    if target_entity_id:
                        if isinstance(target_entity_id, list):
                            entities.update(target_entity_id)
                        else:
                            entities.add(target_entity_id)
                
                # Check for data with entity_id
                data = action.get('data', {})
                if isinstance(data, dict):
                    data_entity_id = data.get('entity_id')
                    if data_entity_id:
                        if isinstance(data_entity_id, list):
                            entities.update(data_entity_id)
                        else:
                            entities.add(data_entity_id)
            
            # Device actions
            elif 'device_id' in action:
                # Device actions don't use entity_id directly
                # Skip for now as we focus on entity relationships
                pass
        
        return entities
    
    def _determine_automation_type(self, automation: Dict) -> str:
        """
        Determine the type of automation based on its triggers.
        
        Args:
            automation: Automation configuration
        
        Returns:
            Automation type string
        """
        triggers = automation.get('trigger', automation.get('triggers', []))
        if not isinstance(triggers, list):
            triggers = [triggers]
        
        if not triggers:
            return 'unknown'
        
        # Get platform of first trigger (most significant)
        first_trigger = triggers[0] if triggers else {}
        platform = first_trigger.get('platform', 'unknown')
        
        # Map platform to automation type
        type_mapping = {
            'state': 'state_based',
            'numeric_state': 'state_based',
            'time': 'time_based',
            'time_pattern': 'time_based',
            'sun': 'time_based',
            'event': 'event_based',
            'webhook': 'event_based',
            'mqtt': 'event_based',
            'zone': 'location_based',
            'template': 'template_based'
        }
        
        return type_mapping.get(platform, 'trigger_based')
    
    def _index_relationship(self, relationship: EntityRelationship) -> None:
        """
        Index relationship for efficient entity pair lookup.
        
        Story AI4.2 AC4: Build efficient lookup structures.
        
        Args:
            relationship: Relationship to index
        """
        # Index all entity pairs
        for trigger_entity in relationship.trigger_entities:
            for action_entity in relationship.action_entities:
                # Index trigger → action
                pair = (trigger_entity, action_entity)
                if pair not in self._entity_pair_index:
                    self._entity_pair_index[pair] = set()
                self._entity_pair_index[pair].add(relationship.automation_id)
                
                # Also index reverse (action → trigger) for bidirectional lookup
                reverse_pair = (action_entity, trigger_entity)
                if reverse_pair not in self._entity_pair_index:
                    self._entity_pair_index[reverse_pair] = set()
                self._entity_pair_index[reverse_pair].add(relationship.automation_id)
    
    def has_relationship(self, entity1: str, entity2: str) -> bool:
        """
        Check if two entities have a relationship in any automation.
        
        Story AI4.2 AC4: Fast entity pair lookup for synergy detection.
        
        Args:
            entity1: First entity ID
            entity2: Second entity ID
        
        Returns:
            True if entities are connected by any automation
        """
        # Check both directions
        return (
            (entity1, entity2) in self._entity_pair_index or
            (entity2, entity1) in self._entity_pair_index
        )
    
    def get_relationships_for_pair(
        self, 
        entity1: str, 
        entity2: str
    ) -> List[EntityRelationship]:
        """
        Get all automations that connect two entities.
        
        Story AI4.2 AC3, AC4: Query relationships by entity pair.
        
        Args:
            entity1: First entity ID
            entity2: Second entity ID
        
        Returns:
            List of EntityRelationship objects connecting these entities
        """
        automation_ids = set()
        
        # Check both directions
        pair1 = (entity1, entity2)
        pair2 = (entity2, entity1)
        
        if pair1 in self._entity_pair_index:
            automation_ids.update(self._entity_pair_index[pair1])
        
        if pair2 in self._entity_pair_index:
            automation_ids.update(self._entity_pair_index[pair2])
        
        return [
            self._relationships[auto_id] 
            for auto_id in automation_ids 
            if auto_id in self._relationships
        ]
    
    def get_all_relationships(self) -> List[EntityRelationship]:
        """
        Get all parsed relationships.
        
        Returns:
            List of all EntityRelationship objects
        """
        return list(self._relationships.values())
    
    def get_entity_pair_count(self) -> int:
        """
        Get number of unique entity pairs indexed.
        
        Returns:
            Number of entity pairs
        """
        return len(self._entity_pair_index)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get parser statistics.
        
        Returns:
            Dictionary with parser stats
        """
        automation_types = {}
        for rel in self._relationships.values():
            automation_types[rel.automation_type] = automation_types.get(rel.automation_type, 0) + 1
        
        return {
            'total_automations': len(self._relationships),
            'entity_pairs_indexed': len(self._entity_pair_index),
            'automation_types': automation_types,
            'last_parse_time': self._last_parse_time.isoformat() if self._last_parse_time else None
        }

