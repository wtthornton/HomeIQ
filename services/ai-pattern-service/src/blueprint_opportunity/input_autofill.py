"""Input auto-fill logic for blueprint inputs."""

import logging
from typing import Any, Optional

from .schemas import AutofilledInput, DeviceSignature

logger = logging.getLogger(__name__)


class InputAutofill:
    """
    Auto-fills blueprint inputs from user's device inventory.
    
    Matches blueprint input requirements (domain, device_class) to
    available devices and entities to automatically configure the blueprint.
    """
    
    def __init__(self):
        """Initialize input autofill."""
        pass
    
    def autofill_inputs(
        self,
        inputs: dict[str, Any],
        devices: list[DeviceSignature],
        area_preference: Optional[str] = None,
    ) -> tuple[list[AutofilledInput], list[str]]:
        """
        Auto-fill blueprint inputs from available devices.
        
        Args:
            inputs: Blueprint input definitions
            devices: Available devices
            area_preference: Preferred area ID for matching
            
        Returns:
            Tuple of (autofilled_inputs, unfilled_input_names)
        """
        autofilled = []
        unfilled = []
        used_entities = set()  # Track used entities to avoid duplicates
        
        for input_name, input_def in inputs.items():
            if not isinstance(input_def, dict):
                continue
            
            selector_type = input_def.get("selector_type")
            domain = input_def.get("domain")
            device_class = input_def.get("device_class")
            is_required = input_def.get("is_required", True)
            
            # Find matching device
            result = self._find_best_match(
                devices,
                domain,
                device_class,
                area_preference,
                used_entities,
            )
            
            if result:
                entity_id, confidence, alternatives = result
                used_entities.add(entity_id)
                
                autofilled.append(AutofilledInput(
                    input_name=input_name,
                    input_type=selector_type or "entity",
                    value=entity_id,
                    entity_id=entity_id,
                    confidence=confidence,
                    is_required=is_required,
                    alternatives=alternatives,
                ))
            elif is_required:
                unfilled.append(input_name)
            else:
                # Optional input not filled - that's okay
                pass
        
        return autofilled, unfilled
    
    def _find_best_match(
        self,
        devices: list[DeviceSignature],
        domain: Optional[str],
        device_class: Optional[str],
        area_preference: Optional[str],
        used_entities: set[str],
    ) -> Optional[tuple[str, float, list[str]]]:
        """
        Find best matching device for an input requirement.
        
        Args:
            devices: Available devices
            domain: Required domain (e.g., "binary_sensor")
            device_class: Required device class (e.g., "motion")
            area_preference: Preferred area ID
            used_entities: Set of already-used entity IDs
            
        Returns:
            Tuple of (entity_id, confidence, alternatives) or None
        """
        candidates = []
        
        for device in devices:
            if device.entity_id in used_entities:
                continue
            
            score = self._calculate_match_score(
                device, domain, device_class, area_preference
            )
            
            if score > 0:
                candidates.append((device, score))
        
        if not candidates:
            return None
        
        # Sort by score
        candidates.sort(key=lambda x: x[1], reverse=True)
        
        best_device, best_score = candidates[0]
        alternatives = [c[0].entity_id for c in candidates[1:4]]  # Top 3 alternatives
        
        return best_device.entity_id, best_score, alternatives
    
    def _calculate_match_score(
        self,
        device: DeviceSignature,
        domain: Optional[str],
        device_class: Optional[str],
        area_preference: Optional[str],
    ) -> float:
        """
        Calculate match score for a device against requirements.
        
        Scoring:
        - Domain match: 0.4
        - Device class match: 0.4
        - Area match: 0.2
        """
        score = 0.0
        
        # Domain match (required)
        if domain:
            if device.domain == domain:
                score += 0.4
            else:
                return 0.0  # Domain mismatch = no match
        else:
            score += 0.4  # No domain requirement = full score
        
        # Device class match
        if device_class:
            if device.device_class == device_class:
                score += 0.4
            else:
                score += 0.1  # Partial score for domain match without class
        else:
            score += 0.4  # No device class requirement = full score
        
        # Area preference match
        if area_preference and device.area_id == area_preference:
            score += 0.2
        else:
            score += 0.1  # Partial score
        
        return min(1.0, score)
    
    def get_autofill_status(
        self,
        autofilled: list[AutofilledInput],
        unfilled: list[str],
    ) -> dict[str, Any]:
        """
        Get status summary of autofill operation.
        
        Returns:
            Dictionary with status information
        """
        total_inputs = len(autofilled) + len(unfilled)
        filled_count = len(autofilled)
        required_unfilled = [u for u in unfilled]  # All unfilled are required
        
        avg_confidence = 0.0
        if autofilled:
            avg_confidence = sum(a.confidence for a in autofilled) / len(autofilled)
        
        return {
            "total_inputs": total_inputs,
            "filled_count": filled_count,
            "unfilled_count": len(unfilled),
            "completion_rate": filled_count / total_inputs if total_inputs > 0 else 1.0,
            "average_confidence": avg_confidence,
            "required_unfilled": required_unfilled,
            "ready_to_deploy": len(required_unfilled) == 0,
        }
    
    def generate_input_dict(
        self,
        autofilled: list[AutofilledInput],
    ) -> dict[str, str]:
        """
        Generate input dictionary for blueprint deployment.
        
        Args:
            autofilled: List of autofilled inputs
            
        Returns:
            Dictionary mapping input names to values
        """
        return {a.input_name: a.value for a in autofilled}
