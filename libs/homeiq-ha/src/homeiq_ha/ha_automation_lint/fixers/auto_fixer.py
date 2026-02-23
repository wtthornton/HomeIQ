"""
Auto-fix engine for applying safe, deterministic fixes.
"""

from typing import List, Tuple
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Finding, PatchOperation, AutomationIR
from constants import FixMode


class AutoFixer:
    """Apply safe auto-fixes to automations."""

    def __init__(self, fix_mode: str = FixMode.SAFE):
        """
        Initialize auto-fixer with fix mode.

        Args:
            fix_mode: Fix mode (none, safe, opinionated)
        """
        self.fix_mode = fix_mode

    def apply_fixes(
        self,
        automations: List[AutomationIR],
        findings: List[Finding]
    ) -> Tuple[List[AutomationIR], List[str]]:
        """
        Apply auto-fixes to automations based on findings.

        Args:
            automations: List of automation IRs
            findings: List of findings from linting

        Returns:
            Tuple of (fixed_automations, applied_rule_ids)
        """
        if self.fix_mode == FixMode.NONE:
            return automations, []

        applied_fixes = []
        fixed_automations = [auto for auto in automations]  # Shallow copy for now

        # MVP: Only implement safe fixes for MAINTAINABILITY001 and MAINTAINABILITY002
        for finding in findings:
            if finding.suggested_fix and finding.suggested_fix.type == "auto":
                # Apply simple fixes
                fix_applied = self._apply_simple_fix(fixed_automations, finding)
                if fix_applied:
                    applied_fixes.append(finding.rule_id)

        return fixed_automations, applied_fixes

    def _apply_simple_fix(
        self,
        automations: List[AutomationIR],
        finding: Finding
    ) -> bool:
        """
        Apply a simple fix to automations.

        Args:
            automations: List of automation IRs to modify
            finding: Finding with suggested fix

        Returns:
            True if fix was applied, False otherwise
        """
        # Extract automation index from path (e.g., "automations[0]" -> 0)
        try:
            path_parts = finding.path.split("[")
            if len(path_parts) > 1:
                index = int(path_parts[1].rstrip("]"))
                if 0 <= index < len(automations):
                    automation = automations[index]

                    # Apply specific fixes based on rule ID
                    if finding.rule_id == "MAINTAINABILITY001":
                        # Add missing description
                        if not automation.description:
                            automation.description = ""
                            automation.raw_source["description"] = ""
                            return True

                    elif finding.rule_id == "MAINTAINABILITY002":
                        # Add missing alias
                        if not automation.alias:
                            automation.alias = ""
                            automation.raw_source["alias"] = ""
                            return True

        except (ValueError, IndexError):
            pass

        return False

    def _apply_patch(self, automations: List[AutomationIR], patch: PatchOperation) -> bool:
        """
        Apply a single patch operation.

        Args:
            automations: List of automation IRs
            patch: Patch operation to apply

        Returns:
            True if patch was applied, False otherwise

        Note:
            This is a placeholder for future implementation.
            Full JSONPath-based patching will be implemented in Phase 1.
        """
        # TODO: Implement full JSONPath-based patching
        # For MVP, we use simple fixes in _apply_simple_fix
        return False
