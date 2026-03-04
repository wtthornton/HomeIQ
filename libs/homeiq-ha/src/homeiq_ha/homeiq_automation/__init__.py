"""
HomeIQ Automation JSON Format

Comprehensive JSON format for HomeIQ automations that extends beyond
Home Assistant YAML to include HomeIQ-specific metadata, patterns,
device context, and integration capabilities.
"""

from .schema import (
    DeviceContext,
    EnergyImpact,
    HomeIQAction,
    HomeIQAutomation,
    HomeIQCondition,
    HomeIQMetadata,
    HomeIQTrigger,
    PatternContext,
    SafetyChecks,
    TimeConstraints,
)

__all__ = [
    "HomeIQAutomation",
    "HomeIQMetadata",
    "HomeIQTrigger",
    "HomeIQCondition",
    "HomeIQAction",
    "PatternContext",
    "DeviceContext",
    "SafetyChecks",
    "EnergyImpact",
    "TimeConstraints",
]

