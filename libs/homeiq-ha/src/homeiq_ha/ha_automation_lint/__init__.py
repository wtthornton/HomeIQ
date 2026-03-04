"""
Home Assistant Automation Linter - Shared Module

This module provides lint and auto-fix capabilities for Home Assistant automation YAML.
"""

from .constants import ENGINE_VERSION, RULESET_VERSION, FixMode, RuleCategory, Severity
from .engine import LintEngine
from .fixers.auto_fixer import AutoFixer
from .models import (
    ActionIR,
    AutomationIR,
    ConditionIR,
    Finding,
    LintReport,
    PatchOperation,
    SuggestedFix,
    TriggerIR,
)
from .parsers.yaml_parser import AutomationParser
from .renderers.yaml_renderer import YAMLRenderer

__version__ = ENGINE_VERSION

__all__ = [
    # Constants
    "ENGINE_VERSION",
    "RULESET_VERSION",
    "Severity",
    "RuleCategory",
    "FixMode",

    # Models
    "AutomationIR",
    "TriggerIR",
    "ConditionIR",
    "ActionIR",
    "Finding",
    "LintReport",
    "SuggestedFix",
    "PatchOperation",

    # Core classes
    "LintEngine",
    "AutomationParser",
    "YAMLRenderer",
    "AutoFixer",
]
