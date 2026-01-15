"""
Service Compatibility Validation

Epic D2: Validate service exists and required fields present
"""

import logging
from typing import Any, Dict, List, Optional

from ..capability.capability_graph import CapabilityGraph

logger = logging.getLogger(__name__)


class ServiceValidator:
    """
    Validates service compatibility.
    
    Features:
    - Check service exists in capability graph
    - Validate required fields present in action data
    - Check supported features for key domains (light, climate, lock)
    - Reference service schemas from capability graph
    """
    
    def __init__(self, capability_graph: CapabilityGraph):
        """
        Initialize service validator.
        
        Args:
            capability_graph: CapabilityGraph instance
        """
        self.capability_graph = capability_graph
    
    def validate_capability(self, capability: str) -> tuple[bool, Optional[str]]:
        """
        Validate capability exists.
        
        Args:
            capability: Capability string (e.g., "light.turn_on")
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        service_info = self.capability_graph.get_capability_service(capability)
        
        if not service_info:
            return False, f"Capability '{capability}' not found in capability graph"
        
        domain, service = service_info
        
        if not self.capability_graph.is_service_available(domain, service):
            return False, f"Service '{domain}.{service}' not available"
        
        return True, None
    
    def validate_action_fields(
        self,
        capability: str,
        action_data: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate required fields are present in action data.
        
        Args:
            capability: Capability string
            action_data: Action data dictionary
        
        Returns:
            Tuple of (is_valid, list_of_missing_fields)
        """
        service_info = self.capability_graph.get_capability_service(capability)
        if not service_info:
            return False, ["capability"]
        
        domain, service = service_info
        schema = self.capability_graph.get_service_schema(domain, service)
        
        if not schema:
            # No schema available - assume valid
            return True, []
        
        fields = schema.get("fields", {})
        required_fields = [
            field_name for field_name, field_schema in fields.items()
            if field_schema.get("required", False)
        ]
        
        missing_fields = [
            field for field in required_fields
            if field not in action_data
        ]
        
        is_valid = len(missing_fields) == 0
        return is_valid, missing_fields
    
    def validate_supported_features(
        self,
        capability: str,
        entity_id: str,
        feature_required: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate entity supports required features.
        
        Args:
            capability: Capability string
            entity_id: Entity ID
            feature_required: Optional feature name to check
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        entity = self.capability_graph.get_entity(entity_id)
        if not entity:
            return False, f"Entity '{entity_id}' not found"
        
        # Check supported features for key domains
        domain = entity.get("domain")
        supported_features = entity.get("supported_features", 0)
        
        if domain == "light":
            # Light features (example)
            if feature_required == "brightness" and not (supported_features & 1):
                return False, f"Entity '{entity_id}' does not support brightness"
            if feature_required == "color" and not (supported_features & 16):
                return False, f"Entity '{entity_id}' does not support color"
        
        elif domain == "climate":
            # Climate features (example)
            if feature_required == "target_temperature" and not (supported_features & 1):
                return False, f"Entity '{entity_id}' does not support target temperature"
        
        elif domain == "lock":
            # Lock features (example)
            if feature_required == "open" and not (supported_features & 1):
                return False, f"Entity '{entity_id}' does not support open"
        
        return True, None
    
    def validate_action(
        self,
        action: Dict[str, Any]
    ) -> tuple[bool, List[str]]:
        """
        Validate a single action.
        
        Args:
            action: Action dictionary
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        capability = action.get("capability")
        if not capability:
            errors.append("Action missing 'capability' field")
            return False, errors
        
        # Validate capability exists
        is_valid, error = self.validate_capability(capability)
        if not is_valid:
            errors.append(error)
        
        # Validate required fields
        action_data = action.get("data", {})
        is_valid_fields, missing_fields = self.validate_action_fields(capability, action_data)
        if not is_valid_fields:
            errors.append(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate supported features for resolved entities
        resolved_entity_ids = action.get("resolved_entity_ids", [])
        for entity_id in resolved_entity_ids:
            # Check if capability requires specific features
            # This is a simplified check - could be more sophisticated
            is_valid_features, error = self.validate_supported_features(
                capability, entity_id
            )
            if not is_valid_features:
                errors.append(error)
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def validate_actions(
        self,
        actions: List[Dict[str, Any]]
    ) -> tuple[bool, Dict[str, List[str]]]:
        """
        Validate all actions.
        
        Args:
            actions: List of action dictionaries
        
        Returns:
            Tuple of (is_valid, dict_of_action_errors)
        """
        all_valid = True
        action_errors = {}
        
        for i, action in enumerate(actions):
            action_id = action.get("id", f"action_{i}")
            is_valid, errors = self.validate_action(action)
            
            if not is_valid:
                all_valid = False
                action_errors[action_id] = errors
        
        return all_valid, action_errors
