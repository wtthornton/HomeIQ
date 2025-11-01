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
        if isinstance(triggers, list):
            for i, trigger in enumerate(triggers):
                if isinstance(trigger, dict):
                    # Check for wrong field name
                    if 'trigger' in trigger and trigger.get('trigger') == 'state':
                        errors.append(
                            f"❌ Trigger {i+1}: Found 'trigger: state' - should be 'platform: state'"
                        )
                    
                    # Check that platform exists (required for state triggers)
                    if 'entity_id' in trigger and 'platform' not in trigger:
                        if 'trigger' not in trigger:  # Only error if 'trigger' field exists (wrong)
                            warnings.append(
                                f"⚠️ Trigger {i+1}: Missing 'platform:' field (may need 'platform: state')"
                            )
        
        # Check action structure
        actions = data.get('action', data.get('actions', []))
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
        fixed_yaml = None
        if errors:
            fixed_yaml = self._auto_fix(yaml_str, errors)
            if fixed_yaml:
                # Validate the fixed version
                fixed_validation = self._validate_fixed(fixed_yaml)
                if fixed_validation.is_valid:
                    logger.info("✅ Auto-fixed YAML structure errors")
                else:
                    logger.warning(f"⚠️ Auto-fix incomplete: {len(fixed_validation.errors)} errors remain")
        
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

