"""
Blueprint Analytics Module

Tracks blueprint deployments, success rates, and user engagement
to achieve the target metrics from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md:
- 30% automation adoption rate
- 85% automation success rate
- 90% pattern quality
- 4.0+ user satisfaction
"""

from .blueprint_analytics import BlueprintAnalytics, DeploymentMetric
from .metrics_collector import MetricsCollector

__all__ = [
    "BlueprintAnalytics",
    "DeploymentMetric",
    "MetricsCollector",
]
