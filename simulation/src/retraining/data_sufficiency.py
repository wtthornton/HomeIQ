"""
Data Sufficiency Checker

Check if sufficient training data is available for model retraining.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataSufficiencyChecker:
    """
    Data sufficiency checker for model retraining.
    
    Checks:
    - Minimum data volume per model type
    - Data quality thresholds
    - Data diversity requirements
    """

    def __init__(
        self,
        min_gnn_samples: int = 100,
        min_soft_prompt_samples: int = 50,
        min_pattern_samples: int = 200,
        min_yaml_samples: int = 100
    ):
        """
        Initialize data sufficiency checker.
        
        Args:
            min_gnn_samples: Minimum GNN synergy samples
            min_soft_prompt_samples: Minimum Soft Prompt samples
            min_pattern_samples: Minimum pattern detection samples
            min_yaml_samples: Minimum YAML generation samples
        """
        self.min_samples = {
            "gnn_synergy": min_gnn_samples,
            "soft_prompt": min_soft_prompt_samples,
            "pattern_detection": min_pattern_samples,
            "yaml_generation": min_yaml_samples
        }
        
        logger.info("DataSufficiencyChecker initialized")

    def check_sufficiency(
        self,
        model_type: str,
        data_count: int,
        quality_metrics: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """
        Check if data is sufficient for model retraining.
        
        Args:
            model_type: Model type (gnn_synergy, soft_prompt, etc.)
            data_count: Number of data samples
            quality_metrics: Quality metrics dictionary
            
        Returns:
            (is_sufficient, reason_message)
        """
        min_samples = self.min_samples.get(model_type, 0)
        
        if data_count < min_samples:
            return False, f"Insufficient data: {data_count} < {min_samples} (minimum)"
        
        # Check quality if provided
        if quality_metrics:
            quality_score = quality_metrics.get("quality_score", 1.0)
            if quality_score < 0.7:  # Minimum quality threshold
                return False, f"Low data quality: {quality_score} < 0.7"
        
        return True, f"Sufficient data: {data_count} >= {min_samples}"

    def check_all_models(
        self,
        data_counts: dict[str, int],
        quality_metrics: dict[str, dict[str, Any]] | None = None
    ) -> dict[str, tuple[bool, str]]:
        """
        Check sufficiency for all model types.
        
        Args:
            data_counts: Dictionary of model_type -> data_count
            quality_metrics: Dictionary of model_type -> quality_metrics
            
        Returns:
            Dictionary of model_type -> (is_sufficient, reason)
        """
        results = {}
        
        for model_type in self.min_samples.keys():
            data_count = data_counts.get(model_type, 0)
            quality = quality_metrics.get(model_type) if quality_metrics else None
            
            results[model_type] = self.check_sufficiency(
                model_type,
                data_count,
                quality
            )
        
        return results

