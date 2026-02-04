"""
Internal Representation (IR) models for automation linting.
All lint operations work on these normalized models, not raw YAML.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class TriggerIR:
    """Normalized trigger representation."""
    platform: str
    raw: Dict[str, Any]
    path: str  # JSONPath location in source


@dataclass
class ConditionIR:
    """Normalized condition representation."""
    condition: str
    raw: Dict[str, Any]
    path: str


@dataclass
class ActionIR:
    """Normalized action representation."""
    service: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)
    path: str = ""


@dataclass
class AutomationIR:
    """Normalized automation representation."""
    id: Optional[str] = None
    alias: Optional[str] = None
    description: Optional[str] = None
    trigger: List[TriggerIR] = field(default_factory=list)
    condition: List[ConditionIR] = field(default_factory=list)
    action: List[ActionIR] = field(default_factory=list)
    mode: str = "single"  # Default mode
    variables: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    source_index: int = 0  # Position in original list
    raw_source: Dict[str, Any] = field(default_factory=dict)
    path: str = "automations[0]"  # JSONPath location


@dataclass
class PatchOperation:
    """Represents a single fix operation."""
    op: str  # add, remove, replace, move
    path: str  # JSONPath location
    value: Any = None


@dataclass
class SuggestedFix:
    """Represents a suggested fix for a finding."""
    type: str  # "auto" or "manual"
    summary: str
    patch_ops: List[PatchOperation] = field(default_factory=list)


@dataclass
class Finding:
    """A lint finding (error, warning, or info)."""
    rule_id: str
    severity: str  # error, warn, info
    message: str
    why_it_matters: str
    path: str  # JSONPath location
    suggested_fix: Optional[SuggestedFix] = None


@dataclass
class LintReport:
    """Complete lint report for a set of automations."""
    engine_version: str
    ruleset_version: str
    automations_detected: int
    findings: List[Finding] = field(default_factory=list)

    @property
    def errors_count(self) -> int:
        """Count findings with error severity."""
        return sum(1 for f in self.findings if f.severity == "error")

    @property
    def warnings_count(self) -> int:
        """Count findings with warning severity."""
        return sum(1 for f in self.findings if f.severity == "warn")

    @property
    def info_count(self) -> int:
        """Count findings with info severity."""
        return sum(1 for f in self.findings if f.severity == "info")
