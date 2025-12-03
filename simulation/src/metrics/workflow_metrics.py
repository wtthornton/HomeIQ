"""
Workflow Metrics

Workflow-specific metrics for 3 AM and Ask AI flows.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class WorkflowMetrics:
    """
    Workflow-specific metrics collector.
    
    Collects metrics for:
    - 3 AM workflow (6 phases)
    - Ask AI flow (query processing, YAML generation)
    """

    def __init__(self, collector: Any):  # MetricsCollector
        """
        Initialize workflow metrics.
        
        Args:
            collector: MetricsCollector instance
        """
        self.collector = collector
        
    def record_3am_phase(
        self,
        home_id: str,
        phase: int,
        phase_name: str,
        duration: float,
        results: dict[str, Any] | None = None
    ) -> None:
        """
        Record 3 AM workflow phase metrics.
        
        Args:
            home_id: Home identifier
            phase: Phase number (1-6)
            phase_name: Phase name
            duration: Phase duration in seconds
            results: Phase results
        """
        self.collector.record_workflow_metric(
            workflow_type="3am",
            home_id=home_id,
            metric_name=f"phase_{phase}_{phase_name}",
            value=duration,
            metadata={
                "phase": phase,
                "phase_name": phase_name,
                "results": results or {}
            }
        )

    def record_ask_ai_query(
        self,
        home_id: str,
        query: str,
        duration: float,
        suggestions_count: int,
        yaml_generated: bool = False,
        yaml_valid: bool = False
    ) -> None:
        """
        Record Ask AI query metrics.
        
        Args:
            home_id: Home identifier
            query: User query
            duration: Query processing duration in seconds
            suggestions_count: Number of suggestions generated
            yaml_generated: Whether YAML was generated
            yaml_valid: Whether YAML is valid
        """
        self.collector.record_workflow_metric(
            workflow_type="ask_ai",
            home_id=home_id,
            metric_name="query",
            value=duration,
            metadata={
                "query": query,
                "suggestions_count": suggestions_count,
                "yaml_generated": yaml_generated,
                "yaml_valid": yaml_valid
            }
        )

