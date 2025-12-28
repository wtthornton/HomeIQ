"""
HomeIQ JSON Automation Validator

Validates HomeIQ JSON automations against schema and business rules.
"""

import logging
from typing import Any

from pydantic import ValidationError

from .schema import HomeIQAutomation

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validation operation."""
    
    def __init__(self, valid: bool, errors: list[str] | None = None, warnings: list[str] | None = None):
        self.valid = valid
        self.errors = errors or []
        self.warnings = warnings or []

    def __bool__(self) -> bool:
        return self.valid


class HomeIQAutomationValidator:
    """
    Validates HomeIQ JSON automations.
    
    Features:
    - Pydantic schema validation
    - Entity ID validation (via Data API)
    - Device capability validation
    - Safety rule validation
    - Energy impact calculation
    """
    
    def __init__(self, data_api_client=None):
        """
        Initialize validator.
        
        Args:
            data_api_client: Optional DataAPIClient for entity/device validation
        """
        self.data_api_client = data_api_client
    
    async def validate(
        self,
        automation_json: dict[str, Any] | HomeIQAutomation,
        validate_entities: bool = True,
        validate_devices: bool = True,
        validate_safety: bool = True
    ) -> ValidationResult:
        """
        Validate HomeIQ automation JSON.
        
        Args:
            automation_json: Automation JSON dict or HomeIQAutomation instance
            validate_entities: Whether to validate entity IDs exist
            validate_devices: Whether to validate device IDs exist
            validate_safety: Whether to validate safety rules
        
        Returns:
            ValidationResult with validation status and errors/warnings
        """
        errors: list[str] = []
        warnings: list[str] = []
        
        # Step 1: Pydantic schema validation
        try:
            if isinstance(automation_json, dict):
                automation = HomeIQAutomation(**automation_json)
            else:
                automation = automation_json
        except ValidationError as e:
            for error in e.errors():
                field = ".".join(str(x) for x in error["loc"])
                errors.append(f"Schema validation error in {field}: {error['msg']}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        except Exception as e:
            errors.append(f"Failed to parse automation JSON: {e}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)
        
        # Step 2: Entity ID validation
        if validate_entities and self.data_api_client:
            entity_errors = await self._validate_entities(automation)
            errors.extend(entity_errors)
        
        # Step 3: Device ID validation
        if validate_devices and self.data_api_client:
            device_errors = await self._validate_devices(automation)
            errors.extend(device_errors)
        
        # Step 4: Device capability validation
        if validate_devices:
            capability_warnings = self._validate_device_capabilities(automation)
            warnings.extend(capability_warnings)
        
        # Step 5: Safety rule validation
        if validate_safety:
            safety_errors, safety_warnings = self._validate_safety_rules(automation)
            errors.extend(safety_errors)
            warnings.extend(safety_warnings)
        
        # Step 6: Energy impact validation
        energy_warnings = self._validate_energy_impact(automation)
        warnings.extend(energy_warnings)
        
        # Step 7: Consistency checks
        consistency_errors = self._validate_consistency(automation)
        errors.extend(consistency_errors)
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors if errors else None,
            warnings=warnings if warnings else None
        )
    
    async def _validate_entities(self, automation: HomeIQAutomation) -> list[str]:
        """Validate that all entity IDs exist."""
        errors: list[str] = []
        
        if not self.data_api_client:
            return errors
        
        try:
            # Collect all entity IDs from triggers, conditions, and actions
            entity_ids: set[str] = set()
            
            # From triggers
            for trigger in automation.triggers:
                if trigger.entity_id:
                    if isinstance(trigger.entity_id, list):
                        entity_ids.update(trigger.entity_id)
                    else:
                        entity_ids.add(trigger.entity_id)
            
            # From conditions
            if automation.conditions:
                for condition in automation.conditions:
                    if condition.entity_id:
                        if isinstance(condition.entity_id, list):
                            entity_ids.update(condition.entity_id)
                        else:
                            entity_ids.add(condition.entity_id)
            
            # From actions (target.entity_id)
            for action in automation.actions:
                if action.target and "entity_id" in action.target:
                    target_entity_id = action.target["entity_id"]
                    if isinstance(target_entity_id, list):
                        entity_ids.update(target_entity_id)
                    elif isinstance(target_entity_id, str):
                        entity_ids.add(target_entity_id)
            
            # Also check device_context entity_ids
            entity_ids.update(automation.device_context.entity_ids)
            
            if not entity_ids:
                return errors
            
            # Fetch all entities from Data API
            try:
                entities = await self.data_api_client.fetch_entities()
                valid_entity_ids = {e.get("entity_id") for e in entities if e.get("entity_id")}
                
                # Check which entities are invalid
                invalid_entities = [eid for eid in entity_ids if eid not in valid_entity_ids]
                if invalid_entities:
                    errors.append(f"Invalid entity IDs: {', '.join(invalid_entities)}")
            except Exception as e:
                logger.warning(f"Failed to validate entities via Data API: {e}")
                errors.append(f"Entity validation failed: {e}")
        
        except Exception as e:
            logger.error(f"Error validating entities: {e}")
            errors.append(f"Entity validation error: {e}")
        
        return errors
    
    async def _validate_devices(self, automation: HomeIQAutomation) -> list[str]:
        """Validate that all device IDs exist."""
        errors: list[str] = []
        
        if not self.data_api_client:
            return errors
        
        try:
            device_ids = automation.device_context.device_ids
            if not device_ids:
                return errors
            
            # Fetch all devices from Data API
            try:
                devices = await self.data_api_client.fetch_devices()
                valid_device_ids = {d.get("device_id") for d in devices if d.get("device_id")}
                
                # Check which devices are invalid
                invalid_devices = [did for did in device_ids if did not in valid_device_ids]
                if invalid_devices:
                    errors.append(f"Invalid device IDs: {', '.join(invalid_devices)}")
            except Exception as e:
                logger.warning(f"Failed to validate devices via Data API: {e}")
                errors.append(f"Device validation failed: {e}")
        
        except Exception as e:
            logger.error(f"Error validating devices: {e}")
            errors.append(f"Device validation error: {e}")
        
        return errors
    
    def _validate_device_capabilities(self, automation: HomeIQAutomation) -> list[str]:
        """Validate that actions use valid device capabilities."""
        warnings: list[str] = []
        
        device_capabilities = automation.device_context.device_capabilities
        if not device_capabilities:
            return warnings
        
        # Check actions for capability usage
        for action in automation.actions:
            if not action.service or not action.data:
                continue
            
            # Check for effect usage (e.g., WLED effects)
            if "effect" in action.data:
                effect = action.data["effect"]
                # Check if effect is in device capabilities
                for device_id, capabilities in device_capabilities.items():
                    if "effects" in capabilities:
                        effects = capabilities.get("effects", [])
                        if effect not in effects:
                            warnings.append(
                                f"Effect '{effect}' may not be supported by device {device_id}. "
                                f"Available effects: {', '.join(effects[:5])}"
                            )
            
            # Check for preset usage
            if "preset" in action.data:
                preset = action.data["preset"]
                for device_id, capabilities in device_capabilities.items():
                    if "presets" in capabilities:
                        presets = capabilities.get("presets", [])
                        if preset not in presets:
                            warnings.append(
                                f"Preset '{preset}' may not be supported by device {device_id}"
                            )
        
        return warnings
    
    def _validate_safety_rules(self, automation: HomeIQAutomation) -> tuple[list[str], list[str]]:
        """Validate safety rules."""
        errors: list[str] = []
        warnings: list[str] = []
        
        if not automation.safety_checks:
            return errors, warnings
        
        safety = automation.safety_checks
        
        # Check for critical devices without confirmation
        if safety.critical_devices and not safety.requires_confirmation:
            warnings.append(
                "Automation uses critical devices but does not require confirmation. "
                "Consider setting requires_confirmation=true"
            )
        
        # Check for time constraints on critical automations
        if safety.critical_devices and not safety.time_constraints:
            warnings.append(
                "Automation uses critical devices but has no time constraints. "
                "Consider adding time constraints for safety"
            )
        
        # Check for security-related automations without time constraints
        if automation.homeiq_metadata.use_case == "security":
            if not safety.time_constraints:
                warnings.append(
                    "Security automation has no time constraints. "
                    "Consider adding time constraints for safety"
                )
        
        return errors, warnings
    
    def _validate_energy_impact(self, automation: HomeIQAutomation) -> list[str]:
        """Validate energy impact calculations."""
        warnings: list[str] = []
        
        if not automation.energy_impact:
            return warnings
        
        energy = automation.energy_impact
        
        # Check if energy impact is calculated but seems unrealistic
        if energy.estimated_power_w and energy.estimated_power_w > 10000:
            warnings.append(
                f"Estimated power consumption ({energy.estimated_power_w}W) seems very high. "
                "Please verify calculation"
            )
        
        if energy.estimated_daily_kwh and energy.estimated_daily_kwh > 100:
            warnings.append(
                f"Estimated daily energy ({energy.estimated_daily_kwh}kWh) seems very high. "
                "Please verify calculation"
            )
        
        return warnings
    
    def _validate_consistency(self, automation: HomeIQAutomation) -> list[str]:
        """Validate consistency between different parts of the automation."""
        errors: list[str] = []
        
        # Check that device_context entity_ids match triggers/conditions/actions
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
            warnings_msg = (
                f"Entities used in automation but not in device_context: "
                f"{', '.join(missing_in_context)}"
            )
            # This is a warning, not an error, but we'll add it as a warning
            logger.warning(warnings_msg)
        
        return errors

