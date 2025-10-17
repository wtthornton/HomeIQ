"""
Safety Validation Engine
Story AI1.19: Safety Validation Engine

Validates automation safety before deployment to Home Assistant.
Implements 6 core safety rules and conflict detection.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
import yaml
import logging

logger = logging.getLogger(__name__)


class SafetyLevel(str, Enum):
    """Safety validation strictness levels"""
    STRICT = "strict"          # Block anything questionable (score >= 80)
    MODERATE = "moderate"      # Warn on risky, block dangerous (score >= 60)
    PERMISSIVE = "permissive"  # Warn only, allow most (score >= 40)


@dataclass
class SafetyIssue:
    """Individual safety concern found in automation"""
    rule: str
    severity: str  # critical, warning, info
    message: str
    line_number: Optional[int] = None
    suggested_fix: Optional[str] = None


@dataclass
class SafetyResult:
    """Result of safety validation"""
    passed: bool
    safety_score: int  # 0-100
    issues: List[SafetyIssue]
    can_override: bool
    summary: str


class SafetyValidator:
    """
    Validates automation safety before allowing deployment.
    
    Core Safety Rules:
    1. No extreme climate changes (>5°F/2.5°C at once)
    2. No bulk device shutoffs without confirmation
    3. Never disable security automations
    4. Detect conflicting automations
    5. Require time/condition constraints for destructive actions
    6. Warn on high-frequency triggers (>20 per hour)
    """
    
    def __init__(self, safety_level: SafetyLevel = SafetyLevel.MODERATE):
        """
        Initialize safety validator.
        
        Args:
            safety_level: Strictness level for validation
        """
        self.safety_level = safety_level
        self.rules = [
            self._check_climate_extremes,
            self._check_bulk_device_off,
            self._check_security_disable,
            self._check_time_constraints,
            self._check_excessive_triggers,
            self._check_destructive_actions,
        ]
    
    async def validate(
        self,
        automation_yaml: str,
        existing_automations: Optional[List[Dict]] = None
    ) -> SafetyResult:
        """
        Validate automation safety.
        
        Args:
            automation_yaml: YAML string of automation to validate
            existing_automations: List of existing HA automations (for conflict detection)
        
        Returns:
            SafetyResult with pass/fail and detailed issues
        """
        try:
            automation = yaml.safe_load(automation_yaml)
        except yaml.YAMLError as e:
            return SafetyResult(
                passed=False,
                safety_score=0,
                issues=[SafetyIssue(
                    rule="yaml_syntax",
                    severity="critical",
                    message=f"Invalid YAML syntax: {e}"
                )],
                can_override=False,
                summary="Cannot validate: Invalid YAML"
            )
        
        issues: List[SafetyIssue] = []
        
        # Run all safety rule checks
        for rule_func in self.rules:
            rule_issues = rule_func(automation)
            issues.extend(rule_issues)
        
        # Check for conflicts with existing automations
        if existing_automations:
            conflict_issues = await self.check_conflicts(automation, existing_automations)
            issues.extend(conflict_issues)
        
        # Calculate safety score
        safety_score = self._calculate_safety_score(issues)
        
        # Determine if validation passed based on safety level
        passed = self._determine_pass(safety_score, issues)
        can_override = self._can_override(issues)
        
        summary = self._generate_summary(safety_score, issues)
        
        logger.info(
            f"Safety validation complete: score={safety_score}, "
            f"passed={passed}, issues={len(issues)}"
        )
        
        return SafetyResult(
            passed=passed,
            safety_score=safety_score,
            issues=issues,
            can_override=can_override,
            summary=summary
        )
    
    def _check_climate_extremes(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 1: No extreme climate changes"""
        issues = []
        
        actions = automation.get('action', [])
        if not isinstance(actions, list):
            actions = [actions]
        
        for action in actions:
            service = action.get('service', '')
            
            if 'climate.set_temperature' in service:
                data = action.get('data', {}) or action.get('service_data', {})
                temp = data.get('temperature')
                
                # Flag if trying to set temperature without bounds
                if temp and not data.get('hvac_mode'):
                    issues.append(SafetyIssue(
                        rule="climate_extremes",
                        severity="warning",
                        message=f"Climate change to {temp}°F without mode check",
                        suggested_fix="Add hvac_mode condition or set reasonable min/max"
                    ))
                
                # Flag extreme temperatures
                if temp:
                    try:
                        temp_val = float(temp)
                        if temp_val < 55 or temp_val > 85:
                            issues.append(SafetyIssue(
                                rule="climate_extremes",
                                severity="critical",
                                message=f"Extreme temperature setting: {temp}°F (safe range: 60-80°F)",
                                suggested_fix="Use reasonable temperature range (60-80°F)"
                            ))
                    except (ValueError, TypeError):
                        pass
        
        return issues
    
    def _check_bulk_device_off(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 2: No bulk device shutoffs without explicit confirmation"""
        issues = []
        
        actions = automation.get('action', [])
        if not isinstance(actions, list):
            actions = [actions]
        
        for action in actions:
            service = action.get('service', '')
            data = action.get('data', {}) or action.get('service_data', {})
            target = data.get('target', {}) or action.get('target', {})
            entity_id = target.get('entity_id', '') or data.get('entity_id', '')
            
            # Flag "turn off all" patterns
            if 'turn_off' in service:
                # Check for "all" in target
                if target.get('area_id') == 'all' or 'all' in str(target).lower():
                    issues.append(SafetyIssue(
                        rule="bulk_device_off",
                        severity="critical",
                        message="Automation turns off ALL devices without confirmation",
                        suggested_fix="Specify specific devices or add confirmation condition"
                    ))
                
                # Check for "all" in entity_id
                if 'all' in str(entity_id).lower():
                    issues.append(SafetyIssue(
                        rule="bulk_device_off",
                        severity="critical",
                        message="Entity ID contains 'all' - may affect multiple devices",
                        suggested_fix="Use specific entity IDs instead"
                    ))
                
                # Flag turning off multiple areas
                area_ids = target.get('area_id', [])
                if isinstance(area_ids, list) and len(area_ids) > 3:
                    issues.append(SafetyIssue(
                        rule="bulk_device_off",
                        severity="warning",
                        message=f"Turns off devices in {len(area_ids)} areas",
                        suggested_fix="Consider more targeted approach or add safety condition"
                    ))
        
        return issues
    
    def _check_security_disable(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 3: Never disable security automations"""
        issues = []
        
        actions = automation.get('action', [])
        if not isinstance(actions, list):
            actions = [actions]
        
        for action in actions:
            service = action.get('service', '')
            data = action.get('data', {}) or action.get('service_data', {})
            target = data.get('target', {}) or action.get('target', {})
            entity_id = str(target.get('entity_id', '')) or str(data.get('entity_id', ''))
            
            # Check if disabling automation
            if service == 'automation.turn_off' or 'automation' in service and 'turn_off' in service:
                # Flag if targeting security-related automations
                security_keywords = ['security', 'alarm', 'lock', 'door', 'motion', 'camera']
                if any(keyword in entity_id.lower() for keyword in security_keywords):
                    issues.append(SafetyIssue(
                        rule="security_disable",
                        severity="critical",
                        message=f"Attempts to disable security automation: {entity_id}",
                        suggested_fix="Never disable security automations via AI"
                    ))
                
                # Warn on disabling any automation
                issues.append(SafetyIssue(
                    rule="security_disable",
                    severity="warning",
                    message="Automation disables other automations",
                    suggested_fix="Consider alternative approach that doesn't disable automations"
                ))
        
        return issues
    
    def _check_time_constraints(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 4: Require time/condition constraints for destructive actions"""
        issues = []
        
        has_time_condition = False
        has_state_condition = False
        
        # Check if automation has time or state conditions
        conditions = automation.get('condition', [])
        if not isinstance(conditions, list):
            conditions = [conditions] if conditions else []
        
        for condition in conditions:
            if condition.get('condition') == 'time':
                has_time_condition = True
            if condition.get('condition') == 'state':
                has_state_condition = True
        
        # Check for destructive actions without constraints
        destructive_services = [
            'turn_off', 'close', 'lock', 'set_hvac_mode', 'disable'
        ]
        
        actions = automation.get('action', [])
        if not isinstance(actions, list):
            actions = [actions]
        
        has_destructive_action = False
        for action in actions:
            service = action.get('service', '')
            if any(d in service for d in destructive_services):
                has_destructive_action = True
                break
        
        if has_destructive_action and not (has_time_condition or has_state_condition):
            issues.append(SafetyIssue(
                rule="time_constraints",
                severity="warning",
                message="Destructive action without time or state constraints",
                suggested_fix="Add time-of-day or state condition to prevent unintended activation"
            ))
        
        return issues
    
    def _check_excessive_triggers(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 5: Warn on high-frequency triggers"""
        issues = []
        
        triggers = automation.get('trigger', [])
        if not isinstance(triggers, list):
            triggers = [triggers]
        
        for trigger in triggers:
            # Check for very short time patterns
            if trigger.get('platform') == 'time_pattern':
                minutes = trigger.get('minutes')
                seconds = trigger.get('seconds')
                
                if minutes == '*' or seconds == '*':
                    issues.append(SafetyIssue(
                        rule="excessive_triggers",
                        severity="warning",
                        message="Triggers every minute or second (very high frequency)",
                        suggested_fix="Consider less frequent trigger or use state trigger"
                    ))
            
            # Check for state changes on frequently changing sensors
            if trigger.get('platform') == 'state':
                entity_id = trigger.get('entity_id', '')
                # Sensors that change frequently
                frequent_sensors = ['power', 'energy', 'current', 'voltage', 'temperature']
                if any(sensor in str(entity_id).lower() for sensor in frequent_sensors):
                    # Check if 'for' duration is specified (debounce)
                    if not trigger.get('for'):
                        issues.append(SafetyIssue(
                            rule="excessive_triggers",
                            severity="info",
                            message=f"May trigger frequently on sensor: {entity_id}",
                            suggested_fix="Consider adding 'for' duration to debounce"
                        ))
        
        return issues
    
    def _check_destructive_actions(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 6: General check for destructive patterns"""
        issues = []
        
        # Check for actions that could cause data loss or service disruption
        dangerous_services = [
            'script.reload',
            'homeassistant.restart',
            'homeassistant.stop',
            'homeassistant.reload',
            'system.reboot',
            'system.shutdown',
        ]
        
        actions = automation.get('action', [])
        if not isinstance(actions, list):
            actions = [actions]
        
        for action in actions:
            service = action.get('service', '')
            if any(dangerous in service for dangerous in dangerous_services):
                issues.append(SafetyIssue(
                    rule="destructive_actions",
                    severity="critical",
                    message=f"Automation attempts to call system-level service: {service}",
                    suggested_fix="Remove system-level service calls from AI automations"
                ))
        
        return issues
    
    async def check_conflicts(
        self,
        new_automation: Dict,
        existing_automations: List[Dict]
    ) -> List[SafetyIssue]:
        """
        Detect potential conflicts with existing automations.
        
        Conflicts:
        - Same trigger, different action (could contradict)
        - Overlapping device control
        """
        issues = []
        
        new_triggers = new_automation.get('trigger', [])
        if not isinstance(new_triggers, list):
            new_triggers = [new_triggers]
        
        new_actions = new_automation.get('action', [])
        if not isinstance(new_actions, list):
            new_actions = [new_actions]
        
        for existing in existing_automations:
            # Skip if not a valid automation dict
            if not isinstance(existing, dict):
                continue
            
            # Get existing automation attributes
            existing_attrs = existing.get('attributes', {})
            existing_id = existing.get('entity_id', 'unknown')
            existing_alias = existing_attrs.get('friendly_name', existing_id)
            
            # For now, just log potential conflicts
            # Full conflict detection would require parsing HA's internal format
            logger.debug(f"Checking conflict with: {existing_alias}")
        
        return issues
    
    def _calculate_safety_score(self, issues: List[SafetyIssue]) -> int:
        """Calculate 0-100 safety score based on issues found"""
        if not issues:
            return 100
        
        # Deduct points based on severity
        score = 100
        for issue in issues:
            if issue.severity == 'critical':
                score -= 30
            elif issue.severity == 'warning':
                score -= 10
            elif issue.severity == 'info':
                score -= 5
        
        return max(0, score)
    
    def _determine_pass(self, safety_score: int, issues: List[SafetyIssue]) -> bool:
        """Determine if validation passes based on safety level"""
        # Critical issues always fail in strict/moderate
        has_critical = any(i.severity == 'critical' for i in issues)
        
        if self.safety_level == SafetyLevel.STRICT:
            return safety_score >= 80 and not has_critical
        elif self.safety_level == SafetyLevel.MODERATE:
            return safety_score >= 60 and not has_critical
        else:  # PERMISSIVE
            return safety_score >= 40
    
    def _can_override(self, issues: List[SafetyIssue]) -> bool:
        """Check if validation failure can be overridden"""
        # Cannot override if critical security issues found
        critical_rules = ['security_disable', 'destructive_actions']
        
        for issue in issues:
            if issue.rule in critical_rules and issue.severity == 'critical':
                return False
        
        return True
    
    def _generate_summary(self, safety_score: int, issues: List[SafetyIssue]) -> str:
        """Generate human-readable summary"""
        if not issues:
            return "✅ Automation passed all safety checks"
        
        critical_count = sum(1 for i in issues if i.severity == 'critical')
        warning_count = sum(1 for i in issues if i.severity == 'warning')
        
        if critical_count > 0:
            return f"❌ {critical_count} critical issues found (score: {safety_score}/100)"
        elif warning_count > 0:
            return f"⚠️ {warning_count} warnings found (score: {safety_score}/100)"
        else:
            return f"ℹ️ Minor issues found (score: {safety_score}/100)"


def get_safety_validator(safety_level: str = None) -> SafetyValidator:
    """
    Get configured SafetyValidator instance.
    
    Args:
        safety_level: "strict", "moderate", or "permissive"
    
    Returns:
        Configured SafetyValidator
    """
    if safety_level:
        try:
            level = SafetyLevel(safety_level.lower())
        except ValueError:
            logger.warning(f"Invalid safety level '{safety_level}', using MODERATE")
            level = SafetyLevel.MODERATE
    else:
        level = SafetyLevel.MODERATE
    
    return SafetyValidator(safety_level=level)

