"""
Live Preflight Checker

Epic D4: Check entity availability before execution
"""

import logging
from typing import Any, Dict, List, Optional

from ..capability.capability_graph import CapabilityGraph
from ..clients.ha_rest_client import HARestClient

logger = logging.getLogger(__name__)


class PreflightChecker:
    """
    Performs live preflight checks before execution.
    
    Features:
    - Check entity availability/online before execution
    - Optional per-risk-class (required for high-risk)
    - Use GET /api/states/<entity_id> for preflight
    """
    
    def __init__(
        self,
        capability_graph: CapabilityGraph,
        rest_client: Optional[HARestClient] = None
    ):
        """
        Initialize preflight checker.
        
        Args:
            capability_graph: CapabilityGraph instance
            rest_client: Optional HARestClient instance
        """
        self.capability_graph = capability_graph
        self.rest_client = rest_client
    
    async def check_entity_availability(
        self,
        entity_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if entity is available/online.
        
        Args:
            entity_id: Entity ID to check
        
        Returns:
            Tuple of (is_available, error_message)
        """
        if not self.rest_client:
            # No REST client - use capability graph cache
            entity = self.capability_graph.get_entity(entity_id)
            if not entity:
                return False, f"Entity '{entity_id}' not found in capability graph"
            
            available = entity.get("available", False)
            if not available:
                return False, f"Entity '{entity_id}' is unavailable"
            
            return True, None
        
        # Live check via REST API
        try:
            state = await self.rest_client.get_state(entity_id)
            
            if state.get("state") == "unavailable":
                return False, f"Entity '{entity_id}' is unavailable"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to check entity availability: {e}")
            return False, f"Failed to check entity '{entity_id}': {str(e)}"
    
    async def check_entities_availability(
        self,
        entity_ids: List[str]
    ) -> Dict[str, tuple[bool, Optional[str]]]:
        """
        Check availability for multiple entities.
        
        Args:
            entity_ids: List of entity IDs
        
        Returns:
            Dictionary mapping entity_id to (is_available, error_message)
        """
        results = {}
        
        for entity_id in entity_ids:
            is_available, error = await self.check_entity_availability(entity_id)
            results[entity_id] = (is_available, error)
        
        return results
    
    async def preflight_check(
        self,
        spec: Dict[str, Any],
        required_for_risk: Optional[str] = None
    ) -> tuple[bool, List[str]]:
        """
        Perform preflight check for a spec.
        
        Args:
            spec: Automation spec dictionary
            required_for_risk: Risk level that requires preflight (default: "high")
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        if required_for_risk is None:
            required_for_risk = "high"
        
        policy = spec.get("policy", {})
        risk = policy.get("risk", "low")
        
        # Only require preflight for high-risk or if explicitly requested
        if risk != required_for_risk and required_for_risk != "all":
            return True, []
        
        errors = []
        
        # Get all entity IDs from actions
        actions = spec.get("actions", [])
        entity_ids = []
        for action in actions:
            resolved_ids = action.get("resolved_entity_ids", [])
            entity_ids.extend(resolved_ids)
        
        # Remove duplicates
        entity_ids = list(set(entity_ids))
        
        # Check availability
        results = await self.check_entities_availability(entity_ids)
        
        for entity_id, (is_available, error) in results.items():
            if not is_available:
                errors.append(error or f"Entity '{entity_id}' preflight check failed")
        
        is_valid = len(errors) == 0
        return is_valid, errors
