"""
MVP rule set for Home Assistant automation linting.
Implements the minimum 15 rules required for MVP.
"""

import re
from typing import List
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import AutomationIR, Finding, SuggestedFix
from constants import Severity, RuleCategory, VALID_MODES, HIGH_FREQUENCY_TRIGGERS, ENTITY_ID_PATTERN
from rules.base import Rule


# ============================================================================
# SCHEMA RULES
# ============================================================================

class MissingTriggerRule(Rule):
    """Check for missing trigger key."""

    rule_id = "SCHEMA001"
    name = "Missing Trigger"
    severity = Severity.ERROR
    category = RuleCategory.SCHEMA

    def check(self, automation: AutomationIR) -> List[Finding]:
        if not automation.trigger:
            return [Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Automation is missing 'trigger' key",
                why_it_matters="Every automation must have at least one trigger to activate",
                path=automation.path,
                suggested_fix=None  # Manual fix required
            )]
        return []


class MissingActionRule(Rule):
    """Check for missing action key."""

    rule_id = "SCHEMA002"
    name = "Missing Action"
    severity = Severity.ERROR
    category = RuleCategory.SCHEMA

    def check(self, automation: AutomationIR) -> List[Finding]:
        if not automation.action:
            return [Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Automation is missing 'action' key",
                why_it_matters="Automations without actions do nothing when triggered",
                path=automation.path,
                suggested_fix=None  # Manual fix required
            )]
        return []


class UnknownTopLevelKeysRule(Rule):
    """Check for unknown top-level keys."""

    rule_id = "SCHEMA003"
    name = "Unknown Top-Level Keys"
    severity = Severity.WARN
    category = RuleCategory.SCHEMA

    KNOWN_KEYS = {
        "id", "alias", "description", "trigger", "condition", "action",
        "mode", "max", "max_exceeded", "variables", "trace", "initial_state"
    }

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []
        unknown_keys = set(automation.raw_source.keys()) - self.KNOWN_KEYS

        if unknown_keys:
            findings.append(Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message=f"Unknown top-level keys: {', '.join(sorted(unknown_keys))}",
                why_it_matters="Unknown keys may indicate typos or deprecated configuration",
                path=automation.path,
                suggested_fix=None
            ))

        return findings


class DuplicateIDRule(Rule):
    """Check for duplicate automation IDs (cross-automation check)."""

    rule_id = "SCHEMA004"
    name = "Duplicate Automation ID"
    severity = Severity.ERROR
    category = RuleCategory.SCHEMA

    # This rule needs special handling in the engine to check across automations
    # For now, we'll mark it as a placeholder
    def check(self, automation: AutomationIR) -> List[Finding]:
        # This check is performed at the engine level
        return []


class InvalidServiceFormatRule(Rule):
    """Check for invalid service format in actions."""

    rule_id = "SCHEMA005"
    name = "Invalid Service Format"
    severity = Severity.ERROR
    category = RuleCategory.SCHEMA

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []

        for action in automation.action:
            if action.service:
                # Service should be in format "domain.service"
                if "." not in action.service:
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        message=f"Invalid service format: '{action.service}' (should be 'domain.service')",
                        why_it_matters="Services must be in 'domain.service' format to be recognized by Home Assistant",
                        path=action.path,
                        suggested_fix=None
                    ))

        return findings


# ============================================================================
# SYNTAX RULES
# ============================================================================

class TriggerMissingPlatformRule(Rule):
    """Check for triggers missing platform key."""

    rule_id = "SYNTAX001"
    name = "Trigger Missing Platform"
    severity = Severity.ERROR
    category = RuleCategory.SYNTAX

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []

        for trigger in automation.trigger:
            if trigger.platform == "unknown":
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    message="Trigger is missing 'platform' key",
                    why_it_matters="Every trigger must specify a platform (state, time, event, etc.)",
                    path=trigger.path,
                    suggested_fix=None
                ))

        return findings


# ============================================================================
# LOGIC RULES
# ============================================================================

class DelayWithSingleModeRule(Rule):
    """Check for delay with mode: single."""

    rule_id = "LOGIC001"
    name = "Delay with Single Mode"
    severity = Severity.WARN
    category = RuleCategory.LOGIC

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []

        # Check if automation has single mode and contains delay
        if automation.mode == "single":
            has_delay = any(
                "delay" in action.raw
                for action in automation.action
            )

            if has_delay:
                findings.append(Finding(
                    rule_id=self.rule_id,
                    severity=self.severity,
                    message="Automation uses delay with mode: single",
                    why_it_matters="With mode: single, new triggers are ignored while automation is running. Consider using mode: restart, queued, or parallel",
                    path=automation.path,
                    suggested_fix=SuggestedFix(
                        type="manual",
                        summary="Change mode to restart, queued, or parallel depending on your use case"
                    )
                ))

        return findings


class HighFrequencyTriggerRule(Rule):
    """Check for high-frequency triggers without debounce."""

    rule_id = "LOGIC002"
    name = "High-Frequency Trigger Without Debounce"
    severity = Severity.WARN
    category = RuleCategory.LOGIC

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []

        for trigger in automation.trigger:
            # Check for high-frequency trigger types
            if trigger.platform in HIGH_FREQUENCY_TRIGGERS:
                # Check if there's a for: duration to debounce
                has_debounce = "for" in trigger.raw

                if not has_debounce and trigger.platform == "state":
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        message=f"High-frequency trigger (platform: {trigger.platform}) without debounce",
                        why_it_matters="State triggers can fire very frequently. Consider adding 'for: HH:MM:SS' to debounce",
                        path=trigger.path,
                        suggested_fix=SuggestedFix(
                            type="manual",
                            summary="Add 'for: 00:00:05' or similar to debounce rapid state changes"
                        )
                    ))

        return findings


class ChooseWithoutDefaultRule(Rule):
    """Check for choose action without default."""

    rule_id = "LOGIC003"
    name = "Choose Without Default"
    severity = Severity.INFO
    category = RuleCategory.LOGIC

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []

        for action in automation.action:
            # Check if this is a choose action
            if "choose" in action.raw:
                has_default = "default" in action.raw

                if not has_default:
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        message="Choose action without default sequence",
                        why_it_matters="Without a default, nothing happens if no conditions match. Consider adding a default action or logging",
                        path=action.path,
                        suggested_fix=SuggestedFix(
                            type="manual",
                            summary="Add 'default:' key with fallback actions"
                        )
                    ))

        return findings


class EmptyTriggerListRule(Rule):
    """Check for empty trigger list."""

    rule_id = "LOGIC004"
    name = "Empty Trigger List"
    severity = Severity.ERROR
    category = RuleCategory.LOGIC

    def check(self, automation: AutomationIR) -> List[Finding]:
        # This is redundant with SCHEMA001 but kept for completeness
        if len(automation.trigger) == 0:
            return [Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Automation has empty trigger list",
                why_it_matters="Automation will never execute without triggers",
                path=automation.path,
                suggested_fix=None
            )]
        return []


class EmptyActionListRule(Rule):
    """Check for empty action list."""

    rule_id = "LOGIC005"
    name = "Empty Action List"
    severity = Severity.ERROR
    category = RuleCategory.LOGIC

    def check(self, automation: AutomationIR) -> List[Finding]:
        # This is redundant with SCHEMA002 but kept for completeness
        if len(automation.action) == 0:
            return [Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Automation has empty action list",
                why_it_matters="Automation does nothing when triggered without actions",
                path=automation.path,
                suggested_fix=None
            )]
        return []


# ============================================================================
# RELIABILITY RULES
# ============================================================================

class ServiceMissingTargetRule(Rule):
    """Check for service actions missing target/entity_id."""

    rule_id = "RELIABILITY001"
    name = "Service Missing Target"
    severity = Severity.ERROR
    category = RuleCategory.RELIABILITY

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []

        for action in automation.action:
            if action.service:
                # Check if action has target or entity_id
                has_target = "target" in action.raw or "entity_id" in action.raw or "device_id" in action.raw or "area_id" in action.raw

                # Some services don't require targets (e.g., homeassistant.restart)
                # Skip those
                service_parts = action.service.split(".")
                if len(service_parts) == 2:
                    domain = service_parts[0]
                    # Services that don't need targets
                    no_target_domains = {"homeassistant", "persistent_notification", "script", "automation", "notify"}

                    if domain not in no_target_domains and not has_target:
                        findings.append(Finding(
                            rule_id=self.rule_id,
                            severity=self.severity,
                            message=f"Service '{action.service}' is missing target/entity_id",
                            why_it_matters="Most services require a target to know what to act on",
                            path=action.path,
                            suggested_fix=None
                        ))

        return findings


class InvalidEntityIDFormatRule(Rule):
    """Check for invalid entity_id format."""

    rule_id = "RELIABILITY002"
    name = "Invalid Entity ID Format"
    severity = Severity.WARN
    category = RuleCategory.RELIABILITY

    def check(self, automation: AutomationIR) -> List[Finding]:
        findings = []

        # Check triggers
        for trigger in automation.trigger:
            if "entity_id" in trigger.raw:
                entity_id = trigger.raw["entity_id"]
                if isinstance(entity_id, str) and not self._is_valid_entity_id(entity_id):
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        message=f"Invalid entity_id format: '{entity_id}'",
                        why_it_matters="Entity IDs should be in format 'domain.object_id' (lowercase with underscores)",
                        path=trigger.path,
                        suggested_fix=None
                    ))

        # Check actions
        for action in automation.action:
            if "entity_id" in action.raw:
                entity_id = action.raw["entity_id"]
                if isinstance(entity_id, str) and not self._is_valid_entity_id(entity_id):
                    findings.append(Finding(
                        rule_id=self.rule_id,
                        severity=self.severity,
                        message=f"Invalid entity_id format: '{entity_id}'",
                        why_it_matters="Entity IDs should be in format 'domain.object_id' (lowercase with underscores)",
                        path=action.path,
                        suggested_fix=None
                    ))

        return findings

    def _is_valid_entity_id(self, entity_id: str) -> bool:
        """Check if entity_id matches expected format."""
        # Allow templates (they start with {{ and may not match pattern)
        if "{{" in entity_id or "{%" in entity_id:
            return True
        return bool(re.match(ENTITY_ID_PATTERN, entity_id))


# ============================================================================
# MAINTAINABILITY RULES
# ============================================================================

class MissingDescriptionRule(Rule):
    """Check for missing description."""

    rule_id = "MAINTAINABILITY001"
    name = "Missing Description"
    severity = Severity.INFO
    category = RuleCategory.MAINTAINABILITY

    def check(self, automation: AutomationIR) -> List[Finding]:
        if not automation.description:
            return [Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Automation is missing 'description' field",
                why_it_matters="Descriptions help document the purpose of automations for future maintenance",
                path=automation.path,
                suggested_fix=SuggestedFix(
                    type="auto",
                    summary="Add description field"
                )
            )]
        return []


class MissingAliasRule(Rule):
    """Check for missing alias."""

    rule_id = "MAINTAINABILITY002"
    name = "Missing Alias"
    severity = Severity.INFO
    category = RuleCategory.MAINTAINABILITY

    def check(self, automation: AutomationIR) -> List[Finding]:
        if not automation.alias:
            return [Finding(
                rule_id=self.rule_id,
                severity=self.severity,
                message="Automation is missing 'alias' field",
                why_it_matters="Aliases provide a friendly name for automations in the UI",
                path=automation.path,
                suggested_fix=SuggestedFix(
                    type="auto",
                    summary="Add alias field"
                )
            )]
        return []


# ============================================================================
# RULE REGISTRY
# ============================================================================

def get_all_rules() -> List[Rule]:
    """
    Get all available MVP rules.

    Returns:
        List of all rule instances
    """
    return [
        # Schema rules
        MissingTriggerRule(),
        MissingActionRule(),
        UnknownTopLevelKeysRule(),
        DuplicateIDRule(),
        InvalidServiceFormatRule(),

        # Syntax rules
        TriggerMissingPlatformRule(),

        # Logic rules
        DelayWithSingleModeRule(),
        HighFrequencyTriggerRule(),
        ChooseWithoutDefaultRule(),
        EmptyTriggerListRule(),
        EmptyActionListRule(),

        # Reliability rules
        ServiceMissingTargetRule(),
        InvalidEntityIDFormatRule(),

        # Maintainability rules
        MissingDescriptionRule(),
        MissingAliasRule(),
    ]
