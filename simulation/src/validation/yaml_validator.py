"""
YAML Validator

Comprehensive YAML validation with ground truth comparison.
"""

import logging
import yaml
from typing import Any

logger = logging.getLogger(__name__)


class YAMLValidator:
    """
    YAML validator for simulation framework.
    
    Validates:
    - YAML syntax
    - Home Assistant automation structure
    - Entity IDs
    - Safety checks
    - Ground truth comparison
    """

    def __init__(self):
        """Initialize YAML validator."""
        logger.info("YAMLValidator initialized")

    def validate_yaml_syntax(self, yaml_content: str) -> dict[str, Any]:
        """
        Validate YAML syntax.
        
        Args:
            yaml_content: YAML content string
            
        Returns:
            Validation result dictionary
        """
        errors = []
        
        try:
            parsed = yaml.safe_load(yaml_content)
            if parsed is None:
                errors.append("YAML is empty or contains only comments")
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {str(e)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors
        }

    def validate_automation_structure(self, yaml_content: str) -> dict[str, Any]:
        """
        Validate Home Assistant automation structure.
        
        Args:
            yaml_content: YAML content string
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        try:
            parsed = yaml.safe_load(yaml_content)
            
            if not isinstance(parsed, dict):
                errors.append("YAML root must be a dictionary")
                return {"is_valid": False, "errors": errors, "warnings": warnings}
            
            if "automation" not in parsed:
                errors.append("Missing 'automation' key")
                return {"is_valid": False, "errors": errors, "warnings": warnings}
            
            automations = parsed["automation"]
            if not isinstance(automations, list):
                errors.append("'automation' must be a list")
                return {"is_valid": False, "errors": errors, "warnings": warnings}
            
            for i, automation in enumerate(automations):
                if not isinstance(automation, dict):
                    errors.append(f"Automation {i} must be a dictionary")
                    continue
                
                # Check required fields
                if "alias" not in automation:
                    warnings.append(f"Automation {i} missing 'alias' (optional but recommended)")
                
                if "trigger" not in automation:
                    errors.append(f"Automation {i} missing 'trigger'")
                
                if "action" not in automation:
                    errors.append(f"Automation {i} missing 'action'")
        
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def validate_entity_ids(
        self,
        yaml_content: str,
        valid_entities: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Validate entity IDs in YAML.
        
        Args:
            yaml_content: YAML content string
            valid_entities: Optional list of valid entity IDs
            
        Returns:
            Validation result dictionary
        """
        errors = []
        warnings = []
        
        try:
            parsed = yaml.safe_load(yaml_content)
            
            if valid_entities:
                valid_set = set(valid_entities)
                
                # Extract entity IDs from YAML
                entity_ids = self._extract_entity_ids(parsed)
                
                for entity_id in entity_ids:
                    if entity_id not in valid_set:
                        errors.append(f"Invalid entity ID: {entity_id}")
        
        except Exception as e:
            errors.append(f"Entity validation error: {str(e)}")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def validate_ground_truth(
        self,
        generated_yaml: str,
        ground_truth_yaml: str
    ) -> dict[str, Any]:
        """
        Validate generated YAML against ground truth.
        
        Args:
            generated_yaml: Generated YAML content
            ground_truth_yaml: Ground truth YAML content
            
        Returns:
            Comparison result dictionary
        """
        try:
            generated = yaml.safe_load(generated_yaml)
            ground_truth = yaml.safe_load(ground_truth_yaml)
            
            # Compare structure
            structure_match = self._compare_structure(generated, ground_truth)
            
            # Compare entity IDs
            generated_entities = self._extract_entity_ids(generated) if generated else set()
            ground_truth_entities = self._extract_entity_ids(ground_truth) if ground_truth else set()
            
            entity_match = generated_entities == ground_truth_entities
            
            return {
                "structure_match": structure_match,
                "entity_match": entity_match,
                "generated_entities": list(generated_entities),
                "ground_truth_entities": list(ground_truth_entities),
                "similarity_score": self._calculate_yaml_similarity(generated, ground_truth)
            }
        
        except Exception as e:
            return {
                "error": str(e),
                "structure_match": False,
                "entity_match": False
            }

    def _extract_entity_ids(self, yaml_obj: Any) -> set[str]:
        """Extract all entity IDs from YAML object."""
        entity_ids = set()
        
        if isinstance(yaml_obj, dict):
            for key, value in yaml_obj.items():
                if key == "entity_id":
                    if isinstance(value, str):
                        entity_ids.add(value)
                    elif isinstance(value, list):
                        entity_ids.update(value)
                else:
                    entity_ids.update(self._extract_entity_ids(value))
        elif isinstance(yaml_obj, list):
            for item in yaml_obj:
                entity_ids.update(self._extract_entity_ids(item))
        
        return entity_ids

    def _compare_structure(self, obj1: Any, obj2: Any) -> bool:
        """Compare YAML structure (keys and types)."""
        if type(obj1) != type(obj2):
            return False
        
        if isinstance(obj1, dict):
            if set(obj1.keys()) != set(obj2.keys()):
                return False
            return all(self._compare_structure(obj1[k], obj2[k]) for k in obj1.keys())
        
        if isinstance(obj1, list):
            if len(obj1) != len(obj2):
                return False
            return all(self._compare_structure(obj1[i], obj2[i]) for i in range(len(obj1)))
        
        return True

    def _calculate_yaml_similarity(self, obj1: Any, obj2: Any) -> float:
        """Calculate similarity score between two YAML objects."""
        if obj1 == obj2:
            return 1.0
        
        if type(obj1) != type(obj2):
            return 0.0
        
        if isinstance(obj1, dict):
            keys1 = set(obj1.keys())
            keys2 = set(obj2.keys())
            common_keys = keys1 & keys2
            
            if not keys1 or not keys2:
                return 0.0
            
            key_similarity = len(common_keys) / max(len(keys1), len(keys2))
            
            value_similarities = [
                self._calculate_yaml_similarity(obj1[k], obj2[k])
                for k in common_keys
            ]
            
            value_similarity = sum(value_similarities) / len(value_similarities) if value_similarities else 0.0
            
            return (key_similarity + value_similarity) / 2
        
        if isinstance(obj1, list):
            if not obj1 or not obj2:
                return 0.0
            
            max_len = max(len(obj1), len(obj2))
            similarities = [
                self._calculate_yaml_similarity(obj1[i] if i < len(obj1) else None, obj2[i] if i < len(obj2) else None)
                for i in range(max_len)
            ]
            
            return sum(similarities) / len(similarities) if similarities else 0.0
        
        return 0.0

