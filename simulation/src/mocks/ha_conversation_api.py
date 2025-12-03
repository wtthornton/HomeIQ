"""
Mock HA Conversation API

Deterministic entity extraction responses for simulation.
Maintains same interface as production HA Conversation API.
"""

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class MockHAConversationAPI:
    """
    Mock Home Assistant Conversation API for simulation.
    
    Provides deterministic entity extraction without actual API calls.
    Maintains same interface as production HA Conversation API.
    """

    def __init__(self, ha_url: str = "http://mock-ha:8123", access_token: str = "mock-token"):
        """
        Initialize mock HA Conversation API.
        
        Args:
            ha_url: Mock HA URL (not used)
            access_token: Mock access token (not used)
        """
        self.ha_url = ha_url
        self.access_token = access_token
        
        logger.info(f"MockHAConversationAPI initialized: ha_url={ha_url}")

    async def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract entities from natural language text.
        
        Args:
            text: Natural language input
            
        Returns:
            List of entity dictionaries
        """
        entities = self._extract_entities(text)
        logger.debug(f"Extracted {len(entities)} entities from: {text[:50]}...")
        return entities

    async def process(self, text: str, language: str = "en") -> dict[str, Any]:
        """
        Process natural language and extract entities deterministically.
        
        Args:
            text: Natural language input
            language: Language code (not used)
            
        Returns:
            Dictionary with entities and response
        """
        # Extract entities using pattern matching
        entities = self._extract_entities(text)
        
        # Generate deterministic response
        response = {
            "response": {
                "response_type": "action_done" if entities else "query",
                "data": {
                    "success": [
                        {
                            "id": entity["entity_id"],
                            "name": entity.get("name", entity["entity_id"]),
                            "type": "entity"
                        }
                        for entity in entities
                    ]
                }
            },
            "entities": entities
        }
        
        logger.debug(f"Extracted {len(entities)} entities from: {text[:50]}...")
        return response

    def _extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract entities from text using pattern matching.
        
        Args:
            text: Natural language text
            
        Returns:
            List of entity dictionaries
        """
        entities = []
        text_lower = text.lower()
        
        # Common entity patterns
        patterns = [
            (r'(office|living room|bedroom|kitchen|garage|front|back)\s+(?:light|lights)', 'light'),
            (r'(office|living room|bedroom|kitchen|garage|front|back)\s+(?:sensor|sensors)', 'sensor'),
            (r'(office|living room|bedroom|kitchen|garage|front|back)\s+(?:switch|switches)', 'switch'),
            (r'(office|living room|bedroom|kitchen|garage|front|back)\s+(?:door|doors)', 'binary_sensor'),
            (r'(office|living room|bedroom|kitchen|garage|front|back)\s+(?:window|windows)', 'binary_sensor'),
            (r'(?:turn on|turn off|flash|dim|control)\s+(office|living room|bedroom|kitchen|garage|front|back)\s+(?:light|lights)', 'light'),
        ]
        
        for pattern, domain in patterns:
            matches = re.finditer(pattern, text_lower)
            for match in matches:
                location = match.group(1).replace(' ', '_')
                entity_id = f"{domain}.{location}"
                
                # Avoid duplicates
                if not any(e["entity_id"] == entity_id for e in entities):
                    entities.append({
                        "entity_id": entity_id,
                        "name": match.group(0),
                        "domain": domain,
                        "state": "unknown"
                    })
        
        # If no entities found, return empty list
        return entities

    async def close(self) -> None:
        """Close the mock client (no-op)."""
        logger.debug("MockHAConversationAPI closed")

