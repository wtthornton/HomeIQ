"""Blueprint Opportunity Engine - Proactive blueprint recommendations."""

from .device_matcher import DeviceMatcher
from .input_autofill import InputAutofill
from .opportunity_engine import BlueprintOpportunityEngine
from .schemas import (
    AutofilledInput,
    BlueprintDeploymentPreview,
    BlueprintOpportunity,
    DeviceSignature,
)

__all__ = [
    "BlueprintOpportunityEngine",
    "DeviceMatcher",
    "InputAutofill",
    "BlueprintOpportunity",
    "DeviceSignature",
    "AutofilledInput",
    "BlueprintDeploymentPreview",
]
