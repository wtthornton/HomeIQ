"""
YAML Structure Validator for Home Assistant Automations

Validates generated YAML structure to ensure 100% accuracy before deployment.
Catches common LLM mistakes like:
- Using 'trigger:' instead of 'platform:' in triggers
- Using 'action:' instead of 'service:' inside action lists
- Using plural keys ('triggers:', 'actions:') instead of singular
- Incorrect sequence structure
"""

import logging
import re
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of YAML structure validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    fixed_yaml: Optional[str] = None


class YAMLStructureValidator:
    """
    Validates YAML structure against Home Assistant automation requirements.
    
    Catches and can auto-fix common structural errors:
    - Wrong field names (trigger vs platform, action vs service)
    - Plural vs singular keys
    - Incorrect nesting
    """
    
    def validate(self, yaml_str: str) -> ValidationResult:
        """
        Validate YAML structure.
        
        Args:
            yaml_str: YAML string to validate
            
        Returns:
            ValidationResult with validation status and any fixes
        """
        errors = []
        warnings = []
        
        # Parse YAML
        try:
            data = yaml.safe_load(yaml_str)
        except yaml.YAMLError as e:
            logger.error(f"❌ YAML parse error: {e}")
            return ValidationResult(
                is_valid=False,
                errors=[f"YAML parse error: {e}"],
                warnings=[],
                fixed_yaml=None
            )
        
        if not data:
            return ValidationResult(
                is_valid=False,
                errors=["Empty or invalid YAML"],
                warnings=[],
                fixed_yaml=None
            )
        
        # Check for plural keys (common mistake)
        if 'triggers' in data:
            errors.append("❌ Found 'triggers:' (plural) - should be 'trigger:' (singular)")
        
        if 'actions' in data:
            errors.append("❌ Found 'actions:' (plural) - should be 'action:' (singular)")
        
        # Check trigger structure
        triggers = data.get('trigger', data.get('triggers', []))
        trigger_fix_needed = False
        if isinstance(triggers, list):
            for i, trigger in enumerate(triggers):
                if isinstance(trigger, dict):
                    # Check for wrong field name
                    if 'trigger' in trigger and trigger.get('trigger') == 'state':
                        errors.append(
                            f"❌ Trigger {i+1}: Found 'trigger: state' - should be 'platform: state'"
                        )
                    
                    # CRITICAL FIX: If trigger: time has minutes/hours/seconds, it should be trigger: time_pattern
                    # Also fix if 'at' field contains cron expressions (like '/10 * * * *')
                    trigger_type = trigger.get('trigger', trigger.get('platform', ''))
                    if trigger_type == 'time':
                        at_value = trigger.get('at')
                        has_interval_fields = 'minutes' in trigger or 'hours' in trigger or 'seconds' in trigger
                        has_cron_in_at = False
                        minutes_value = None
                        
                        # Check if 'at' contains a cron expression (e.g., '/10 * * * *')
                        if at_value:
                            if isinstance(at_value, list) and len(at_value) > 0:
                                at_value = at_value[0]
                            if isinstance(at_value, str):
                                # Check for cron pattern: starts with '/' or contains '*'
                                if at_value.startswith('/') or '*' in at_value:
                                    has_cron_in_at = True
                                    # Extract the interval (e.g., '/10' from '/10 * * * *')
                                    cron_match = re.match(r'^/(\d+)', at_value)
                                    if cron_match:
                                        minutes_value = f"/{cron_match.group(1)}"
                                        logger.info(f"🔧 Detected cron expression in 'at' field: {at_value}, extracting interval: {minutes_value}")
                        
                        if has_interval_fields or has_cron_in_at:
                            # This is a recurring interval - should use time_pattern
                            if has_cron_in_at:
                                errors.append(
                                    f"❌ Trigger {i+1}: Found 'trigger: time' with cron expression in 'at' field - "
                                    f"should be 'trigger: time_pattern' with 'minutes:' for recurring intervals"
                                )
                            else:
                                errors.append(
                                    f"❌ Trigger {i+1}: Found 'trigger: time' with 'minutes'/'hours'/'seconds' - "
                                    f"should be 'trigger: time_pattern' for recurring intervals"
                                )
                            
                            # Auto-fix: Change trigger type to time_pattern
                            if 'trigger' in trigger:
                                trigger['trigger'] = 'time_pattern'
                            elif 'platform' in trigger:
                                trigger['platform'] = 'time_pattern'
                            
                            # If we found a cron expression, convert it to minutes field
                            if has_cron_in_at and minutes_value:
                                # Remove the invalid 'at' field
                                if 'at' in trigger:
                                    del trigger['at']
                                # Add the correct 'minutes' field
                                trigger['minutes'] = minutes_value
                                logger.info(f"🔧 Converted cron expression to time_pattern with minutes: {minutes_value}")
                            
                            trigger_fix_needed = True
                            logger.info(f"🔧 Fixed trigger {i+1}: Changed 'trigger: time' to 'trigger: time_pattern'")
                    
                    # Check that platform exists (required for state triggers)
                    if 'entity_id' in trigger and 'platform' not in trigger:
                        if 'trigger' not in trigger:  # Only error if 'trigger' field exists (wrong)
                            warnings.append(
                                f"⚠️ Trigger {i+1}: Missing 'platform:' field (may need 'platform: state')"
                            )
        
        # Check action structure and fix service names
        actions = data.get('action', data.get('actions', []))
        service_fixes_applied = []
        
        def fix_services_in_structure(obj, path=""):
            """Recursively fix service names in actions, sequences, chooses, etc."""
            if isinstance(obj, dict):
                # Check if this is a service call
                if 'service' in obj:
                    service = obj.get('service', '')
                    target = obj.get('target', {})
                    entity_id = None
                    
                    # Extract entity_id from target
                    if isinstance(target, dict):
                        entity_id = target.get('entity_id')
                    elif isinstance(target, str):
                        entity_id = target
                    
                    # Handle list of entity IDs
                    if isinstance(entity_id, list) and len(entity_id) > 0:
                        entity_id = entity_id[0]
                    
                    # Fix WLED service names: wled.turn_on -> light.turn_on
                    if entity_id and isinstance(entity_id, str):
                        domain = entity_id.split('.')[0].lower() if '.' in entity_id else ''
                        
                        # WLED entities are lights - use light.turn_on, not wled.turn_on
                        if domain == 'wled':
                            if service == 'wled.turn_on':
                                obj['service'] = 'light.turn_on'
                                service_fixes_applied.append(f"{path}: wled.turn_on → light.turn_on (WLED entities use light service)")
                                logger.info(f"🔧 Fixed service: wled.turn_on → light.turn_on for {entity_id}")
                            elif service == 'wled.turn_off':
                                obj['service'] = 'light.turn_off'
                                service_fixes_applied.append(f"{path}: wled.turn_off → light.turn_off (WLED entities use light service)")
                                logger.info(f"🔧 Fixed service: wled.turn_off → light.turn_off for {entity_id}")
                            elif service.startswith('wled.'):
                                # Generic fix for any wled.* service
                                new_service = service.replace('wled.', 'light.', 1)
                                obj['service'] = new_service
                                service_fixes_applied.append(f"{path}: {service} → {new_service} (WLED entities use light service)")
                                logger.info(f"🔧 Fixed service: {service} → {new_service} for {entity_id}")
                
                # Recursively check nested structures
                for key, value in obj.items():
                    if key in ['action', 'sequence', 'repeat', 'choose', 'parallel']:
                        fix_services_in_structure(value, f"{path}.{key}" if path else key)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    fix_services_in_structure(item, f"{path}[{i}]" if path else f"[{i}]")
        
        # Fix services in the entire YAML structure
        fix_services_in_structure(actions, "action")
        
        if service_fixes_applied:
            logger.info(f"✅ Applied {len(service_fixes_applied)} service name fixes")
            # Regenerate YAML with fixes
            fixed_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
            warnings.extend(service_fixes_applied)
        else:
            fixed_yaml = None
        
        if isinstance(actions, list):
            for i, action in enumerate(actions):
                if isinstance(action, dict):
                    # Check if action has wrong 'action:' field (should be 'service:')
                    if 'action' in action and 'service' not in action:
                        errors.append(
                            f"❌ Action {i+1}: Found 'action:' field - should be 'service:' "
                            f"(e.g., 'service: light.turn_on' not 'action: light.turn_on')"
                        )
                    
                    # Check sequence structure
                    if 'sequence' in action:
                        sequence = action['sequence']
                        if isinstance(sequence, list):
                            for j, seq_item in enumerate(sequence):
                                if isinstance(seq_item, dict):
                                    # Check for wrong field name in sequence items
                                    if 'action' in seq_item and 'service' not in seq_item:
                                        errors.append(
                                            f"❌ Action {i+1}, sequence item {j+1}: "
                                            f"Found 'action:' - should be 'service:'"
                                        )
                                    
                                    # Delay items should have 'delay' field, not 'action'
                                    if 'delay' not in seq_item and 'action' in seq_item:
                                        errors.append(
                                            f"❌ Action {i+1}, sequence item {j+1}: "
                                            f"Non-delay items should use 'service:' not 'action:'"
                                        )
        
        # Auto-fix if errors found
        auto_fixed_yaml = None
        fixed_yaml = None
        if errors:
            auto_fixed_yaml = self._auto_fix(yaml_str, errors)
            if auto_fixed_yaml:
                # Validate the fixed version
                fixed_validation = self._validate_fixed(auto_fixed_yaml)
                if fixed_validation.is_valid:
                    logger.info("✅ Auto-fixed YAML structure errors")
                else:
                    logger.warning(f"⚠️ Auto-fix incomplete: {len(fixed_validation.errors)} errors remain")
        
        # Use the most complete fixed version
        # Priority: trigger_fix > service_fixes > auto_fix
        if trigger_fix_needed or service_fixes_applied:
            # Regenerate YAML with all fixes applied
            fixed_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
            if trigger_fix_needed:
                logger.info(f"🔧 Regenerated YAML with trigger fix applied (trigger_fix_needed=True)")
            if service_fixes_applied:
                logger.info(f"🔧 Regenerated YAML with service fixes applied ({len(service_fixes_applied)} fixes)")
        elif auto_fixed_yaml:
            fixed_yaml = auto_fixed_yaml
            logger.info(f"🔧 Using auto-fixed YAML from regex fixes")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            fixed_yaml=fixed_yaml
        )
    
    def _auto_fix(self, yaml_str: str, errors: List[str]) -> Optional[str]:
        """
        Attempt to auto-fix common YAML structure errors.
        
        Args:
            yaml_str: Original YAML string
            errors: List of error messages
            
        Returns:
            Fixed YAML string or None if auto-fix not possible
        """
        fixed = yaml_str
        
        try:
            # Fix 1: Plural keys → singular
            fixed = re.sub(r'^(\s*)triggers:', r'\1trigger:', fixed, flags=re.MULTILINE)
            fixed = re.sub(r'^(\s*)actions:', r'\1action:', fixed, flags=re.MULTILINE)
            
            # Fix 2: trigger: state → platform: state
            # Match indented "trigger: state" or "trigger:state"
            fixed = re.sub(
                r'(\n\s+)(-?\s*)trigger:\s*state\b',
                r'\1\2platform: state',
                fixed,
                flags=re.MULTILINE
            )
            
            # Fix 3: action: inside action list → service:
            # This is trickier - need to be careful about context
            # Only fix if it's clearly inside an action list (has indentation and looks like a service)
            
            # Pattern: action: domain.service (like action: light.turn_on)
            # Replace with service: domain.service
            lines = fixed.split('\n')
            fixed_lines = []
            in_action_list = False
            in_sequence = False
            
            for i, line in enumerate(lines):
                # Detect if we're in an action list
                if re.match(r'^\s*action:\s*$', line):
                    in_action_list = True
                    fixed_lines.append(line)
                    continue
                
                # Detect if we're in a sequence
                if re.match(r'^\s+-?\s*sequence:\s*$', line):
                    in_sequence = True
                    fixed_lines.append(line)
                    continue
                
                # Detect end of action list (next top-level key)
                if re.match(r'^[a-z_]+:', line) and not line.strip().startswith(' '):
                    if in_action_list and not any(line.strip().startswith(k) for k in ['trigger', 'action', 'condition', 'mode', 'alias', 'description', 'id']):
                        in_action_list = False
                        in_sequence = False
                
                # Detect end of sequence (less indentation)
                if in_sequence:
                    if not re.match(r'^\s{4,}', line) and not re.match(r'^\s*-\s*$', line):
                        in_sequence = False
                
                # Fix action: → service: inside action lists or sequences
                if in_action_list or in_sequence:
                    # Match: "    action: light.turn_on" or "      action: wled.turn_on"
                    if re.match(r'^(\s+)(-?\s*)action:\s+([a-z_]+\.[a-z_]+)', line):
                        line = re.sub(
                            r'^(\s+)(-?\s*)action:\s+',
                            r'\1\2service: ',
                            line
                        )
                        logger.debug(f"Fixed line {i+1}: action: → service:")
                
                fixed_lines.append(line)
            
            fixed = '\n'.join(fixed_lines)
            
            return fixed
            
        except Exception as e:
            logger.warning(f"⚠️ Auto-fix failed: {e}")
            return None
    
    def _validate_fixed(self, yaml_str: str) -> ValidationResult:
        """Validate the auto-fixed YAML"""
        return self.validate(yaml_str)

