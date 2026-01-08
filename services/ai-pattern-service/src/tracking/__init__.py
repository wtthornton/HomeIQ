"""
Automation Execution Tracking Module

Monitors Home Assistant automation executions to track success rates.
Integrates with analytics and rating services for continuous improvement.

Target: 85% automation success rate
"""

from .execution_tracker import ExecutionTracker, ExecutionRecord
from .ha_event_subscriber import HAEventSubscriber

__all__ = [
    "ExecutionTracker",
    "ExecutionRecord",
    "HAEventSubscriber",
]
