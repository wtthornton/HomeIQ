"""
Mock HA Client

Entity validation simulation for simulation.
Maintains same interface as production HomeAssistantClient.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MockHAClient:
    """
    Mock Home Assistant client for simulation.
    
    Provides entity validation simulation without actual API calls.
    Maintains same interface as production HomeAssistantClient.
    """

    def __init__(self, ha_url: str = "http://mock-ha:8123", access_token: str = "mock-token"):
        """
        Initialize mock HA client.
        
        Args:
            ha_url: Mock HA URL (not used)
            access_token: Mock access token (not used)
        """
        self.ha_url = ha_url
        self.access_token = access_token
        
        # Mock entity registry
        self._entities: dict[str, dict[str, Any]] = {}
        
        logger.info(f"MockHAClient initialized: ha_url={ha_url}")

    async def get_entity_state(self, entity_id: str) -> dict[str, Any] | None:
        """
        Get entity state from mock registry.
        
        Args:
            entity_id: Entity ID to lookup
            
        Returns:
            Entity state dictionary, or None if not found
        """
        if entity_id in self._entities:
            entity = self._entities[entity_id].copy()
            logger.debug(f"Retrieved state for {entity_id}")
            return entity
        
        logger.debug(f"Entity {entity_id} not found in mock registry")
        return None

    async def validate_automation(self, automation_yaml: str) -> dict[str, Any]:
        """
        Validate automation YAML (mock validation).
        
        Args:
            automation_yaml: Automation YAML string
            
        Returns:
            Validation result dictionary
        """
        # Basic validation: check if YAML is parseable
        import yaml
        try:
            yaml.safe_load(automation_yaml)
            valid = True
            errors = []
        except yaml.YAMLError as e:
            valid = False
            errors = [str(e)]
        
        result = {
            "valid": valid,
            "errors": errors,
            "warnings": []
        }
        
        logger.debug(f"Validated automation: valid={valid}, errors={len(errors)}")
        return result

    async def create_automation(self, automation_yaml: str, automation_id: str | None = None) -> dict[str, Any]:
        """
        Create automation in mock HA (no-op).
        
        Args:
            automation_yaml: Automation YAML string
            automation_id: Optional automation ID
            
        Returns:
            Creation result dictionary
        """
        logger.debug(f"Would create automation: {automation_id or 'new'}")
        return {
            "success": True,
            "automation_id": automation_id or "mock-automation-1",
            "message": "Automation created (mock)"
        }

    def register_entity(self, entity_id: str, state: dict[str, Any]) -> None:
        """
        Register an entity in mock registry.
        
        Args:
            entity_id: Entity ID
            state: Entity state dictionary
        """
        self._entities[entity_id] = state
        logger.debug(f"Registered entity {entity_id}")

    def clear_registry(self) -> None:
        """Clear mock entity registry."""
        self._entities.clear()
        logger.info("Cleared mock HA entity registry")

    async def close(self) -> None:
        """Close the mock client (no-op)."""
        logger.debug("MockHAClient closed")

