"""
Home Assistant Blueprint Pattern Library

Stores Home Assistant blueprint patterns for common automation types.
Provides pattern matching and blueprint parameter extraction.
"""

import logging
from typing import Any

from .schema import HomeIQAutomation

logger = logging.getLogger(__name__)


class BlueprintPattern:
    """Represents a Home Assistant blueprint pattern."""
    
    def __init__(
        self,
        name: str,
        description: str,
        blueprint_yaml: str,
        match_criteria: dict[str, Any],
        parameters: dict[str, Any]
    ):
        """
        Initialize blueprint pattern.
        
        Args:
            name: Blueprint name
            description: Blueprint description
            blueprint_yaml: Blueprint YAML template
            match_criteria: Criteria for matching automations to this blueprint
            parameters: Blueprint input parameters
        """
        self.name = name
        self.description = description
        self.blueprint_yaml = blueprint_yaml
        self.match_criteria = match_criteria
        self.parameters = parameters


class BlueprintPatternLibrary:
    """
    Library of Home Assistant blueprint patterns.
    
    Features:
    - Pattern matching (match HomeIQ JSON to blueprint templates)
    - Blueprint parameter extraction
    - Blueprint YAML generation
    """
    
    def __init__(self):
        """Initialize blueprint pattern library."""
        self.patterns: list[BlueprintPattern] = []
        self._load_default_patterns()
    
    def _load_default_patterns(self):
        """Load default blueprint patterns."""
        # Motion Light Pattern
        motion_light_pattern = BlueprintPattern(
            name="motion_light",
            description="Turn on light when motion is detected",
            blueprint_yaml="""blueprint:
  name: Motion Light
  description: Turn a light on based on detected motion
  domain: automation
  input:
    motion_sensor:
      name: Motion Sensor
      selector:
        entity:
          domain: binary_sensor
          device_class: motion
    target_light:
      name: Target Light
      selector:
        entity:
          domain: light
    delay_off:
      name: Turn Off Delay
      default: 300
      selector:
        number:
          min: 0
          max: 3600
          unit_of_measurement: seconds

trigger:
  - platform: state
    entity_id: !input motion_sensor
    to: "on"

action:
  - service: light.turn_on
    target: !input target_light
  - delay: !input delay_off
  - service: light.turn_off
    target: !input target_light
""",
            match_criteria={
                "trigger_platform": "state",
                "trigger_to": "on",
                "action_service": "light.turn_on",
                "has_delay": True
            },
            parameters={
                "motion_sensor": "entity_id",
                "target_light": "target.entity_id",
                "delay_off": "delay"
            }
        )
        
        # Time-Based Pattern
        time_based_pattern = BlueprintPattern(
            name="time_based",
            description="Automation triggered by time",
            blueprint_yaml="""blueprint:
  name: Time-Based Automation
  description: Automation triggered at specific time
  domain: automation
  input:
    time:
      name: Time
      selector:
        time:
    target_entity:
      name: Target Entity
      selector:
        entity:

trigger:
  - platform: time
    at: !input time

action:
  - service: homeassistant.turn_on
    target: !input target_entity
""",
            match_criteria={
                "trigger_platform": "time"
            },
            parameters={
                "time": "trigger.at",
                "target_entity": "action.target.entity_id"
            }
        )
        
        # State Change Pattern
        state_change_pattern = BlueprintPattern(
            name="state_change",
            description="Automation triggered by state change",
            blueprint_yaml="""blueprint:
  name: State Change Automation
  description: Automation triggered by entity state change
  domain: automation
  input:
    entity_id:
      name: Entity
      selector:
        entity:
    from_state:
      name: From State
      selector:
        text:
    to_state:
      name: To State
      selector:
        text:
    action_service:
      name: Action Service
      selector:
        service:

trigger:
  - platform: state
    entity_id: !input entity_id
    from: !input from_state
    to: !input to_state

action:
  - service: !input action_service
    target:
      entity_id: !input entity_id
""",
            match_criteria={
                "trigger_platform": "state",
                "has_from_state": True,
                "has_to_state": True
            },
            parameters={
                "entity_id": "trigger.entity_id",
                "from_state": "trigger.from",
                "to_state": "trigger.to",
                "action_service": "action.service"
            }
        )
        
        self.patterns = [
            motion_light_pattern,
            time_based_pattern,
            state_change_pattern
        ]
    
    def find_matching_blueprint(
        self,
        automation: HomeIQAutomation
    ) -> BlueprintPattern | None:
        """
        Find matching blueprint pattern for HomeIQ automation.
        
        Args:
            automation: HomeIQ automation to match
        
        Returns:
            Matching BlueprintPattern or None
        """
        for pattern in self.patterns:
            if self._matches_pattern(automation, pattern):
                logger.debug(f"Found matching blueprint: {pattern.name}")
                return pattern
        
        return None
    
    def _matches_pattern(
        self,
        automation: HomeIQAutomation,
        pattern: BlueprintPattern
    ) -> bool:
        """Check if automation matches blueprint pattern criteria."""
        criteria = pattern.match_criteria
        
        # Check trigger platform
        if "trigger_platform" in criteria:
            trigger_platforms = [t.platform for t in automation.triggers]
            if criteria["trigger_platform"] not in trigger_platforms:
                return False
        
        # Check trigger state
        if "trigger_to" in criteria:
            trigger_states = [t.to for t in automation.triggers if t.to]
            if criteria["trigger_to"] not in trigger_states:
                return False
        
        # Check action service
        if "action_service" in criteria:
            action_services = [a.service for a in automation.actions if a.service]
            if criteria["action_service"] not in action_services:
                return False
        
        # Check for delay
        if criteria.get("has_delay", False):
            has_delay = any(a.delay for a in automation.actions if a.delay)
            if not has_delay:
                return False
        
        # Check for from/to states
        if criteria.get("has_from_state", False):
            has_from = any(t.from_state for t in automation.triggers if t.from_state)
            if not has_from:
                return False
        
        if criteria.get("has_to_state", False):
            has_to = any(t.to for t in automation.triggers if t.to)
            if not has_to:
                return False
        
        return True
    
    def extract_blueprint_parameters(
        self,
        automation: HomeIQAutomation,
        pattern: BlueprintPattern
    ) -> dict[str, Any]:
        """
        Extract blueprint parameters from HomeIQ automation.
        
        Args:
            automation: HomeIQ automation
            pattern: Blueprint pattern to extract parameters for
        
        Returns:
            Dictionary of blueprint parameters
        """
        parameters: dict[str, Any] = {}
        
        for param_name, param_path in pattern.parameters.items():
            value = self._extract_value_by_path(automation, param_path)
            if value is not None:
                parameters[param_name] = value
        
        return parameters
    
    def _extract_value_by_path(
        self,
        automation: HomeIQAutomation,
        path: str
    ) -> Any:
        """Extract value from automation using dot-notation path."""
        parts = path.split(".")
        current: Any = automation
        
        for part in parts:
            if isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            elif hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def generate_blueprint_yaml(
        self,
        automation: HomeIQAutomation,
        pattern: BlueprintPattern
    ) -> str:
        """
        Generate blueprint YAML from HomeIQ automation and pattern.
        
        Args:
            automation: HomeIQ automation
            pattern: Blueprint pattern to use
        
        Returns:
            Blueprint YAML string
        """
        # Extract parameters
        parameters = self.extract_blueprint_parameters(automation, pattern)
        
        # For now, return the template blueprint
        # In a full implementation, we would substitute parameters
        return pattern.blueprint_yaml
    
    def add_pattern(self, pattern: BlueprintPattern):
        """Add a custom blueprint pattern to the library."""
        self.patterns.append(pattern)
        logger.info(f"Added blueprint pattern: {pattern.name}")

