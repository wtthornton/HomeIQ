"""
Target Resolution

Epic D1: Resolve area/device_class selectors to concrete entities
"""

import logging
from typing import Any, Dict, List

from ..capability.capability_graph import CapabilityGraph

logger = logging.getLogger(__name__)


class TargetResolver:
    """
    Resolves target selectors to concrete entity IDs.
    
    This class handles the resolution of abstract target selectors (area,
    device_class, user) to concrete entity IDs that can be used for
    automation execution. It provides a unified interface for different
    target types and ensures proper error handling.
    
    Features:
    - Resolve area selectors to concrete entity IDs
    - Resolve device_class selectors to entities
    - Resolve entity_id directly (single or list)
    - Handle user selectors (placeholder for future implementation)
    - Produce execution plans with resolved targets
    - Remove duplicate entity IDs while preserving order
    
    Example:
        >>> resolver = TargetResolver(capability_graph)
        >>> target = {"area": "living_room"}
        >>> entity_ids = resolver.resolve_target(target)
        >>> # Returns: ["light.living_room", "switch.living_room", ...]
    """
    
    def __init__(self, capability_graph: CapabilityGraph):
        """
        Initialize target resolver.
        
        Args:
            capability_graph: CapabilityGraph instance for entity lookups
            
        Raises:
            TypeError: If capability_graph is not a CapabilityGraph instance
        """
        if not isinstance(capability_graph, CapabilityGraph):
            raise TypeError(
                f"capability_graph must be CapabilityGraph instance, "
                f"got {type(capability_graph).__name__}"
            )
        self.capability_graph = capability_graph
    
    def resolve_target(self, target: Dict[str, Any]) -> List[str]:
        """
        Resolve target to list of entity IDs.
        
        Supports multiple target types:
        - entity_id: Direct entity ID(s) - string or list
        - area: Area name - resolves to all entities in that area
        - device_class: Device class - resolves to all entities of that class
        - user: User identifier - not yet implemented (returns empty list)
        
        Args:
            target: Target dictionary with one of:
                - entity_id: str | List[str]
                - area: str
                - device_class: str
                - user: str
        
        Returns:
            List of resolved entity IDs (deduplicated, order preserved)
            
        Raises:
            ValueError: If target is empty or contains invalid combination of keys
            KeyError: If capability_graph methods fail (propagated)
        
        Example:
            >>> target = {"area": "living_room"}
            >>> entity_ids = resolver.resolve_target(target)
            >>> # Returns: ["light.living_room", "switch.living_room"]
        """
        if not target:
            logger.warning("Empty target dictionary provided")
            return []
        
        entity_ids = []
        
        # Direct entity_id (highest priority)
        if "entity_id" in target:
            entity_id = target["entity_id"]
            if isinstance(entity_id, str):
                entity_ids.append(entity_id)
            elif isinstance(entity_id, list):
                if not all(isinstance(eid, str) for eid in entity_id):
                    raise ValueError("entity_id list must contain only strings")
                entity_ids.extend(entity_id)
            else:
                raise ValueError(f"entity_id must be str or List[str], got {type(entity_id).__name__}")
        
        # Area selector
        elif "area" in target:
            area_id = target["area"]
            if not isinstance(area_id, str):
                raise ValueError(f"area must be str, got {type(area_id).__name__}")
            
            try:
                entities = self.capability_graph.get_entities_by_area(area_id)
                entity_ids.extend([e["entity_id"] for e in entities])
                logger.debug(f"Resolved area '{area_id}' to {len(entities)} entities")
            except Exception as e:
                logger.error(f"Failed to resolve area '{area_id}': {e}")
                raise
        
        # Device class selector
        elif "device_class" in target:
            device_class = target["device_class"]
            if not isinstance(device_class, str):
                raise ValueError(f"device_class must be str, got {type(device_class).__name__}")
            
            try:
                entities = self.capability_graph.get_entities_by_device_class(device_class)
                entity_ids.extend([e["entity_id"] for e in entities])
                logger.debug(f"Resolved device_class '{device_class}' to {len(entities)} entities")
            except Exception as e:
                logger.error(f"Failed to resolve device_class '{device_class}': {e}")
                raise
        
        # User selector (not yet implemented)
        elif "user" in target:
            user = target["user"]
            logger.warning(f"User selector '{user}' not yet implemented - returning empty list")
            # TODO: Implement user->entity mapping when user management is added
            return []
        
        else:
            logger.warning(f"Unknown target type: {list(target.keys())}")
            return []
        
        # Remove duplicates while preserving order
        return self._deduplicate_entity_ids(entity_ids)
    
    def _deduplicate_entity_ids(self, entity_ids: List[str]) -> List[str]:
        """
        Remove duplicate entity IDs while preserving order.
        
        Args:
            entity_ids: List of entity IDs (may contain duplicates)
        
        Returns:
            List of unique entity IDs in original order
        """
        seen = set()
        unique_entity_ids = []
        for eid in entity_ids:
            if eid not in seen:
                seen.add(eid)
                unique_entity_ids.append(eid)
        return unique_entity_ids
    
    def resolve_action_targets(
        self,
        actions: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Resolve targets for all actions.
        
        Processes each action's target selector and adds resolved entity IDs
        to the action dictionary. If resolution fails for an action, it is
        still included but with an empty resolved_entity_ids list and an
        error message.
        
        Args:
            actions: List of action dictionaries, each with:
                - id: str (action identifier)
                - target: Dict (target selector)
                - capability: str (service capability)
                - data: Dict (action data)
        
        Returns:
            List of actions with resolved targets, each containing:
                - All original action fields
                - resolved_entity_ids: List[str] (resolved entity IDs)
                - target_resolved: bool (True if resolution succeeded)
                - resolution_error: Optional[str] (error message if failed)
        
        Example:
            >>> actions = [{"id": "act1", "target": {"area": "living_room"}}]
            >>> resolved = resolver.resolve_action_targets(actions)
            >>> # Returns: [{
            >>> #     "id": "act1",
            >>> #     "target": {"area": "living_room"},
            >>> #     "resolved_entity_ids": ["light.living_room", ...],
            >>> #     "target_resolved": True
            >>> # }]
        """
        if not isinstance(actions, list):
            raise ValueError(f"actions must be list, got {type(actions).__name__}")
        
        resolved_actions = []
        
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                logger.warning(f"Action {i} is not a dictionary, skipping")
                continue
            
            action_id = action.get("id", f"action_{i}")
            target = action.get("target", {})
            
            try:
                resolved_entity_ids = self.resolve_target(target)
                
                resolved_action = action.copy()
                resolved_action["resolved_entity_ids"] = resolved_entity_ids
                resolved_action["target_resolved"] = True
                
                resolved_actions.append(resolved_action)
                
                if not resolved_entity_ids:
                    logger.warning(
                        f"Action {action_id} resolved to empty entity list - "
                        f"target may be invalid or no entities match"
                    )
                    
            except Exception as e:
                logger.error(f"Failed to resolve target for action {action_id}: {e}")
                resolved_action = action.copy()
                resolved_action["resolved_entity_ids"] = []
                resolved_action["target_resolved"] = False
                resolved_action["resolution_error"] = str(e)
                resolved_actions.append(resolved_action)
        
        return resolved_actions
    
    def create_execution_plan(
        self,
        spec: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create execution plan with resolved targets.
        
        This method orchestrates the resolution of all action targets
        in a spec and produces a structured execution plan that can be
        used by the executor.
        
        Args:
            spec: Automation spec dictionary with:
                - id: str (spec identifier)
                - version: str (spec version)
                - actions: List[Dict] (action definitions)
        
        Returns:
            Execution plan dictionary with:
                - spec_id: str
                - spec_version: str
                - actions: List[Dict] (actions with resolved_entity_ids)
                - total_actions: int
                - total_entities: int
        
        Raises:
            KeyError: If spec is missing required fields
            ValueError: If target resolution fails (propagated from resolve_target)
        
        Example:
            >>> plan = resolver.create_execution_plan(spec)
            >>> # Returns: {
            >>> #     "spec_id": "auto_1",
            >>> #     "spec_version": "1.0.0",
            >>> #     "actions": [...],
            >>> #     "total_actions": 2,
            >>> #     "total_entities": 5
            >>> # }
        """
        if not isinstance(spec, dict):
            raise ValueError(f"spec must be dict, got {type(spec).__name__}")
        
        spec_id = spec.get("id", "unknown")
        spec_version = spec.get("version", "unknown")
        actions = spec.get("actions", [])
        
        if not actions:
            logger.warning(f"Spec {spec_id} has no actions")
            return {
                "spec_id": spec_id,
                "spec_version": spec_version,
                "actions": [],
                "total_actions": 0,
                "total_entities": 0
            }
        
        try:
            resolved_actions = self.resolve_action_targets(actions)
        except Exception as e:
            logger.error(f"Failed to resolve action targets for spec {spec_id}: {e}")
            raise ValueError(f"Target resolution failed: {e}") from e
        
        total_entities = sum(
            len(action.get("resolved_entity_ids", []))
            for action in resolved_actions
        )
        
        plan = {
            "spec_id": spec_id,
            "spec_version": spec_version,
            "actions": resolved_actions,
            "total_actions": len(resolved_actions),
            "total_entities": total_entities
        }
        
        logger.info(
            f"Created execution plan for spec {spec_id} v{spec_version}: "
            f"{plan['total_actions']} actions, {plan['total_entities']} entities"
        )
        
        return plan
