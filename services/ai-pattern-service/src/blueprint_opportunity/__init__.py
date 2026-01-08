"""Blueprint Opportunity Engine - Proactive blueprint recommendations."""

from .opportunity_engine import BlueprintOpportunityEngine
from .device_matcher import DeviceMatcher
from .input_autofill import InputAutofill
from .schemas import (
    BlueprintOpportunity,
    DeviceSignature,
    AutofilledInput,
    BlueprintDeploymentPreview,
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
