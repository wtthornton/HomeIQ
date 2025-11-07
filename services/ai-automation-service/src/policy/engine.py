"""
Policy Engine - Evaluates automation plans against policy rules
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class Verdict(str, Enum):
    """Policy verdict"""
    ALLOW = "allow"
    WARN = "warn"
    DENY = "deny"


@dataclass
class PolicyRule:
    """Policy rule definition"""
    name: str
    description: str
    condition: str  # Condition expression (simplified for v1)
    severity: str  # "critical", "warning", "info"
    message: str
    override: Optional[str] = None  # Override key if allowed


@dataclass
class PolicyResult:
    """Result of policy evaluation"""
    rule_name: str
    verdict: Verdict
    message: str
    severity: str
    can_override: bool


@dataclass
class PolicyVerdict:
    """Overall policy verdict"""
    verdict: Verdict  # Overall verdict
    results: List[PolicyResult]  # Individual rule results
    reasons: List[str]  # Human-readable reasons
    can_override: bool  # Whether override is possible
    
    @property
    def passed(self) -> bool:
        """Check if policy passed"""
        return self.verdict == Verdict.ALLOW


class PolicyEngine:
    """
    Policy engine that evaluates automations against policy rules.
    
    Simple rule evaluation for v1:
    - Load rules from YAML
    - Evaluate rules against automation
    - Return verdict (allow/warn/deny)
    """
    
    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize policy engine.
        
        Args:
            rules_path: Path to rules YAML file (default: policy/rules.yaml)
        """
        if rules_path is None:
            rules_path = Path(__file__).parent / "rules.yaml"
        
        self.rules_path = Path(rules_path)
        self.rules: Dict[str, List[PolicyRule]] = {
            "deny": [],
            "warn": []
        }
        self._load_rules()
        logger.info(f"PolicyEngine initialized with {len(self.rules['deny'])} deny rules, {len(self.rules['warn'])} warn rules")
    
    def _load_rules(self):
        """Load policy rules from YAML file"""
        try:
            if not self.rules_path.exists():
                logger.warning(f"Policy rules file not found: {self.rules_path}, using empty rules")
                self.rules = {"deny": [], "warn": []}
                return
            
            with open(self.rules_path) as f:
                data = yaml.safe_load(f)
            
            if not data:
                logger.warning("Policy rules file is empty, using empty rules")
                self.rules = {"deny": [], "warn": []}
                return
            
            rules_data = data.get("rules", {})
            
            # Load deny rules
            for rule_dict in rules_data.get("deny", []):
                rule = PolicyRule(
                    name=rule_dict["name"],
                    description=rule_dict.get("description", ""),
                    condition=rule_dict.get("condition", ""),
                    severity=rule_dict.get("severity", "critical"),
                    message=rule_dict.get("message", ""),
                    override=rule_dict.get("override")
                )
                self.rules["deny"].append(rule)
            
            # Load warn rules
            for rule_dict in rules_data.get("warn", []):
                rule = PolicyRule(
                    name=rule_dict["name"],
                    description=rule_dict.get("description", ""),
                    condition=rule_dict.get("condition", ""),
                    severity=rule_dict.get("severity", "warning"),
                    message=rule_dict.get("message", ""),
                    override=rule_dict.get("override")
                )
                self.rules["warn"].append(rule)
            
        except Exception as e:
            logger.error(f"Failed to load policy rules: {e}")
            # Use minimal default rules
            self.rules = {
                "deny": [],
                "warn": []
            }
    
    async def evaluate(
        self,
        automation: Dict[str, Any],
        overrides: Optional[Dict[str, bool]] = None
    ) -> PolicyVerdict:
        """
        Evaluate automation against policy rules.
        
        Args:
            automation: Automation plan (dict or AutomationPlan)
            overrides: Optional override flags (e.g., {"allow_peak": True})
            
        Returns:
            PolicyVerdict with overall verdict and rule results
        """
        if overrides is None:
            overrides = {}
        
        results: List[PolicyResult] = []
        reasons: List[str] = []
        
        # Evaluate deny rules
        for rule in self.rules["deny"]:
            # Check if override is set
            if rule.override and overrides.get(rule.override):
                continue  # Skip this rule if overridden
            
            # Simple condition evaluation (v1 - basic pattern matching)
            if self._evaluate_condition(rule.condition, automation, overrides):
                results.append(PolicyResult(
                    rule_name=rule.name,
                    verdict=Verdict.DENY,
                    message=rule.message,
                    severity=rule.severity,
                    can_override=rule.override is not None
                ))
                reasons.append(f"{rule.name}: {rule.message}")
        
        # Evaluate warn rules
        for rule in self.rules["warn"]:
            if self._evaluate_condition(rule.condition, automation, overrides):
                results.append(PolicyResult(
                    rule_name=rule.name,
                    verdict=Verdict.WARN,
                    message=rule.message,
                    severity=rule.severity,
                    can_override=False  # Warns don't need override
                ))
                reasons.append(f"{rule.name}: {rule.message}")
        
        # Determine overall verdict
        if any(r.verdict == Verdict.DENY for r in results):
            verdict = Verdict.DENY
        elif any(r.verdict == Verdict.WARN for r in results):
            verdict = Verdict.WARN
        else:
            verdict = Verdict.ALLOW
        
        can_override = any(r.can_override for r in results if r.verdict == Verdict.DENY)
        
        return PolicyVerdict(
            verdict=verdict,
            results=results,
            reasons=reasons,
            can_override=can_override
        )
    
    def _evaluate_condition(
        self,
        condition: str,
        automation: Dict[str, Any],
        overrides: Dict[str, bool]
    ) -> bool:
        """
        Evaluate condition expression (simplified for v1).
        
        For v1, we do basic pattern matching on common patterns.
        Future: Full expression evaluation with AST.
        
        Args:
            condition: Condition expression string
            automation: Automation plan
            overrides: Override flags
            
        Returns:
            True if condition matches
        """
        # Simple pattern matching for v1
        # Future: Use proper expression evaluator
        
        # Check for unlock while away
        if "unlock_while_away" in condition or "lock.unlock" in condition:
            actions = automation.get("actions", automation.get("action", []))
            if not isinstance(actions, list):
                actions = [actions]
            
            for action in actions:
                service = action.get("service", "")
                if "lock.unlock" in service:
                    # Check for zone condition
                    conditions = automation.get("conditions", automation.get("condition", []))
                    if not isinstance(conditions, list):
                        conditions = [conditions] if conditions else []
                    
                    has_home_zone = any(
                        c.get("condition") == "zone" and c.get("zone") == "home"
                        for c in conditions
                    )
                    
                    if not has_home_zone and not overrides.get("allow_away_unlock"):
                        return True
        
        # Check for high power during peak
        if "high_power_during_peak" in condition or "allow_peak" in condition:
            actions = automation.get("actions", automation.get("action", []))
            if not isinstance(actions, list):
                actions = [actions]
            
            for action in actions:
                service = action.get("service", "")
                if service in ["climate.set_temperature", "switch.turn_on"]:
                    # Simple peak hours check (22:00-06:00 for example)
                    # Future: Integrate with utility peak hours API
                    from datetime import datetime
                    hour = datetime.now().hour
                    if (hour >= 22 or hour < 6) and not overrides.get("allow_peak"):
                        return True
        
        # Check for camera/mic after hours
        if "camera_mic_after_hours" in condition:
            actions = automation.get("actions", automation.get("action", []))
            if not isinstance(actions, list):
                actions = [actions]
            
            for action in actions:
                service = action.get("service", "")
                if service in ["camera.turn_on", "camera.enable_motion_detection"]:
                    from datetime import datetime
                    if datetime.now().hour >= 22:
                        return True
        
        # Check for bulk device off
        if "bulk_device_off" in condition:
            actions = automation.get("actions", automation.get("action", []))
            if not isinstance(actions, list):
                actions = [actions]
            
            for action in actions:
                target = action.get("target", {})
                entity_ids = target.get("entity_id", [])
                if isinstance(entity_ids, str):
                    entity_ids = [entity_ids]
                
                if len(entity_ids) > 5 or target.get("area_id") == "all":
                    return True
        
        return False

