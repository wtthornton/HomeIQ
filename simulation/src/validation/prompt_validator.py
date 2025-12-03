"""
Prompt Validator

Prompt generation and validation framework.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PromptValidator:
    """
    Prompt validator for simulation framework.
    
    Validates:
    - Prompt structure
    - Prompt completeness
    - Prompt quality
    """

    def __init__(self):
        """Initialize prompt validator."""
        logger.info("PromptValidator initialized")

    def validate_prompt(
        self,
        prompt_dict: dict[str, Any],
        expected_keys: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Validate prompt structure and completeness.
        
        Args:
            prompt_dict: Prompt dictionary
            expected_keys: Expected keys in prompt (default: ["system_prompt", "user_prompt"])
            
        Returns:
            Validation result dictionary
        """
        expected_keys = expected_keys or ["system_prompt", "user_prompt"]
        
        errors = []
        warnings = []
        
        # Check required keys
        for key in expected_keys:
            if key not in prompt_dict:
                errors.append(f"Missing required key: {key}")
            elif not prompt_dict[key] or not isinstance(prompt_dict[key], str):
                errors.append(f"Invalid value for key: {key}")
        
        # Check prompt length
        for key in expected_keys:
            if key in prompt_dict:
                prompt_text = prompt_dict[key]
                if len(prompt_text) < 10:
                    warnings.append(f"Prompt {key} is very short ({len(prompt_text)} chars)")
                if len(prompt_text) > 10000:
                    warnings.append(f"Prompt {key} is very long ({len(prompt_text)} chars)")
        
        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }

    def validate_prompt_quality(
        self,
        prompt_dict: dict[str, Any],
        ground_truth: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Validate prompt quality against ground truth.
        
        Args:
            prompt_dict: Prompt dictionary
            ground_truth: Optional ground truth for comparison
            
        Returns:
            Quality metrics dictionary
        """
        metrics = {
            "system_prompt_length": len(prompt_dict.get("system_prompt", "")),
            "user_prompt_length": len(prompt_dict.get("user_prompt", "")),
            "total_length": sum(len(v) for v in prompt_dict.values() if isinstance(v, str))
        }
        
        if ground_truth:
            # Compare with ground truth
            similarity_score = self._calculate_similarity(prompt_dict, ground_truth)
            metrics["similarity_score"] = similarity_score
        
        return metrics

    def _calculate_similarity(
        self,
        prompt_dict: dict[str, Any],
        ground_truth: dict[str, Any]
    ) -> float:
        """
        Calculate similarity between prompt and ground truth.
        
        Simple word overlap similarity for now.
        """
        # Simple word overlap
        prompt_words = set()
        for value in prompt_dict.values():
            if isinstance(value, str):
                prompt_words.update(value.lower().split())
        
        ground_truth_words = set()
        for value in ground_truth.values():
            if isinstance(value, str):
                ground_truth_words.update(value.lower().split())
        
        if not ground_truth_words:
            return 0.0
        
        overlap = len(prompt_words & ground_truth_words)
        return overlap / len(ground_truth_words)

