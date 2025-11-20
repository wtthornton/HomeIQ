"""
Relationship Analyzer - Home Assistant Automation Checker

Checks if device pairs already have automations connecting them to avoid
suggesting duplicate automations.

Epic AI-3: Cross-Device Synergy & Contextual Opportunities
Story AI3.3: Unconnected Relationship Analysis
"""

import logging

logger = logging.getLogger(__name__)


class HomeAssistantAutomationChecker:
    """
    Checks Home Assistant for existing automations to avoid duplicates.
    
    Queries HA API for automation configurations and parses them to identify
    entity relationships. Used to filter out synergies that already have automations.
    
    Story AI3.3: Unconnected Relationship Analysis
    """

    def __init__(self, ha_client):
        """
        Initialize automation checker.
        
        Args:
            ha_client: Home Assistant API client
        """
        self.ha_client = ha_client
        self._automation_cache = None
        self._relationship_cache = None

        logger.info("HomeAssistantAutomationChecker initialized")

    async def get_existing_automations(self) -> list[dict]:
        """
        Fetch all automations from Home Assistant.
        
        Returns:
            List of automation configurations
        """
        if self._automation_cache is not None:
            logger.debug("Using cached automation list")
            return self._automation_cache

        try:
            # Query HA API for automations
            automations = await self.ha_client.get_automations()

            self._automation_cache = automations
            logger.info(f"✅ Fetched {len(automations)} automations from Home Assistant")

            return automations

        except Exception as e:
            logger.warning(f"Failed to fetch automations from HA: {e}")
            return []

    async def get_connected_entity_pairs(self) -> set[tuple[str, str]]:
        """
        Extract connected entity pairs from existing automations.
        
        Returns:
            Set of (trigger_entity, action_entity) tuples
        """
        if self._relationship_cache is not None:
            return self._relationship_cache

        automations = await self.get_existing_automations()

        if not automations:
            logger.debug("No automations found, all pairs are new")
            self._relationship_cache = set()
            return set()

        connected_pairs = set()

        for automation in automations:
            try:
                # Parse automation to extract entity relationships
                pairs = self._parse_automation_relationships(automation)
                connected_pairs.update(pairs)

            except Exception as e:
                logger.debug(f"Failed to parse automation: {e}")
                continue

        self._relationship_cache = connected_pairs
        logger.info(f"✅ Found {len(connected_pairs)} connected entity pairs")

        return connected_pairs

    def _parse_automation_relationships(self, automation: dict) -> list[tuple[str, str]]:
        """
        Parse automation to extract trigger→action entity relationships.
        
        Args:
            automation: Automation configuration dict
        
        Returns:
            List of (trigger_entity, action_entity) tuples
        """
        relationships = []

        try:
            # Extract trigger entities
            triggers = automation.get('trigger', [])
            if not isinstance(triggers, list):
                triggers = [triggers]

            trigger_entities = []
            for trigger in triggers:
                if isinstance(trigger, dict):
                    # State trigger
                    if 'entity_id' in trigger:
                        trigger_entities.append(trigger['entity_id'])
                    # Numeric state trigger
                    elif 'entity' in trigger:
                        trigger_entities.append(trigger['entity'])

            # Extract action entities
            actions = automation.get('action', [])
            if not isinstance(actions, list):
                actions = [actions]

            action_entities = []
            for action in actions:
                if isinstance(action, dict):
                    # Service call with target
                    if 'target' in action and 'entity_id' in action['target']:
                        entity_id = action['target']['entity_id']
                        if isinstance(entity_id, list):
                            action_entities.extend(entity_id)
                        else:
                            action_entities.append(entity_id)
                    # Direct entity_id in action
                    elif 'entity_id' in action:
                        entity_id = action['entity_id']
                        if isinstance(entity_id, list):
                            action_entities.extend(entity_id)
                        else:
                            action_entities.append(entity_id)

            # Create pairs
            for trigger_entity in trigger_entities:
                for action_entity in action_entities:
                    if trigger_entity != action_entity:  # Don't self-connect
                        relationships.append((trigger_entity, action_entity))

        except Exception as e:
            logger.debug(f"Error parsing automation: {e}")

        return relationships

    async def is_connected(self, trigger_entity: str, action_entity: str) -> bool:
        """
        Check if two entities have an existing automation connecting them.
        
        Args:
            trigger_entity: Trigger entity ID
            action_entity: Action entity ID
        
        Returns:
            True if automation exists, False otherwise
        """
        connected_pairs = await self.get_connected_entity_pairs()

        # Check both directions (trigger→action and action→trigger)
        return (
            (trigger_entity, action_entity) in connected_pairs or
            (action_entity, trigger_entity) in connected_pairs
        )

    def clear_cache(self):
        """Clear cached automation data."""
        self._automation_cache = None
        self._relationship_cache = None
        logger.debug("Automation checker cache cleared")

