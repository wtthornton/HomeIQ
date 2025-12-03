"""
Training Data Collector

Collect training data from all simulation collection points.
"""

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .validators import DataQualityValidator

logger = logging.getLogger(__name__)


class TrainingDataCollector:
    """
    Training data collector for simulation framework.
    
    Collects data from:
    - Pattern detection (patterns, ground truth, metrics)
    - Synergy detection (synergies, relationships, predictions)
    - Suggestion generation (suggestions, prompts, responses)
    - YAML generation (YAML pairs, validation results, ground truth)
    - Ask AI conversation (queries, responses, approvals)
    """

    def __init__(self, quality_validator: DataQualityValidator | None = None):
        """
        Initialize training data collector.
        
        Args:
            quality_validator: Data quality validator instance
        """
        self.quality_validator = quality_validator or DataQualityValidator()
        self.collected_data: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.collection_stats: dict[str, Any] = {
            "total_collected": 0,
            "total_filtered": 0,
            "by_type": defaultdict(int)
        }
        
        logger.info("TrainingDataCollector initialized")

    def collect_pattern_data(
        self,
        pattern: dict[str, Any],
        ground_truth: dict[str, Any] | None = None,
        metrics: dict[str, Any] | None = None
    ) -> bool:
        """
        Collect pattern detection data.
        
        Args:
            pattern: Detected pattern dictionary
            ground_truth: Ground truth pattern (if available)
            metrics: Pattern detection metrics
            
        Returns:
            True if collected (passed quality check), False if filtered
        """
        data_entry = {
            "type": "pattern_detection",
            "pattern": pattern,
            "ground_truth": ground_truth,
            "metrics": metrics,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Validate quality
        if not self.quality_validator.validate_pattern_data(data_entry):
            self.collection_stats["total_filtered"] += 1
            logger.debug("Pattern data filtered (quality check failed)")
            return False
        
        self.collected_data["pattern_detection"].append(data_entry)
        self.collection_stats["total_collected"] += 1
        self.collection_stats["by_type"]["pattern_detection"] += 1
        
        logger.debug("Pattern data collected")
        return True

    def collect_synergy_data(
        self,
        synergy: dict[str, Any],
        relationship: dict[str, Any] | None = None,
        prediction: dict[str, Any] | None = None
    ) -> bool:
        """
        Collect synergy detection data.
        
        Args:
            synergy: Detected synergy dictionary
            relationship: Device relationship data
            prediction: Model prediction data
            
        Returns:
            True if collected, False if filtered
        """
        data_entry = {
            "type": "synergy_detection",
            "synergy": synergy,
            "relationship": relationship,
            "prediction": prediction,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if not self.quality_validator.validate_synergy_data(data_entry):
            self.collection_stats["total_filtered"] += 1
            logger.debug("Synergy data filtered (quality check failed)")
            return False
        
        self.collected_data["synergy_detection"].append(data_entry)
        self.collection_stats["total_collected"] += 1
        self.collection_stats["by_type"]["synergy_detection"] += 1
        
        logger.debug("Synergy data collected")
        return True

    def collect_suggestion_data(
        self,
        suggestion: dict[str, Any],
        prompt: dict[str, Any] | None = None,
        response: dict[str, Any] | None = None
    ) -> bool:
        """
        Collect suggestion generation data.
        
        Args:
            suggestion: Generated suggestion dictionary
            prompt: Prompt used for generation
            response: LLM response data
            
        Returns:
            True if collected, False if filtered
        """
        data_entry = {
            "type": "suggestion_generation",
            "suggestion": suggestion,
            "prompt": prompt,
            "response": response,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if not self.quality_validator.validate_suggestion_data(data_entry):
            self.collection_stats["total_filtered"] += 1
            logger.debug("Suggestion data filtered (quality check failed)")
            return False
        
        self.collected_data["suggestion_generation"].append(data_entry)
        self.collection_stats["total_collected"] += 1
        self.collection_stats["by_type"]["suggestion_generation"] += 1
        
        logger.debug("Suggestion data collected")
        return True

    def collect_yaml_data(
        self,
        yaml_pair: dict[str, Any],
        validation_result: dict[str, Any] | None = None,
        ground_truth: dict[str, Any] | None = None
    ) -> bool:
        """
        Collect YAML generation data.
        
        Args:
            yaml_pair: YAML input/output pair
            validation_result: YAML validation result
            ground_truth: Ground truth YAML (if available)
            
        Returns:
            True if collected, False if filtered
        """
        data_entry = {
            "type": "yaml_generation",
            "yaml_pair": yaml_pair,
            "validation_result": validation_result,
            "ground_truth": ground_truth,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if not self.quality_validator.validate_yaml_data(data_entry):
            self.collection_stats["total_filtered"] += 1
            logger.debug("YAML data filtered (quality check failed)")
            return False
        
        self.collected_data["yaml_generation"].append(data_entry)
        self.collection_stats["total_collected"] += 1
        self.collection_stats["by_type"]["yaml_generation"] += 1
        
        logger.debug("YAML data collected")
        return True

    def collect_ask_ai_data(
        self,
        query: str,
        response: dict[str, Any],
        approval: bool | None = None
    ) -> bool:
        """
        Collect Ask AI conversation data.
        
        Args:
            query: User query string
            response: AI response dictionary
            approval: User approval status (if available)
            
        Returns:
            True if collected, False if filtered
        """
        data_entry = {
            "type": "ask_ai_conversation",
            "query": query,
            "response": response,
            "approval": approval,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        if not self.quality_validator.validate_ask_ai_data(data_entry):
            self.collection_stats["total_filtered"] += 1
            logger.debug("Ask AI data filtered (quality check failed)")
            return False
        
        self.collected_data["ask_ai_conversation"].append(data_entry)
        self.collection_stats["total_collected"] += 1
        self.collection_stats["by_type"]["ask_ai_conversation"] += 1
        
        logger.debug("Ask AI data collected")
        return True

    def get_collected_data(self, data_type: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        """
        Get collected data.
        
        Args:
            data_type: Data type to retrieve (None for all)
            
        Returns:
            Collected data dictionary or list
        """
        if data_type:
            return self.collected_data.get(data_type, [])
        else:
            return dict(self.collected_data)

    def get_collection_stats(self) -> dict[str, Any]:
        """
        Get collection statistics.
        
        Returns:
            Collection statistics dictionary
        """
        return {
            **self.collection_stats,
            "by_type": dict(self.collection_stats["by_type"])
        }

    def clear_collected_data(self) -> None:
        """Clear all collected data."""
        self.collected_data.clear()
        self.collection_stats = {
            "total_collected": 0,
            "total_filtered": 0,
            "by_type": defaultdict(int)
        }
        logger.info("Collected data cleared")

