"""
Render IR back to stable, formatted YAML.
"""

import yaml
from typing import List, Dict, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import AutomationIR


class YAMLRenderer:
    """Render AutomationIR back to YAML string."""

    def render(self, automations: List[AutomationIR]) -> str:
        """
        Render list of AutomationIR to formatted YAML.

        Args:
            automations: List of automation IRs to render

        Returns:
            Stable, deterministic YAML output
        """
        # Convert IR back to dicts
        automation_dicts = [self._ir_to_dict(auto) for auto in automations]

        # Render to YAML with consistent formatting
        if len(automation_dicts) == 1:
            output = yaml.dump(
                automation_dicts[0],
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=120,  # Reasonable line width
                indent=2
            )
        else:
            output = yaml.dump(
                automation_dicts,
                default_flow_style=False,
                sort_keys=False,
                allow_unicode=True,
                width=120,
                indent=2
            )

        return output

    def _ir_to_dict(self, ir: AutomationIR) -> Dict[str, Any]:
        """
        Convert AutomationIR back to dict format.

        Args:
            ir: Automation IR to convert

        Returns:
            Dictionary representation of the automation
        """
        result: Dict[str, Any] = {}

        # Add fields in conventional order
        if ir.id:
            result["id"] = ir.id

        if ir.alias:
            result["alias"] = ir.alias

        if ir.description:
            result["description"] = ir.description

        # Trigger (required)
        result["trigger"] = [t.raw for t in ir.trigger]

        # Condition (optional)
        if ir.condition:
            result["condition"] = [c.raw for c in ir.condition]

        # Action (required)
        result["action"] = [a.raw for a in ir.action]

        # Mode (only if not default)
        if ir.mode != "single":
            result["mode"] = ir.mode

        # Variables (optional)
        if ir.variables:
            result["variables"] = ir.variables

        # Preserve any other keys from raw_source that we don't explicitly handle
        for key, value in ir.raw_source.items():
            if key not in result and key not in {"trigger", "condition", "action"}:
                result[key] = value

        return result

    def create_diff_summary(self, original: str, fixed: str) -> str:
        """
        Create a human-readable diff summary.

        Args:
            original: Original YAML string
            fixed: Fixed YAML string

        Returns:
            Diff summary string
        """
        # Simple line-based diff for MVP
        original_lines = original.strip().split('\n')
        fixed_lines = fixed.strip().split('\n')

        if original_lines == fixed_lines:
            return "No changes"

        changes = abs(len(fixed_lines) - len(original_lines))
        return f"Modified {changes} lines"
