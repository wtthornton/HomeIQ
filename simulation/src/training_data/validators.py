"""
Data Quality Validators

Data quality validation and filtering for collected training data.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataQualityValidator:
    """
    Data quality validator for training data collection.
    
    Validates:
    - Pattern detection data quality
    - Synergy detection data quality
    - Suggestion generation data quality
    - YAML generation data quality
    - Ask AI conversation data quality
    """

    def __init__(
        self,
        min_pattern_confidence: float = 0.5,
        min_synergy_confidence: float = 0.6,
        min_suggestion_quality: float = 0.7,
        min_yaml_validity: bool = True
    ):
        """
        Initialize data quality validator.
        
        Args:
            min_pattern_confidence: Minimum pattern confidence threshold
            min_synergy_confidence: Minimum synergy confidence threshold
            min_suggestion_quality: Minimum suggestion quality threshold
            min_yaml_validity: Require valid YAML
        """
        self.min_pattern_confidence = min_pattern_confidence
        self.min_synergy_confidence = min_synergy_confidence
        self.min_suggestion_quality = min_suggestion_quality
        self.min_yaml_validity = min_yaml_validity
        
        logger.info("DataQualityValidator initialized")

    def validate_pattern_data(self, data_entry: dict[str, Any]) -> bool:
        """
        Validate pattern detection data quality.
        
        Args:
            data_entry: Pattern data entry
            
        Returns:
            True if data passes quality check
        """
        pattern = data_entry.get("pattern", {})
        
        # Check required fields
        if not pattern:
            logger.debug("Pattern validation failed: missing pattern dict")
            return False
        
        # Check confidence
        confidence = pattern.get("confidence", 0.0)
        if confidence < self.min_pattern_confidence:
            logger.debug(f"Pattern validation failed: confidence {confidence} < {self.min_pattern_confidence}")
            return False
        
        # Check occurrences
        occurrences = pattern.get("occurrences", 0)
        if occurrences < 2:  # Minimum occurrences for pattern
            logger.debug(f"Pattern validation failed: occurrences {occurrences} < 2")
            return False
        
        return True

    def validate_synergy_data(self, data_entry: dict[str, Any]) -> bool:
        """
        Validate synergy detection data quality.
        
        Args:
            data_entry: Synergy data entry
            
        Returns:
            True if data passes quality check
        """
        synergy = data_entry.get("synergy", {})
        
        if not synergy:
            logger.debug("Synergy validation failed: missing synergy dict")
            return False
        
        # Check confidence - support both 'confidence' and 'synergy_score' fields
        confidence = synergy.get("confidence") or synergy.get("synergy_score", 0.0)
        if confidence < self.min_synergy_confidence:
            logger.debug(f"Synergy validation failed: confidence {confidence} < {self.min_synergy_confidence}")
            return False
        
        # Check required fields - support both 'entity_1/entity_2' and 'device1/device2' formats
        entity_1 = synergy.get("entity_1") or synergy.get("device1")
        entity_2 = synergy.get("entity_2") or synergy.get("device2")
        if not entity_1 or not entity_2:
            logger.debug(f"Synergy validation failed: missing entities (entity_1/device1={entity_1}, entity_2/device2={entity_2})")
            return False
        
        return True

    def validate_suggestion_data(self, data_entry: dict[str, Any]) -> bool:
        """
        Validate suggestion generation data quality.
        
        Args:
            data_entry: Suggestion data entry
            
        Returns:
            True if data passes quality check
        """
        suggestion = data_entry.get("suggestion", {})
        
        if not suggestion:
            logger.debug("Suggestion validation failed: missing suggestion dict")
            return False
        
        # Check quality score (if available) - default to 1.0 if not present
        quality = suggestion.get("quality_score", 1.0)
        if quality < self.min_suggestion_quality:
            logger.debug(f"Suggestion validation failed: quality {quality} < {self.min_suggestion_quality}")
            return False
        
        # Check required fields - support both 'description' and 'text' fields
        description = suggestion.get("description") or suggestion.get("text")
        automation_type = suggestion.get("automation_type") or suggestion.get("type", "automation")
        
        if not description:
            logger.debug("Suggestion validation failed: missing description/text field")
            return False
        
        # automation_type is optional if we can infer it
        if not automation_type or automation_type == "":
            automation_type = "automation"  # Default value
        
        return True

    def validate_yaml_data(self, data_entry: dict[str, Any]) -> bool:
        """
        Validate YAML generation data quality.
        
        Args:
            data_entry: YAML data entry
            
        Returns:
            True if data passes quality check
        """
        yaml_pair = data_entry.get("yaml_pair", {})
        validation_result = data_entry.get("validation_result", {})
        
        if not yaml_pair:
            logger.debug("YAML validation failed: missing yaml_pair dict")
            return False
        
        # Check YAML validity if required
        if self.min_yaml_validity:
            is_valid = validation_result.get("is_valid", False)
            # Also check yaml_valid field (alternative name)
            if not is_valid:
                is_valid = validation_result.get("yaml_valid", False)
            if not is_valid:
                logger.debug("YAML validation failed: YAML not valid")
                return False
        
        # Check required fields - support both 'output' and 'yaml' field names
        yaml_input = yaml_pair.get("input")
        yaml_output = yaml_pair.get("output") or yaml_pair.get("yaml")
        
        if not yaml_input or not yaml_output:
            logger.debug(f"YAML validation failed: missing input/output (input={bool(yaml_input)}, output={bool(yaml_output)})")
            return False
        
        return True

    def validate_ask_ai_data(self, data_entry: dict[str, Any]) -> bool:
        """
        Validate Ask AI conversation data quality.
        
        Args:
            data_entry: Ask AI data entry
            
        Returns:
            True if data passes quality check
        """
        query = data_entry.get("query", "")
        response = data_entry.get("response", {})
        
        # Check query quality
        if not query or len(query.strip()) < 5:  # Minimum query length
            logger.debug(f"Ask AI validation failed: query too short (length={len(query.strip()) if query else 0})")
            return False
        
        # Check response quality
        if not response:
            logger.debug("Ask AI validation failed: missing response")
            return False
        
        # Check response has content - check multiple possible fields
        has_suggestion = bool(response.get("suggestion"))
        has_yaml = bool(response.get("yaml") or response.get("yaml_content"))
        has_steps = bool(response.get("steps"))  # Ask AI result has steps
        
        if not (has_suggestion or has_yaml or has_steps):
            logger.debug("Ask AI validation failed: response has no content (suggestion/yaml/steps)")
            return False
        
        return True

