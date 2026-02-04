"""
Home Assistant Automation Linter - Shared Module

This module provides lint and auto-fix capabilities for Home Assistant automation YAML.
"""

from .constants import ENGINE_VERSION, RULESET_VERSION, Severity, RuleCategory, FixMode
from .models import (
    AutomationIR,
    TriggerIR,
    ConditionIR,
    ActionIR,
    Finding,
    LintReport,
    SuggestedFix,
    PatchOperation
)
from .engine import LintEngine
from .parsers.yaml_parser import AutomationParser
from .renderers.yaml_renderer import YAMLRenderer
from .fixers.auto_fixer import AutoFixer

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
