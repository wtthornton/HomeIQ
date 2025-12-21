"""
Evaluation and scoring system for Ask AI automation results.

Provides scoring for:
- Automation correctness (prompt-specific and generic)
- YAML validity
- Total weighted score calculation
"""
import re
import yaml
from typing import Any, Callable

from .config import (
    AUTOMATION_SCORE_WEIGHT,
    YAML_SCORE_WEIGHT,
    CLARIFICATION_SCORE_WEIGHT
)
from .terminal_output import TerminalOutput


class Scorer:
    """Scoring system for automation correctness, YAML validity, and clarification count"""
    
    @staticmethod
    def _find_in_actions(actions: Any, predicate: Callable[[Any], bool]) -> bool:
        """Helper to search actions recursively"""
        if not isinstance(actions, list):
            return False
        for action in actions:
            if predicate(action):
                return True
            # Check nested sequences
            if isinstance(action, dict):
                if 'sequence' in action:
                    if Scorer._find_in_actions(action['sequence'], predicate):
                        return True
                if 'choose' in action:
                    for choice in action['choose']:
                        if Scorer._find_in_actions(choice.get('sequence', []), predicate):
                            return True
                    if 'default' in action:
                        if Scorer._find_in_actions(action['default'], predicate):
                            return True
        return False
    
    @staticmethod
    def score_automation_correctness(yaml_str: str, prompt: str, prompt_id: str = None) -> float:
        """
        Score automation correctness based on prompt requirements.
        Returns score 0-100. Uses prompt-specific scoring when available.
        """
        if not yaml_str:
            return 0.0
        
        try:
            yaml_data = yaml.safe_load(yaml_str)
        except yaml.YAMLError:
            return 0.0
        
        if not isinstance(yaml_data, dict):
            return 0.0
        
        # Use prompt-specific scorer if available (Python 3.10+ match/case)
        match prompt_id:
            case "prompt-12-very-complex":  # WLED state restoration prompt
                return Scorer._score_wled_prompt(yaml_data, yaml_str)
            case "prompt-14-extremely-complex":  # Complex conditional logic prompt
                return Scorer._score_complex_logic_prompt(yaml_data, yaml_str, prompt)
            case _:
                # Generic scoring for other prompts
                return Scorer._score_generic_prompt(yaml_data, yaml_str, prompt)
    
    @staticmethod
    def _score_generic_prompt(yaml_data: dict, yaml_str: str, prompt: str) -> float:
        """Generic scoring that checks for common automation patterns"""
        score = 0.0
        max_score = 100.0
        checks = []
        prompt_lower = prompt.lower()
        
        # Check 1: Has valid trigger (20 points)
        trigger = yaml_data.get('trigger', [])
        if isinstance(trigger, list) and len(trigger) > 0:
            score += 20.0
            checks.append("✓ Valid trigger found")
            # Bonus: Multiple triggers (5 points)
            if len(trigger) > 1:
                score += 5.0
                checks.append("✓ Multiple triggers found")
        else:
            checks.append("✗ No trigger found")
        
        # Check 2: Has valid actions (20 points)
        action = yaml_data.get('action', [])
        if isinstance(action, list) and len(action) > 0:
            score += 20.0
            checks.append("✓ Valid actions found")
            # Bonus: Multiple actions (5 points)
            if len(action) > 1:
                score += 5.0
                checks.append("✓ Multiple actions found")
        else:
            checks.append("✗ No actions found")
        
        # Check 3: Time-based requirements (20 points)
        time_keywords = ['time', '7:00', '8:00', '9:00', 'am', 'pm', 'sunset', 'sunrise', 'every day', 'daily']
        if any(keyword in prompt_lower for keyword in time_keywords):
            has_time_trigger = False
            for t in trigger:
                if isinstance(t, dict):
                    platform = t.get('platform', '')
                    if platform in ['time', 'time_pattern', 'sun', 'sunset', 'sunrise']:
                        has_time_trigger = True
                        break
            if has_time_trigger:
                score += 20.0
                checks.append("✓ Time-based trigger found")
            else:
                checks.append("✗ Time-based trigger not found")
        
        # Check 4: Device/entity usage (20 points)
        device_keywords = ['light', 'lights', 'wled', 'thermostat', 'speaker', 'door', 'motion']
        if any(word in prompt_lower for word in device_keywords):
            # Check for entity IDs in format domain.entity
            valid_entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
            entities_found = re.findall(valid_entity_pattern, yaml_str)
            valid_entities = [e for e in entities_found if not e.startswith('service:')]
            if valid_entities:
                score += 20.0
                checks.append(f"✓ Entity IDs found ({len(valid_entities)} entities)")
            else:
                # Partial credit if service calls found
                if 'service:' in yaml_str or 'service' in yaml_str.lower():
                    score += 10.0
                    checks.append("⚠ Service calls found but no entity IDs")
                else:
                    checks.append("✗ No entity IDs found")
        
        # Check 5: Conditional logic (20 points)
        if 'if' in prompt_lower or 'when' in prompt_lower or 'between' in prompt_lower:
            has_condition = (
                Scorer._find_in_actions(action, lambda a: 'condition' in a) or
                any('condition' in str(t) for t in trigger)
            )
            if has_condition or Scorer._find_in_actions(action, lambda a: 'choose' in a):
                score += 20.0
                checks.append("✓ Conditional logic found")
            else:
                checks.append("⚠ Conditional logic may be missing")
        
        if score < max_score:
            TerminalOutput.print_info(f"Automation correctness: {score:.1f}/100 ({len([c for c in checks if c.startswith('✓')])}/{len(checks)} checks passed)")
        return min(score, max_score)
    
    @staticmethod
    def _score_wled_prompt(yaml_data: dict, yaml_str: str) -> float:
        """Score the WLED prompt (prompt-12-very-complex)"""
        score = 0.0
        max_score = 100.0
        checks = []
        
        trigger = yaml_data.get('trigger', [])
        action = yaml_data.get('action', [])
        
        # Check 1: 15-minute interval trigger (20 points)
        trigger_found = False
        if isinstance(trigger, list) and len(trigger) > 0:
            for t in trigger:
                if isinstance(t, dict) and t.get('platform') == 'time_pattern':
                    minutes = str(t.get('minutes', ''))
                    if '/15' in minutes or '*/15' in minutes or minutes == '*/15':
                        score += 20.0
                        checks.append("✓ 15-minute interval trigger")
                        trigger_found = True
                        break
            if not trigger_found:
                checks.append("✗ 15-minute interval trigger not found")
        else:
            checks.append("✗ No trigger found")
        
        # Check 2: Random effect selection (15 points)
        def check_random_effect(action_item):
            data = action_item.get('data', {})
            return (
                action_item.get('service') == 'light.turn_on' and 
                ('random' in str(data.get('effect', '')).lower() or 
                 'random' in str(data.get('color_name', '')).lower())
            )
        
        if Scorer._find_in_actions(action, check_random_effect):
            score += 15.0
            checks.append("✓ Random effect selection")
        else:
            checks.append("✗ Random effect selection not found")
        
        # Check 3: 15-second duration (15 points)
        def check_duration(action_item):
            if 'delay' in action_item:
                delay = str(action_item['delay'])
                return '00:00:15' in delay or delay.strip() == '15' or delay.strip() == '15.0'
            return False
        
        if Scorer._find_in_actions(action, check_duration):
            score += 15.0
            checks.append("✓ 15-second duration")
        else:
            checks.append("✗ 15-second duration not found")
        
        # Check 4: Brightness 100% (15 points)
        def check_brightness(action_item):
            data = action_item.get('data', {})
            brightness = data.get('brightness_pct', '')
            return str(brightness) == '100' or brightness == 100
        
        if Scorer._find_in_actions(action, check_brightness):
            score += 15.0
            checks.append("✓ Brightness 100%")
        else:
            checks.append("✗ Brightness 100% not found")
        
        # Check 5: State restoration (20 points)
        has_snapshot = Scorer._find_in_actions(action, lambda a: a.get('service') == 'scene.create')
        has_restore = Scorer._find_in_actions(action, lambda a: a.get('service') == 'scene.turn_on')
        
        if has_snapshot and has_restore:
            score += 20.0
            checks.append("✓ State restoration logic (snapshot & restore)")
        elif has_snapshot or has_restore:
            score += 10.0
            checks.append("⚠ Partial state restoration")
        else:
            checks.append("✗ State restoration not found")
        
        # Check 6: Office WLED device entity (15 points)
        def check_entity(action_item):
            target = action_item.get('target', {})
            entity_id = target.get('entity_id', '')
            if isinstance(entity_id, list):
                entity_id = ' '.join(entity_id)
            return 'office' in entity_id.lower() and ('wled' in entity_id.lower() or 'light' in entity_id.lower())
        
        if Scorer._find_in_actions(action, check_entity):
            score += 15.0
            checks.append("✓ Office WLED device")
        else:
            checks.append("✗ Office WLED device not found")
        
        if score < max_score:
            TerminalOutput.print_info(f"Automation correctness: {score:.1f}/100 ({len([c for c in checks if c.startswith('✓')])}/{len(checks)} checks passed)")
        return min(score, max_score)
    
    @staticmethod
    def _score_complex_logic_prompt(yaml_data: dict, yaml_str: str, prompt: str) -> float:
        """Score the extremely complex prompt (prompt-14-extremely-complex)"""
        score = 0.0
        max_score = 100.0
        checks = []
        prompt_lower = prompt.lower()
        
        trigger = yaml_data.get('trigger', [])
        action = yaml_data.get('action', [])
        
        # Check 1: WiFi/device tracker trigger (15 points)
        has_wifi_trigger = False
        for t in trigger:
            if isinstance(t, dict):
                platform = t.get('platform', '')
                if platform in ['device_tracker', 'zone']:
                    has_wifi_trigger = True
                    break
                entity_id = t.get('entity_id', '')
                if isinstance(entity_id, str) and 'wifi' in entity_id.lower():
                    has_wifi_trigger = True
                    break
        if has_wifi_trigger:
            score += 15.0
            checks.append("✓ WiFi/arrival trigger found")
        else:
            checks.append("✗ WiFi/arrival trigger not found")
        
        # Check 2: Time-based conditions (20 points)
        has_time_condition = Scorer._find_in_actions(action, lambda a: 'condition' in a and any(
            'time' in str(c).lower() or 'sun' in str(c).lower() for c in a.get('condition', [])
        ))
        if has_time_condition or Scorer._find_in_actions(action, lambda a: 'choose' in a):
            score += 20.0
            checks.append("✓ Time-based conditions found")
        else:
            checks.append("✗ Time-based conditions not found")
        
        # Check 3: Multiple time ranges (20 points)
        if '6 am' in prompt_lower and '9 am' in prompt_lower and '5 pm' in prompt_lower and '8 pm' in prompt_lower:
            has_multiple_ranges = Scorer._find_in_actions(action, lambda a: 'choose' in a)
            if has_multiple_ranges:
                score += 20.0
                checks.append("✓ Multiple time ranges (choose statement)")
            else:
                checks.append("✗ Multiple time ranges not found")
        
        # Check 4: Multiple device actions (15 points)
        def count_actions(actions, predicate):
            count = 0
            if not isinstance(actions, list):
                return 0
            for a in actions:
                if predicate(a):
                    count += 1
                if 'sequence' in a:
                    count += count_actions(a['sequence'], predicate)
                if 'choose' in a:
                    for choice in a['choose']:
                        count += count_actions(choice.get('sequence', []), predicate)
                    if 'default' in a:
                        count += count_actions(a['default'], predicate)
            return count
        
        light_actions = count_actions(action, lambda a: 'light' in str(a.get('service', '')).lower())
        other_actions = count_actions(action, lambda a: 
            'media_player' in str(a.get('service', '')).lower() or 
            'climate' in str(a.get('service', '')).lower() or
            'notify' in str(a.get('service', '')).lower()
        )
        if light_actions > 0 and other_actions > 0:
            score += 15.0
            checks.append("✓ Multiple device types (lights + other)")
        else:
            checks.append("⚠ Limited device variety")
        
        # Check 5: Delay/wait logic (15 points)
        has_delay = Scorer._find_in_actions(action, lambda a: 'delay' in a)
        if has_delay:
            score += 15.0
            checks.append("✓ Delay/wait logic found")
        else:
            checks.append("✗ Delay/wait logic not found")
        
        # Check 6: Notification action (15 points)
        has_notify = Scorer._find_in_actions(action, lambda a: 'notify' in str(a.get('service', '')).lower())
        if has_notify:
            score += 15.0
            checks.append("✓ Notification action found")
        else:
            checks.append("✗ Notification action not found")
        
        if score < max_score:
            TerminalOutput.print_info(f"Automation correctness: {score:.1f}/100 ({len([c for c in checks if c.startswith('✓')])}/{len(checks)} checks passed)")
        return min(score, max_score)
    
    @staticmethod
    def score_yaml_validity(yaml_str: str) -> float:
        """
        Score YAML validity and Home Assistant structure.
        Returns score 0-100.
        """
        if not yaml_str:
            return 0.0
        
        score = 0.0
        max_score = 100.0
        checks = []
        
        # Check 1: Valid YAML syntax (40 points)
        try:
            yaml_data = yaml.safe_load(yaml_str)
            if yaml_data is not None:
                score += 40.0
                checks.append("✓ Valid YAML syntax")
            else:
                checks.append("✗ YAML is empty")
                return 0.0
        except yaml.YAMLError as e:
            checks.append(f"✗ Invalid YAML syntax: {e}")
            return 0.0
        
        if not isinstance(yaml_data, dict):
            checks.append("✗ YAML root is not a dictionary")
            return 0.0
        
        # Check 2: Required fields (30 points)
        required_fields = ['id', 'alias', 'trigger', 'action']
        missing_fields = []
        for field in required_fields:
            if field in yaml_data:
                score += 7.5
                checks.append(f"✓ Required field '{field}' present")
            else:
                missing_fields.append(field)
                checks.append(f"✗ Required field '{field}' missing")
        
        # Check 3: Valid HA structure (20 points)
        trigger = yaml_data.get('trigger', [])
        action = yaml_data.get('action', [])
        
        if isinstance(trigger, list) and len(trigger) > 0:
            score += 10.0
            checks.append("✓ Trigger is a list")
        else:
            checks.append("✗ Trigger is not a valid list")
        
        if isinstance(action, list) and len(action) > 0:
            score += 10.0
            checks.append("✓ Action is a list")
        else:
            checks.append("✗ Action is not a valid list")
        
        # Check 4: Valid entity IDs format (10 points)
        entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
        if re.search(entity_pattern, yaml_str):
            score += 10.0
            checks.append("✓ Valid entity ID format")
        else:
            checks.append("✗ No valid entity IDs found")
        
        # Log checks (but don't print all details in terminal to reduce noise)
        if score < max_score:
            TerminalOutput.print_info(f"YAML validity: {score:.1f}/100 ({len([c for c in checks if c.startswith('✓')])}/{len(checks)} checks passed)")
        return min(score, max_score)
    
    @staticmethod
    def count_clarifications(session_log: list[dict[str, Any]]) -> int:
        """Count clarification rounds"""
        return len(session_log)
    
    @staticmethod
    def calculate_total_score(automation_score: float, yaml_score: float, 
                             clarification_count: int) -> dict[str, Any]:
        """
        Calculate weighted total score.
        Weights: automation (50%), YAML (30%), clarifications (20% - lower is better)
        """
        # Clarification score: 100 - (count * penalty), minimum 0
        clarification_penalty = 5.0
        clarification_score = max(0.0, 100.0 - (clarification_count * clarification_penalty))
        
        # Weighted total
        total = (
            automation_score * AUTOMATION_SCORE_WEIGHT +
            yaml_score * YAML_SCORE_WEIGHT +
            clarification_score * CLARIFICATION_SCORE_WEIGHT
        )
        
        return {
            'automation_score': automation_score,
            'yaml_score': yaml_score,
            'clarification_count': clarification_count,
            'clarification_score': clarification_score,
            'total_score': total,
            'weights': {
                'automation': AUTOMATION_SCORE_WEIGHT,
                'yaml': YAML_SCORE_WEIGHT,
                'clarifications': CLARIFICATION_SCORE_WEIGHT
            }
        }

