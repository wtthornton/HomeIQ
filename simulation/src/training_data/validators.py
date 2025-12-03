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
            return False
        
        # Check confidence
        confidence = pattern.get("confidence", 0.0)
        if confidence < self.min_pattern_confidence:
            return False
        
        # Check occurrences
        occurrences = pattern.get("occurrences", 0)
        if occurrences < 2:  # Minimum occurrences for pattern
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
            return False
        
        # Check confidence
        confidence = synergy.get("confidence", 0.0)
        if confidence < self.min_synergy_confidence:
            return False
        
        # Check required fields
        if not synergy.get("entity_1") or not synergy.get("entity_2"):
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
            return False
        
        # Check quality score (if available)
        quality = suggestion.get("quality_score", 1.0)
        if quality < self.min_suggestion_quality:
            return False
        
        # Check required fields
        if not suggestion.get("description") or not suggestion.get("automation_type"):
            return False
        
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
            return False
        
        # Check YAML validity if required
        if self.min_yaml_validity:
            is_valid = validation_result.get("is_valid", False)
            if not is_valid:
                return False
        
        # Check required fields
        if not yaml_pair.get("input") or not yaml_pair.get("output"):
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
            return False
        
        # Check response quality
        if not response:
            return False
        
        # Check response has content
        if not response.get("suggestion") and not response.get("yaml"):
            return False
        
        return True

