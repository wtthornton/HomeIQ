"""
Shared Prompt Guidance System

Provides consistent LLM prompt guidance across all HomeIQ services.
Ensures all services understand that HomeIQ creates automations (not "Home Assistant automations"),
uses HomeIQ JSON format as the standard, and Home Assistant YAML is only for deployment.
"""

from .builder import PromptBuilder
from .core_principles import (
    AUTOMATION_CREATION_FLOW,
    AUTOMATION_FORMAT_STANDARD,
    CORE_IDENTITY,
)

__all__ = [
    "PromptBuilder",
    "CORE_IDENTITY",
    "AUTOMATION_FORMAT_STANDARD",
    "AUTOMATION_CREATION_FLOW",
]
