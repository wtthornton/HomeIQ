"""
Prompt templates for HomeIQ automation system.
"""

from .automation_generation import AUTOMATION_GENERATION_SYSTEM_PROMPT
from .suggestion_generation import SUGGESTION_GENERATION_SYSTEM_PROMPT
from .yaml_generation import YAML_GENERATION_SYSTEM_PROMPT

__all__ = [
    "AUTOMATION_GENERATION_SYSTEM_PROMPT",
    "SUGGESTION_GENERATION_SYSTEM_PROMPT",
    "YAML_GENERATION_SYSTEM_PROMPT",
]
