"""Contract definitions for AI Automation Service"""

from .models import (
    Action,
    AutomationMetadata,
    AutomationMode,
    AutomationPlan,
    Condition,
    MaxExceeded,
    Trigger,
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

