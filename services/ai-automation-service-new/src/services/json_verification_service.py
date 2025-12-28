"""
JSON Verification Service

Verifies HomeIQ JSON Automation integrity and provides rebuild capabilities.
"""

import logging
from typing import Any

from shared.homeiq_automation.schema import HomeIQAutomation
from shared.homeiq_automation.validator import HomeIQAutomationValidator, ValidationResult

from ..clients.data_api_client import DataAPIClient

logger = logging.getLogger(__name__)


class JSONVerificationService:
    """
    Service for verifying HomeIQ JSON automations.
    
    Features:
    - Schema validation
    - Entity/device validation
    - Consistency checks
    - Rebuild JSON from YAML (reverse transformation)
    """
    
    def __init__(self, data_api_client: DataAPIClient | None = None):
        """
        Initialize JSON verification service.
        
        Args:
            data_api_client: Optional DataAPIClient for entity/device validation
        """
        self.data_api_client = data_api_client
        self.validator = HomeIQAutomationValidator(data_api_client=data_api_client)
    
    async def verify(
        self,
        automation_json: dict[str, Any] | HomeIQAutomation,
        validate_entities: bool = True,
        validate_devices: bool = True,
        validate_safety: bool = True
    ) -> ValidationResult:
        """
        Verify HomeIQ JSON automation.
        
        Args:
            automation_json: Automation JSON dict or HomeIQAutomation instance
            validate_entities: Whether to validate entity IDs exist
            validate_devices: Whether to validate device IDs exist
            validate_safety: Whether to validate safety rules
        
        Returns:
            ValidationResult with validation status and errors/warnings
        """
        return await self.validator.validate(
            automation_json=automation_json,
            validate_entities=validate_entities,
            validate_devices=validate_devices,
            validate_safety=validate_safety
        )
    
    async def verify_consistency(
        self,
        automation_json: dict[str, Any] | HomeIQAutomation
    ) -> dict[str, Any]:
        """
        Verify consistency between different parts of the automation.
        
        Args:
            automation_json: Automation JSON dict or HomeIQAutomation instance
        
        Returns:
            Dictionary with consistency check results
        """
        try:
            if isinstance(automation_json, dict):
                automation = HomeIQAutomation(**automation_json)
            else:
                automation = automation_json
            
            issues: list[str] = []
            warnings: list[str] = []
            
            # Check device_context matches triggers/conditions/actions
            context_entity_ids = set(automation.device_context.entity_ids)
            
            # Collect entity IDs from automation structure
            automation_entity_ids: set[str] = set()
            
            for trigger in automation.triggers:
                if trigger.entity_id:
                    if isinstance(trigger.entity_id, list):
                        automation_entity_ids.update(trigger.entity_id)
                    else:
                        automation_entity_ids.add(trigger.entity_id)
            
            if automation.conditions:
                for condition in automation.conditions:
                    if condition.entity_id:
                        if isinstance(condition.entity_id, list):
                            automation_entity_ids.update(condition.entity_id)
                        else:
                            automation_entity_ids.add(condition.entity_id)
            
            for action in automation.actions:
                if action.target and "entity_id" in action.target:
                    target_entity_id = action.target["entity_id"]
                    if isinstance(target_entity_id, list):
                        automation_entity_ids.update(target_entity_id)
                    elif isinstance(target_entity_id, str):
                        automation_entity_ids.add(target_entity_id)
            
            # Check for entities in automation that aren't in device_context
            missing_in_context = automation_entity_ids - context_entity_ids
            if missing_in_context:
                warnings.append(
                    f"Entities used in automation but not in device_context: "
                    f"{', '.join(missing_in_context)}"
                )
            
            # Check for entities in device_context that aren't used
            unused_in_context = context_entity_ids - automation_entity_ids
            if unused_in_context:
                warnings.append(
                    f"Entities in device_context but not used in automation: "
                    f"{', '.join(unused_in_context)}"
                )
            
            # Check area consistency
            if automation.area_context:
                area_ids = set(automation.area_context)
                device_area_ids = set(automation.device_context.area_ids or [])
                
                if area_ids != device_area_ids:
                    warnings.append(
                        f"Area context mismatch: area_context={area_ids}, "
                        f"device_context.area_ids={device_area_ids}"
                    )
            
            return {
                "consistent": len(issues) == 0,
                "issues": issues,
                "warnings": warnings
            }
        
        except Exception as e:
            logger.error(f"Consistency check failed: {e}")
            return {
                "consistent": False,
                "issues": [f"Consistency check error: {e}"],
                "warnings": []
            }
    
    async def rebuild_from_yaml(
        self,
        yaml_content: str,
        suggestion_id: int | None = None
    ) -> dict[str, Any] | None:
        """
        Rebuild HomeIQ JSON from YAML (reverse transformation).
        
        This is a basic implementation. Full implementation would use LLM
        to extract HomeIQ metadata from YAML.
        
        Args:
            yaml_content: Home Assistant automation YAML
            suggestion_id: Optional suggestion ID for metadata
        
        Returns:
            HomeIQ JSON Automation dictionary or None if rebuild fails
        """
        try:
            import yaml as yaml_lib
            
            # Parse YAML
            yaml_data = yaml_lib.safe_load(yaml_content)
            if not yaml_data:
                return None
            
            # Extract basic information
            automation_json: dict[str, Any] = {
                "alias": yaml_data.get("alias", "Automation"),
                "description": yaml_data.get("description"),
                "version": "1.0.0",
                "homeiq_metadata": {
                    "created_by": "json_verification_service",
                    "created_at": "2025-01-01T00:00:00Z",
                    "suggestion_id": suggestion_id,
                    "use_case": "convenience",  # Default
                    "complexity": "medium"  # Default
                },
                "device_context": {
                    "device_ids": [],
                    "entity_ids": [],
                    "device_types": [],
                    "area_ids": None
                },
                "triggers": [],
                "actions": []
            }
            
            # Extract triggers
            triggers = yaml_data.get("trigger") or yaml_data.get("triggers", [])
            for trigger in triggers:
                automation_json["triggers"].append({
                    "platform": trigger.get("platform"),
                    "entity_id": trigger.get("entity_id"),
                    "to": trigger.get("to"),
                    "from": trigger.get("from"),
                    "at": trigger.get("at"),
                    "extra": {k: v for k, v in trigger.items() 
                             if k not in ["platform", "entity_id", "to", "from", "at"]}
                })
            
            # Extract actions
            actions = yaml_data.get("action") or yaml_data.get("actions", [])
            for action in actions:
                automation_json["actions"].append({
                    "service": action.get("service"),
                    "target": action.get("target"),
                    "data": action.get("data", {}),
                    "extra": {k: v for k, v in action.items() 
                             if k not in ["service", "target", "data"]}
                })
            
            # Extract conditions
            conditions = yaml_data.get("condition") or yaml_data.get("conditions")
            if conditions:
                automation_json["conditions"] = []
                for condition in conditions:
                    automation_json["conditions"].append({
                        "condition": condition.get("condition"),
                        "entity_id": condition.get("entity_id"),
                        "state": condition.get("state"),
                        "extra": {k: v for k, v in condition.items() 
                                 if k not in ["condition", "entity_id", "state"]}
                    })
            
            # Extract entity IDs
            entity_ids: set[str] = set()
            for trigger in automation_json["triggers"]:
                if trigger.get("entity_id"):
                    if isinstance(trigger["entity_id"], list):
                        entity_ids.update(trigger["entity_id"])
                    else:
                        entity_ids.add(trigger["entity_id"])
            
            for action in automation_json["actions"]:
                if action.get("target", {}).get("entity_id"):
                    target_entity_id = action["target"]["entity_id"]
                    if isinstance(target_entity_id, list):
                        entity_ids.update(target_entity_id)
                    elif isinstance(target_entity_id, str):
                        entity_ids.add(target_entity_id)
            
            automation_json["device_context"]["entity_ids"] = list(entity_ids)
            
            logger.info(f"Rebuilt HomeIQ JSON from YAML: {automation_json['alias']}")
            return automation_json
        
        except Exception as e:
            logger.error(f"Failed to rebuild JSON from YAML: {e}")
            return None

