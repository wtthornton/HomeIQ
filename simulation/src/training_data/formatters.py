"""
Data Formatters

Format conversion utilities for training data.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class DataFormatter:
    """
    Data formatter for converting between formats.
    """

    @staticmethod
    def format_for_gnn_synergy(data: dict[str, Any]) -> dict[str, Any]:
        """
        Format data for GNN synergy training.
        
        Args:
            data: Raw synergy data
            
        Returns:
            Formatted data for GNN training
        """
        synergy = data.get("synergy", {})
        return {
            "source": synergy.get("entity_1"),
            "target": synergy.get("entity_2"),
            "edge_type": synergy.get("synergy_type", "co_activation"),
            "weight": synergy.get("confidence", 0.0)
        }

    @staticmethod
    def format_for_soft_prompt(data: dict[str, Any]) -> dict[str, Any]:
        """
        Format data for Soft Prompt training.
        
        Args:
            data: Raw suggestion data
            
        Returns:
            Formatted data for Soft Prompt training
        """
        suggestion = data.get("suggestion", {})
        prompt = data.get("prompt", {})
        return {
            "input": prompt.get("user_prompt", ""),
            "output": suggestion.get("description", ""),
            "label": suggestion.get("automation_type", "")
        }

    @staticmethod
    def format_for_pattern_detection(data: dict[str, Any]) -> dict[str, Any]:
        """
        Format data for pattern detection training.
        
        Args:
            data: Raw pattern data
            
        Returns:
            Formatted data for pattern detection training
        """
        pattern = data.get("pattern", {})
        return {
            "entity_id": pattern.get("entity_id"),
            "pattern": pattern.get("pattern_type", ""),
            "features": {
                "confidence": pattern.get("confidence", 0.0),
                "occurrences": pattern.get("occurrences", 0)
            },
            "label": pattern.get("pattern_type", "")
        }

