"""Contract definitions for AI Automation Service"""

from .models import (
    AutomationPlan,
    AutomationMetadata,
    Trigger,
    Condition,
    Action,
    AutomationMode,
    MaxExceeded
)

__all__ = [
    "AutomationPlan",
    "AutomationMetadata",
    "Trigger",
    "Condition",
    "Action",
    "AutomationMode",
    "MaxExceeded"
]

