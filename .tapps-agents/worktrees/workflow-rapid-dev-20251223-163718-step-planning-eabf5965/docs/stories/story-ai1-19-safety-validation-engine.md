# Story AI1.19: Safety Validation Engine

**Epic:** Epic-AI-1 - AI Automation Suggestion System  
**Story ID:** AI1.19  
**Priority:** Critical  
**Estimated Effort:** 8-10 hours  
**Dependencies:** Story AI1.11 (HA Integration API)

---

## User Story

**As a** system administrator  
**I want** AI-generated automations to be validated for safety  
**so that** dangerous or destructive automations are prevented from being deployed

---

## Business Value

- Prevents dangerous automations (e.g., disabling security, extreme climate changes)
- Detects conflicting automations before deployment
- Builds user trust in AI-generated suggestions
- Reduces risk of home automation failures
- Provides clear safety warnings with actionable feedback

---

## Acceptance Criteria

1. ✅ Validates automations against 6 core safety rules
2. ✅ Detects conflicting automations with existing HA automations
3. ✅ Calculates safety score (0-100) for each automation
4. ✅ Blocks deployment of automations scoring <60 (configurable)
5. ✅ Provides detailed safety report with specific issues
6. ✅ Supports override mechanism for power users
7. ✅ Configurable safety levels (strict/moderate/permissive)
8. ✅ Processing time <500ms per automation
9. ✅ Unit tests validate all safety rules
10. ✅ False positive rate <5% (validated on test data)

---

## Technical Implementation Notes

### Safety Validator Service

**Create: services/ai-automation-service/src/safety_validator.py**

```python
from typing import Dict, List, Optional
from dataclasses import dataclass
import yaml
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class SafetyLevel(str, Enum):
    """Safety validation strictness levels"""
    STRICT = "strict"          # Block anything questionable
    MODERATE = "moderate"      # Warn on risky, block dangerous
    PERMISSIVE = "permissive"  # Warn only, allow override


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
        
        for action in automation.get('action', []):
            if action.get('service') == 'climate.set_temperature':
                data = action.get('data', {})
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
                if temp and (temp < 55 or temp > 85):
                    issues.append(SafetyIssue(
                        rule="climate_extremes",
                        severity="critical",
                        message=f"Extreme temperature setting: {temp}°F",
                        suggested_fix="Use reasonable temperature range (60-80°F)"
                    ))
        
        return issues
    
    def _check_bulk_device_off(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 2: No bulk device shutoffs without explicit confirmation"""
        issues = []
        
        for action in automation.get('action', []):
            service = action.get('service', '')
            target = action.get('target', {})
            
            # Flag "turn off all" patterns
            if 'turn_off' in service:
                if target.get('area_id') == 'all' or 'all' in str(target):
                    issues.append(SafetyIssue(
                        rule="bulk_device_off",
                        severity="critical",
                        message="Automation turns off ALL devices without confirmation",
                        suggested_fix="Specify specific devices or add confirmation condition"
                    ))
                
                # Flag turning off multiple areas
                if isinstance(target.get('area_id'), list) and len(target['area_id']) > 3:
                    issues.append(SafetyIssue(
                        rule="bulk_device_off",
                        severity="warning",
                        message=f"Turns off devices in {len(target['area_id'])} areas",
                        suggested_fix="Consider more targeted approach or add safety condition"
                    ))
        
        return issues
    
    def _check_security_disable(self, automation: Dict) -> List[SafetyIssue]:
        """Rule 3: Never disable security automations"""
        issues = []
        
        for action in automation.get('action', []):
            service = action.get('service', '')
            target = action.get('target', {})
            entity_id = target.get('entity_id', '')
            
            # Check if disabling automation
            if service == 'automation.turn_off':
                # Flag if targeting security-related automations
                if 'security' in str(entity_id).lower() or 'alarm' in str(entity_id).lower():
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
        for condition in automation.get('condition', []):
            if condition.get('condition') == 'time':
                has_time_condition = True
            if condition.get('condition') == 'state':
                has_state_condition = True
        
        # Check for destructive actions without constraints
        destructive_services = [
            'turn_off', 'close', 'lock', 'set_hvac_mode'
        ]
        
        has_destructive_action = False
        for action in automation.get('action', []):
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
        
        for trigger in automation.get('trigger', []):
            # Check for very short time patterns
            if trigger.get('platform') == 'time_pattern':
                minutes = trigger.get('minutes')
                if minutes == '*':  # Every minute
                    issues.append(SafetyIssue(
                        rule="excessive_triggers",
                        severity="warning",
                        message="Triggers every minute (60 times per hour)",
                        suggested_fix="Consider less frequent trigger or use state trigger"
                    ))
            
            # Check for state changes on frequently changing sensors
            if trigger.get('platform') == 'state':
                entity_id = trigger.get('entity_id', '')
                if 'sensor.' in entity_id and 'power' in entity_id.lower():
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
        ]
        
        for action in automation.get('action', []):
            service = action.get('service', '')
            if service in dangerous_services:
                issues.append(SafetyIssue(
                    rule="destructive_actions",
                    severity="critical",
                    message=f"Automation attempts to call: {service}",
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
        - Duplicate functionality
        """
        issues = []
        
        new_triggers = new_automation.get('trigger', [])
        new_actions = new_automation.get('action', [])
        
        for existing in existing_automations:
            existing_triggers = existing.get('trigger', [])
            existing_actions = existing.get('action', [])
            
            # Check for identical triggers
            if self._triggers_match(new_triggers, existing_triggers):
                # Check if actions conflict
                if self._actions_conflict(new_actions, existing_actions):
                    issues.append(SafetyIssue(
                        rule="conflicting_automation",
                        severity="warning",
                        message=f"May conflict with existing automation: {existing.get('alias', 'unknown')}",
                        suggested_fix="Review existing automation and ensure actions are compatible"
                    ))
        
        return issues
    
    def _triggers_match(self, triggers1: List[Dict], triggers2: List[Dict]) -> bool:
        """Check if trigger lists are similar"""
        if len(triggers1) != len(triggers2):
            return False
        
        # Simple matching - check if platforms and entity_ids match
        for t1, t2 in zip(triggers1, triggers2):
            if t1.get('platform') != t2.get('platform'):
                return False
            if t1.get('entity_id') != t2.get('entity_id'):
                return False
        
        return True
    
    def _actions_conflict(self, actions1: List[Dict], actions2: List[Dict]) -> bool:
        """Check if action lists conflict"""
        # Check if both act on same entities with opposite commands
        entities1 = {a.get('target', {}).get('entity_id') for a in actions1}
        entities2 = {a.get('target', {}).get('entity_id') for a in actions2}
        
        # If acting on same entities, might conflict
        if entities1.intersection(entities2):
            # Check for opposite commands (turn_on vs turn_off)
            services1 = {a.get('service', '') for a in actions1}
            services2 = {a.get('service', '') for a in actions2}
            
            if ('turn_on' in services1 and 'turn_off' in services2) or \
               ('turn_off' in services1 and 'turn_on' in services2):
                return True
        
        return False
    
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


# Dependency injection helper
def get_safety_validator(safety_level: str = None) -> SafetyValidator:
    """Get configured SafetyValidator instance"""
    level = SafetyLevel(safety_level) if safety_level else SafetyLevel.MODERATE
    return SafetyValidator(safety_level=level)
```

### Integration with Deployment Endpoint

**Update: services/ai-automation-service/src/api/deployment.py**

```python
from src.safety_validator import SafetyValidator, get_safety_validator
from fastapi import Depends

@router.post("/{suggestion_id}")
async def deploy_automation(
    suggestion_id: int,
    force_deploy: bool = False,  # Override safety checks
    ha_client: HomeAssistantClient = Depends(get_ha_client),
    safety_validator: SafetyValidator = Depends(get_safety_validator),
    db: AsyncSession = Depends(get_db)
):
    """
    Deploy approved automation with safety validation.
    
    Args:
        suggestion_id: ID of suggestion to deploy
        force_deploy: Override safety checks (requires admin)
    """
    
    # Get suggestion
    suggestion = await get_suggestion_by_id(db, suggestion_id)
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    
    if suggestion.status != 'approved':
        raise HTTPException(status_code=400, detail="Only approved suggestions can be deployed")
    
    # SAFETY VALIDATION (NEW)
    existing_automations = await ha_client.get_automations()
    safety_result = await safety_validator.validate(
        suggestion.automation_yaml,
        existing_automations
    )
    
    if not safety_result.passed and not force_deploy:
        logger.warning(
            f"Safety validation failed for suggestion {suggestion_id}: "
            f"{safety_result.summary}"
        )
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Safety validation failed",
                "safety_score": safety_result.safety_score,
                "issues": [
                    {
                        "rule": issue.rule,
                        "severity": issue.severity,
                        "message": issue.message,
                        "suggested_fix": issue.suggested_fix
                    }
                    for issue in safety_result.issues
                ],
                "can_override": safety_result.can_override,
                "summary": safety_result.summary
            }
        )
    
    # Store safety result
    await store_safety_validation(db, suggestion_id, safety_result)
    
    # Proceed with deployment (existing logic)
    try:
        automation_dict = ha_client.validate_automation_yaml(suggestion.automation_yaml)
        ha_automation_id = await ha_client.deploy_automation(automation_dict)
    except Exception as e:
        logger.error(f"Deployment failed for suggestion {suggestion_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {e}")
    
    # Update database
    await update_deployment_status(
        db,
        suggestion_id,
        status='deployed',
        ha_automation_id=ha_automation_id,
        deployed_at=datetime.utcnow(),
        safety_score=safety_result.safety_score
    )
    
    logger.info(
        f"Suggestion {suggestion_id} deployed as {ha_automation_id} "
        f"(safety score: {safety_result.safety_score})"
    )
    
    return {
        "success": True,
        "suggestion_id": suggestion_id,
        "ha_automation_id": ha_automation_id,
        "deployed_at": datetime.utcnow().isoformat(),
        "safety_score": safety_result.safety_score
    }
```

### Configuration

**Update: infrastructure/env.ai-automation**

```bash
# Safety Validation
AI_AUTOMATION_SAFETY_LEVEL=moderate  # strict, moderate, permissive
AI_AUTOMATION_ALLOW_OVERRIDE=true    # Allow force_deploy override
AI_AUTOMATION_MIN_SAFETY_SCORE=60    # Minimum score to deploy
```

---

## Integration Verification

**IV1: Safety rules block dangerous automations**
- Test with automation that disables security
- Verify deployment blocked
- Check clear error message returned

**IV2: Conflict detection works**
- Create existing automation in HA
- Generate conflicting AI automation
- Verify conflict detected and reported

**IV3: Safety scores accurate**
- Test with clean automation (expect 100)
- Test with minor warnings (expect 70-90)
- Test with critical issues (expect <60)

**IV4: Override mechanism works for admins**
- Deploy with `force_deploy=true`
- Verify bypasses non-critical checks
- Verify still blocks security-critical issues

**IV5: Performance within limits**
- Validate 10 automations
- Verify average time <500ms each
- Check no memory leaks

---

## Tasks Breakdown

1. **Create SafetyValidator class** (2 hours)
2. **Implement 6 safety rule checks** (2 hours)
3. **Implement conflict detection** (1.5 hours)
4. **Add safety score calculation** (0.5 hours)
5. **Integrate with deployment endpoint** (1 hour)
6. **Add configuration and override support** (0.5 hours)
7. **Unit tests for all rules** (1.5 hours)
8. **Integration test with deployment flow** (1 hour)

**Total:** 8-10 hours

---

## Definition of Done

- [ ] SafetyValidator class implemented with 6 rules
- [ ] Conflict detection algorithm working
- [ ] Safety scoring accurate (0-100 scale)
- [ ] Integrated with deployment endpoint
- [ ] Override mechanism functional
- [ ] Configurable safety levels working
- [ ] Unit tests >85% coverage
- [ ] All 6 rules tested independently
- [ ] Integration test with HA deployment passes
- [ ] Performance <500ms per validation verified
- [ ] False positive rate <5% validated
- [ ] Documentation updated
- [ ] Code reviewed and approved

---

## Testing Strategy

### Unit Tests

```python
# tests/test_safety_validator.py
import pytest
from src.safety_validator import SafetyValidator, SafetyLevel

def test_climate_extremes_detected():
    """Test Rule 1: Extreme climate changes blocked"""
    validator = SafetyValidator(SafetyLevel.MODERATE)
    
    automation_yaml = """
    alias: Dangerous Heat
    trigger:
      - platform: time
        at: "12:00:00"
    action:
      - service: climate.set_temperature
        data:
          temperature: 95
    """
    
    result = await validator.validate(automation_yaml)
    
    assert not result.passed
    assert result.safety_score < 70
    assert any(i.rule == "climate_extremes" for i in result.issues)

def test_bulk_device_off_detected():
    """Test Rule 2: Bulk shutoff blocked"""
    validator = SafetyValidator(SafetyLevel.MODERATE)
    
    automation_yaml = """
    alias: Turn Off Everything
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: light.turn_off
        target:
          area_id: all
    """
    
    result = await validator.validate(automation_yaml)
    
    assert not result.passed
    assert any(i.severity == "critical" for i in result.issues)

def test_safe_automation_passes():
    """Test safe automation gets high score"""
    validator = SafetyValidator(SafetyLevel.MODERATE)
    
    automation_yaml = """
    alias: Morning Lights
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: state
        entity_id: binary_sensor.workday
        state: "on"
    action:
      - service: light.turn_on
        target:
          entity_id: light.kitchen
        data:
          brightness_pct: 50
    """
    
    result = await validator.validate(automation_yaml)
    
    assert result.passed
    assert result.safety_score >= 90
    assert len(result.issues) == 0

def test_conflict_detection():
    """Test conflict detection with existing automation"""
    validator = SafetyValidator(SafetyLevel.MODERATE)
    
    new_automation_yaml = """
    alias: Turn Light Off
    trigger:
      - platform: state
        entity_id: binary_sensor.motion
        to: "off"
    action:
      - service: light.turn_off
        target:
          entity_id: light.kitchen
    """
    
    existing_automations = [
        {
            'alias': 'Turn Light On',
            'trigger': [
                {
                    'platform': 'state',
                    'entity_id': 'binary_sensor.motion',
                    'to': 'off'
                }
            ],
            'action': [
                {
                    'service': 'light.turn_on',
                    'target': {'entity_id': 'light.kitchen'}
                }
            ]
        }
    ]
    
    result = await validator.validate(new_automation_yaml, existing_automations)
    
    assert any(i.rule == "conflicting_automation" for i in result.issues)
```

### Integration Tests

```python
# tests/test_safe_deployment.py
async def test_safe_automation_deploys():
    """Test safe automation passes validation and deploys"""
    response = client.post(
        "/api/deploy/1",
        json={"force_deploy": False}
    )
    
    assert response.status_code == 200
    assert "safety_score" in response.json()
    assert response.json()["safety_score"] >= 60

async def test_unsafe_automation_blocked():
    """Test unsafe automation blocked by validation"""
    # Create suggestion with dangerous automation
    suggestion_id = await create_dangerous_suggestion()
    
    response = client.post(
        f"/api/deploy/{suggestion_id}",
        json={"force_deploy": False}
    )
    
    assert response.status_code == 400
    assert "Safety validation failed" in response.json()["detail"]["error"]
    assert response.json()["detail"]["safety_score"] < 60

async def test_override_works():
    """Test force_deploy overrides validation"""
    suggestion_id = await create_warning_suggestion()
    
    response = client.post(
        f"/api/deploy/{suggestion_id}",
        json={"force_deploy": True}
    )
    
    assert response.status_code == 200
```

---

## Reference Files

**Copy patterns from:**
- Story AI1.11 (HA Integration) for deployment flow
- `services/ai-automation-service/src/ha_client.py` for HA integration
- YAML validation patterns from existing services

**Documentation:**
- PyYAML: https://pyyaml.org/wiki/PyYAMLDocumentation
- Home Assistant Automation: https://www.home-assistant.io/docs/automation/

---

## Notes

- Safety validation is **critical** for production use
- False positives should be minimized to avoid user frustration
- Conflict detection uses simple heuristics (can be enhanced later)
- Override mechanism requires admin permissions (implement in Story AI1.22)
- Safety scores help users understand risk level
- Detailed issue messages improve user trust
- Consider machine learning for conflict detection in Phase 2

---

**Story Status:** Ready for Development  
**Assigned To:** TBD  
**Created:** 2025-10-16  
**Updated:** 2025-10-16

