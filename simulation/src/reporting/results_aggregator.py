"""
Results Aggregator

Comprehensive results aggregation for simulation framework.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class ResultsAggregator:
    """
    Results aggregator for simulation framework.
    
    Aggregates results from:
    - 3 AM workflow simulations
    - Ask AI flow simulations
    - Metrics collection
    - Validation results
    """

    def __init__(self):
        """Initialize results aggregator."""
        self.results: dict[str, Any] = {
            "3am_workflows": [],
            "ask_ai_queries": [],
            "metrics": {},
            "validation": {}
        }
        
        logger.info("ResultsAggregator initialized")

    def add_3am_result(self, result: dict[str, Any]) -> None:
        """
        Add 3 AM workflow result.
        
        Args:
            result: 3 AM workflow result dictionary
        """
        self.results["3am_workflows"].append(result)

    def add_ask_ai_result(self, result: dict[str, Any]) -> None:
        """
        Add Ask AI query result.
        
        Args:
            result: Ask AI query result dictionary
        """
        self.results["ask_ai_queries"].append(result)

    def add_metrics(self, metrics: dict[str, Any]) -> None:
        """
        Add metrics.
        
        Args:
            metrics: Metrics dictionary
        """
        self.results["metrics"] = metrics

    def add_validation_result(self, validation_type: str, result: dict[str, Any]) -> None:
        """
        Add validation result.
        
        Args:
            validation_type: Validation type ("prompt" or "yaml")
            result: Validation result dictionary
        """
        if validation_type not in self.results["validation"]:
            self.results["validation"][validation_type] = []
        
        self.results["validation"][validation_type].append(result)

    def get_summary(self) -> dict[str, Any]:
        """
        Get aggregated summary.
        
        Returns:
            Summary dictionary
        """
        # Calculate 3 AM workflow statistics
        total_3am = len(self.results["3am_workflows"])
        successful_3am = sum(1 for r in self.results["3am_workflows"] if r.get("status") == "success")
        failed_3am = total_3am - successful_3am
        
        avg_duration_3am = 0.0
        if successful_3am > 0:
            durations = [
                r.get("duration_seconds", 0)
                for r in self.results["3am_workflows"]
                if r.get("status") == "success"
            ]
            avg_duration_3am = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate Ask AI query statistics
        total_ask_ai = len(self.results["ask_ai_queries"])
        successful_ask_ai = sum(1 for r in self.results["ask_ai_queries"] if r.get("status") == "success")
        failed_ask_ai = total_ask_ai - successful_ask_ai
        
        avg_duration_ask_ai = 0.0
        if successful_ask_ai > 0:
            durations = [
                r.get("duration_seconds", 0)
                for r in self.results["ask_ai_queries"]
                if r.get("status") == "success"
            ]
            avg_duration_ask_ai = sum(durations) / len(durations) if durations else 0.0
        
        # Calculate validation statistics
        validation_stats = {}
        for validation_type, results in self.results["validation"].items():
            total = len(results)
            valid = sum(1 for r in results if r.get("is_valid", False))
            invalid = total - valid
            
            validation_stats[validation_type] = {
                "total": total,
                "valid": valid,
                "invalid": invalid,
                "validity_rate": valid / total if total > 0 else 0.0
            }
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "3am_workflows": {
                "total": total_3am,
                "successful": successful_3am,
                "failed": failed_3am,
                "success_rate": successful_3am / total_3am if total_3am > 0 else 0.0,
                "avg_duration_seconds": avg_duration_3am
            },
            "ask_ai_queries": {
                "total": total_ask_ai,
                "successful": successful_ask_ai,
                "failed": failed_ask_ai,
                "success_rate": successful_ask_ai / total_ask_ai if total_ask_ai > 0 else 0.0,
                "avg_duration_seconds": avg_duration_ask_ai
            },
            "validation": validation_stats,
            "metrics": self.results["metrics"]
        }

    def clear(self) -> None:
        """Clear all results."""
        self.results = {
            "3am_workflows": [],
            "ask_ai_queries": [],
            "metrics": {},
            "validation": {}
        }

