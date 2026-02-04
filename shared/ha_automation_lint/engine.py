"""
Core lint engine that orchestrates parsing, rule checking, and fixing.
"""

from typing import List, Dict, Optional
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from models import AutomationIR, Finding, LintReport
from parsers.yaml_parser import AutomationParser
from rules.mvp_rules import get_all_rules
from constants import ENGINE_VERSION, RULESET_VERSION, Severity


class LintEngine:
    """Main lint engine for HA automations."""

    def __init__(self, rule_config: Optional[Dict[str, bool]] = None):
        """
        Initialize engine with optional rule configuration.

        Args:
            rule_config: Dict of rule_id -> enabled (True/False)
        """
        self.parser = AutomationParser()
        self.rules = get_all_rules()

        # Apply rule configuration
        if rule_config:
            for rule in self.rules:
                if rule.rule_id in rule_config:
                    rule.enabled = rule_config[rule.rule_id]

    def lint(self, yaml_content: str, strict: bool = False) -> LintReport:
        """
        Lint automation YAML and return findings.

        Args:
            yaml_content: Raw YAML string
            strict: If True, treat warnings as errors

        Returns:
            LintReport with all findings
        """
        # Parse YAML to IR
        automations, parse_findings = self.parser.parse(yaml_content)

        # Check rules
        all_findings = parse_findings.copy()

        # First, check for duplicate IDs across all automations
        all_findings.extend(self._check_duplicate_ids(automations))

        # Then check each automation against all rules
        for automation in automations:
            for rule in self.rules:
                if rule.enabled and rule.rule_id != "SCHEMA004":  # Skip duplicate ID rule (handled above)
                    findings = rule.check(automation)
                    all_findings.extend(findings)

        # Apply strict mode
        if strict:
            for finding in all_findings:
                if finding.severity == Severity.WARN:
                    finding.severity = Severity.ERROR

        return LintReport(
            engine_version=ENGINE_VERSION,
            ruleset_version=RULESET_VERSION,
            automations_detected=len(automations),
            findings=all_findings
        )

    def _check_duplicate_ids(self, automations: List[AutomationIR]) -> List[Finding]:
        """
        Check for duplicate automation IDs across all automations.

        Args:
            automations: List of automation IRs

        Returns:
            List of findings for duplicate IDs
        """
        findings = []
        seen_ids: Dict[str, int] = {}

        for automation in automations:
            if automation.id:
                if automation.id in seen_ids:
                    findings.append(Finding(
                        rule_id="SCHEMA004",
                        severity=Severity.ERROR,
                        message=f"Duplicate automation ID: '{automation.id}'",
                        why_it_matters="Automation IDs must be unique. Duplicate IDs can cause conflicts in Home Assistant",
                        path=automation.path,
                        suggested_fix=None
                    ))
                else:
                    seen_ids[automation.id] = automation.source_index

        return findings

    def get_rules(self) -> List[Dict]:
        """
        Return list of all rules with metadata.

        Returns:
            List of rule metadata dicts
        """
        return [
            {
                "rule_id": rule.rule_id,
                "name": rule.name,
                "severity": rule.severity,
                "category": rule.category,
                "enabled": rule.enabled
            }
            for rule in self.rules
        ]
