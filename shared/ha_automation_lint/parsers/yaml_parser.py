"""
YAML parser and normalizer for Home Assistant automations.
Converts raw YAML to internal representation (IR).
"""

import yaml
from typing import List, Dict, Any, Tuple, Optional
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import AutomationIR, TriggerIR, ConditionIR, ActionIR, Finding
from constants import Severity, RuleCategory


class YAMLParseError(Exception):
    """Raised when YAML cannot be parsed."""
    pass


class AutomationParser:
    """Parse and normalize automation YAML to IR."""

    def parse(self, yaml_content: str) -> Tuple[List[AutomationIR], List[Finding]]:
        """
        Parse YAML content and return normalized IR + parse errors.

        Args:
            yaml_content: Raw YAML string to parse

        Returns:
            Tuple of (automations list, parse findings list)
        """
        findings: List[Finding] = []

        # Step 1: Parse YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            findings.append(Finding(
                rule_id="PARSE001",
                severity=Severity.ERROR,
                message=f"Invalid YAML syntax: {str(e)}",
                why_it_matters="The automation YAML cannot be parsed and will not load in Home Assistant",
                path="root"
            ))
            return [], findings

        # Handle None/empty case
        if data is None:
            findings.append(Finding(
                rule_id="PARSE002",
                severity=Severity.ERROR,
                message="Empty YAML content",
                why_it_matters="No automation data found to lint",
                path="root"
            ))
            return [], findings

        # Step 2: Detect format and normalize to list
        automations_list = self._normalize_to_list(data, findings)

        # Step 3: Convert to IR
        ir_automations: List[AutomationIR] = []
        for idx, auto_dict in enumerate(automations_list):
            ir = self._dict_to_ir(auto_dict, idx, findings)
            if ir:
                ir_automations.append(ir)

        return ir_automations, findings

    def _normalize_to_list(self, data: Any, findings: List[Finding]) -> List[Dict[str, Any]]:
        """
        Normalize various formats to a list of automation dicts.

        Args:
            data: Parsed YAML data
            findings: List to append parse findings to

        Returns:
            List of automation dictionaries
        """
        if isinstance(data, dict):
            # Check if it's a single automation or a package format
            if "trigger" in data or "action" in data:
                # Single automation
                return [data]
            else:
                # Package format or unknown
                findings.append(Finding(
                    rule_id="PARSE003",
                    severity=Severity.WARN,
                    message="Expected automation format, got dict without trigger/action",
                    why_it_matters="This may be a package format or invalid structure",
                    path="root"
                ))
                return []
        elif isinstance(data, list):
            return data
        else:
            findings.append(Finding(
                rule_id="PARSE004",
                severity=Severity.ERROR,
                message=f"Expected dict or list, got {type(data).__name__}",
                why_it_matters="Automation YAML must be a dictionary or list",
                path="root"
            ))
            return []

    def _dict_to_ir(
        self,
        data: Any,
        index: int,
        findings: List[Finding]
    ) -> Optional[AutomationIR]:
        """
        Convert a single automation dict to IR.

        Args:
            data: Automation dictionary
            index: Index in the list of automations
            findings: List to append findings to

        Returns:
            AutomationIR object or None if conversion failed
        """
        if not isinstance(data, dict):
            findings.append(Finding(
                rule_id="PARSE005",
                severity=Severity.ERROR,
                message=f"Automation {index} is not a dictionary",
                why_it_matters="Each automation must be a YAML dictionary",
                path=f"automations[{index}]"
            ))
            return None

        ir = AutomationIR(
            id=data.get("id"),
            alias=data.get("alias"),
            description=data.get("description"),
            mode=data.get("mode", "single"),
            variables=data.get("variables", {}),
            source_index=index,
            raw_source=data,
            path=f"automations[{index}]"
        )

        # Parse triggers
        triggers = data.get("trigger", [])
        if not isinstance(triggers, list):
            triggers = [triggers]
        ir.trigger = [
            TriggerIR(
                platform=t.get("platform", "unknown") if isinstance(t, dict) else "unknown",
                raw=t if isinstance(t, dict) else {},
                path=f"{ir.path}.trigger[{i}]"
            )
            for i, t in enumerate(triggers)
        ]

        # Parse conditions
        conditions = data.get("condition", [])
        if not isinstance(conditions, list):
            conditions = [conditions]
        ir.condition = [
            ConditionIR(
                condition=c.get("condition", "unknown") if isinstance(c, dict) else "unknown",
                raw=c if isinstance(c, dict) else {},
                path=f"{ir.path}.condition[{i}]"
            )
            for i, c in enumerate(conditions)
        ]

        # Parse actions
        actions = data.get("action", [])
        if not isinstance(actions, list):
            actions = [actions]
        ir.action = [
            ActionIR(
                service=a.get("service") if isinstance(a, dict) else None,
                raw=a if isinstance(a, dict) else {},
                path=f"{ir.path}.action[{i}]"
            )
            for i, a in enumerate(actions)
        ]

        return ir
