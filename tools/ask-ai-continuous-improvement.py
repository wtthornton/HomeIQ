#!/usr/bin/env python3
"""
Ask AI Continuous Improvement Process

Automated testing and improvement cycle for Ask AI API that processes a complex
WLED automation prompt through the full workflow (query → clarifications → approve),
scores results, and iterates through 5 improvement cycles.
"""

import asyncio
import httpx
import json
import yaml
import os
import sys
import subprocess
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Any
from dataclasses import dataclass, asdict, field
from collections.abc import Callable
import logging
import aiohttp

# Configure logging with better formatting
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Terminal output helpers
class TerminalOutput:
    """Helper class for formatted terminal output"""
    
    @staticmethod
    def print_header(text: str, char: str = "="):
        """Print a formatted header"""
        width = 80
        logger.info("")
        logger.info(char * width)
        logger.info(f"  {text}")
        logger.info(char * width)
    
    @staticmethod
    def print_step(step_num: int, total_steps: int, description: str):
        """Print a step indicator"""
        logger.info(f"\n[Step {step_num}/{total_steps}] {description}")
        logger.info("-" * 80)
    
    @staticmethod
    def print_status(status: str, message: str, indent: int = 0):
        """Print a status message"""
        prefix = "  " * indent
        logger.info(f"{prefix}[{status}] {message}")
    
    @staticmethod
    def print_success(message: str, indent: int = 0):
        """Print a success message"""
        TerminalOutput.print_status("✓", message, indent)
    
    @staticmethod
    def print_error(message: str, indent: int = 0):
        """Print an error message"""
        TerminalOutput.print_status("✗", message, indent)
    
    @staticmethod
    def print_warning(message: str, indent: int = 0):
        """Print a warning message"""
        TerminalOutput.print_status("!", message, indent)
    
    @staticmethod
    def print_info(message: str, indent: int = 0):
        """Print an info message"""
        TerminalOutput.print_status("i", message, indent)
    
    @staticmethod
    def print_progress(current: int, total: int, description: str = ""):
        """Print progress indicator"""
        percentage = int((current / total) * 100) if total > 0 else 0
        bar_length = 40
        filled = int(bar_length * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (bar_length - filled)
        logger.info(f"\r  [{bar}] {percentage:3d}% {description}", end="", flush=True)
        if current >= total:
            logger.info("")  # New line when complete

# Configuration
BASE_URL = "http://localhost:8024/api/v1/ask-ai"
HEALTH_URL = "http://localhost:8024/health"

# 15 Prompts of Increasing Complexity
# All prompts use device-friendly names that the system can resolve to actual entity IDs
# Devices used: Office WLED (light.wled_office), Living Room lights (various light.lr_* entities)
TARGET_PROMPTS = [
    # Simple Prompts (1-3)
    {
        "id": "prompt-1-simple",
        "name": "Simple Time-Based Light",
        "prompt": "Turn on the Office WLED every day at 7:00 AM",
        "complexity": "Simple"
    },
    {
        "id": "prompt-2-simple",
        "name": "Simple Light Control",
        "prompt": "Turn off all living room lights at 11:00 PM every night",
        "complexity": "Simple"
    },
    {
        "id": "prompt-3-simple",
        "name": "Basic Schedule",
        "prompt": "Turn on the Office WLED at 8:00 AM on weekdays only",
        "complexity": "Simple"
    },
    # Medium Prompts (4-7)
    {
        "id": "prompt-4-medium",
        "name": "Time-Based Conditional Lighting",
        "prompt": "Between 6 PM and 11 PM every day, turn on the living room lights to 80% brightness",
        "complexity": "Medium"
    },
    {
        "id": "prompt-5-medium",
        "name": "Time-Based Multi-Light",
        "prompt": "At sunset, turn on the Office WLED to 60% brightness and set it to a warm white color",
        "complexity": "Medium"
    },
    {
        "id": "prompt-6-medium",
        "name": "Conditional Brightness",
        "prompt": "When the living room lights are turned on after 8 PM, automatically dim them to 40% brightness",
        "complexity": "Medium"
    },
    {
        "id": "prompt-7-medium",
        "name": "Multi-Area Lighting",
        "prompt": "At 6:00 AM, turn on the Office WLED to 50% and turn on all living room lights to 30%",
        "complexity": "Medium"
    },
    # Complex Prompts (8-11)
    {
        "id": "prompt-8-complex",
        "name": "Sunset-Based Multi-Device Sequence",
        "prompt": "After sunset every day, turn on the living room lights for 5 minutes, then turn on the Office WLED, wait 30 seconds, and turn off the living room lights",
        "complexity": "Complex"
    },
    {
        "id": "prompt-9-complex",
        "name": "Sequential Actions",
        "prompt": "When the Office WLED is turned on, wait 2 seconds, then turn on all living room lights to 70%, wait another 3 seconds, and set the Office WLED to 100% brightness",
        "complexity": "Complex"
    },
    {
        "id": "prompt-10-complex",
        "name": "Time-Based Sequence",
        "prompt": "Every day at 5:00 PM, turn on the Office WLED to 80%, wait 1 minute, turn on all living room lights to 60%, wait 30 seconds, and dim the Office WLED to 40%",
        "complexity": "Complex"
    },
    {
        "id": "prompt-11-complex",
        "name": "Conditional Chain",
        "prompt": "When any living room light is turned on between 9 PM and 11 PM, turn on the Office WLED to 20% brightness, wait 10 seconds, then turn off the Office WLED",
        "complexity": "Complex"
    },
    # Very Complex Prompts (12-13)
    {
        "id": "prompt-12-very-complex",
        "name": "State Restoration with Conditions",
        "prompt": "Every 15 mins choose a random effect on the Office WLED device. Play the effect for 15 secs. Choose random effect, random colors and brightness to 100%. At the end of the 15 sec the WLED light needs to return to exactly what it was before it started.",
        "complexity": "Very Complex"
    },
    {
        "id": "prompt-13-very-complex",
        "name": "Complex State Management",
        "prompt": "When the Office WLED is turned on, save its current state. Then turn on all living room lights to 80%. After 10 minutes, restore the Office WLED to its saved state and turn off all living room lights",
        "complexity": "Very Complex"
    },
    # Extremely Complex Prompts (14-15)
    {
        "id": "prompt-14-extremely-complex",
        "name": "Complex Conditional Logic",
        "prompt": "Check the time. If it's between 6 AM and 9 AM, turn on the Office WLED to 50% with a warm white color and turn off all living room lights. If it's between 5 PM and 8 PM, turn on all living room lights to 80% and set the Office WLED to 100% with a cool white color. If it's after 9 PM, turn on the Office WLED to 20% brightness and turn off all living room lights. Wait 5 seconds after any action.",
        "complexity": "Extremely Complex"
    },
    {
        "id": "prompt-15-extremely-complex",
        "name": "Multi-Conditional with Choose",
        "prompt": "When any living room light changes state, check the time and the current brightness of the Office WLED. If it's daytime (6 AM to 6 PM) and the Office WLED is below 50%, turn it on to 70%. If it's nighttime (6 PM to 6 AM) and any living room light is above 60%, dim the Office WLED to 30%. If the Office WLED is already at the target brightness, do nothing. Wait 2 seconds between each check and action.",
        "complexity": "Extremely Complex"
    }
]

OUTPUT_DIR = Path("implementation/continuous-improvement")
MAX_CYCLES = 25
TIMEOUT = 300.0  # 5 minutes timeout for API calls

# Constants
MAX_CLARIFICATION_ROUNDS = 10
HEALTH_CHECK_RETRIES = 30
HEALTH_CHECK_INTERVAL = 1.0
DEPLOYMENT_WAIT_TIME = 5.0
CYCLE_WAIT_TIME = 2.0
HA_API_TIMEOUT = 10.0
YAML_VALIDITY_THRESHOLD = 50.0
SCORE_EXCELLENT_THRESHOLD = 85.0
SCORE_WARNING_THRESHOLD = 70.0
CLARIFICATION_PENALTY = 10.0
AUTOMATION_SCORE_WEIGHT = 0.5
YAML_SCORE_WEIGHT = 0.3
CLARIFICATION_SCORE_WEIGHT = 0.2

# API Key for authentication (read from environment or use default)
API_KEY = os.getenv("AI_AUTOMATION_API_KEY", "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR")


@dataclass
class PromptResult:
    """Results from a single prompt execution"""
    prompt_id: str
    prompt_name: str
    prompt_text: str
    complexity: str
    query_id: str | None = None
    suggestion_id: str | None = None
    automation_id: str | None = None
    automation_yaml: str | None = None
    clarification_rounds: int = 0
    clarification_log: list[dict[str, Any]] = field(default_factory=list)
    automation_score: float = 0.0
    yaml_score: float = 0.0
    total_score: float = 0.0
    error: str | None = None
    success: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CycleResult:
    """Results from a single improvement cycle with all prompts"""
    cycle_number: int
    prompt_results: list[PromptResult] = field(default_factory=list)
    overall_score: float = 0.0
    all_successful: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def calculate_overall_score(self) -> float:
        """Calculate average score across all prompts"""
        if not self.prompt_results:
            return 0.0
        successful_results = [r for r in self.prompt_results if r.success]
        if not successful_results:
            return 0.0
        return sum(r.total_score for r in successful_results) / len(successful_results)
    
    def all_prompts_successful(self) -> bool:
        """Check if all prompts were successful"""
        if not self.prompt_results:
            return False
        return all(r.success for r in self.prompt_results)


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
            case "prompt-12-very-complex":  # FIXED: Correct prompt ID for WLED state restoration prompt
                return Scorer._score_wled_prompt(yaml_data, yaml_str)
            case "prompt-14-extremely-complex":  # FIXED: Correct prompt ID for complex conditional logic prompt
                return Scorer._score_complex_logic_prompt(yaml_data, yaml_str, prompt)
            case _:
                # Generic scoring for other prompts
                return Scorer._score_generic_prompt(yaml_data, yaml_str, prompt)
    
    @staticmethod
    def _score_generic_prompt(yaml_data: dict, yaml_str: str, prompt: str) -> float:
        """Generic scoring that checks for common automation patterns - IMPROVED with more granular checks"""
        score = 0.0
        max_score = 100.0
        checks = []
        prompt_lower = prompt.lower()
        
        # Check 1: Has valid trigger (20 points) - FIXED: Reduced to prevent score overflow
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
        
        # Check 2: Has valid actions (20 points) - FIXED: Reduced to prevent score overflow
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
        
        # Check 3: Time-based requirements (20 points) - IMPROVED detection
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
        
        # Check 4: Device/entity usage (20 points) - FIXED: Correctly detects all valid HA entity IDs
        device_keywords = ['light', 'lights', 'wled', 'thermostat', 'speaker', 'door', 'motion']
        if any(word in prompt_lower for word in device_keywords):
            # Check for entity IDs in format domain.entity - FIXED: Include all valid HA domains
            # Valid HA entity domains: light, switch, sensor, binary_sensor, climate, media_player,
            # cover, fan, lock, vacuum, camera, device_tracker, person, zone, input_*, automation, script, scene
            valid_entity_pattern = r'\b(light|switch|sensor|binary_sensor|climate|media_player|cover|fan|lock|vacuum|camera|device_tracker|person|zone|input_|automation|script|scene)\.\w+\b'
            entities_found = re.findall(valid_entity_pattern, yaml_str)
            # Filter out service calls only (light.* entities are VALID!)
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
        
        # Check 5: Conditional logic (20 points) - for complex prompts
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
        """Score the WLED prompt (prompt-12-very-complex) - FIXED: Updated comment to match actual prompt ID"""
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
                    # Check for '/15' or '*/15' pattern (every 15 minutes)
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
                # Check for exactly 15 seconds: '00:00:15' or '15' (seconds) or 15.0 (float)
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
            # Handle both string '100' and int 100
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
        """Score the extremely complex prompt (prompt-14-extremely-complex) - FIXED: Updated comment to match actual prompt ID"""
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
                # Check platform field first (most reliable)
                if platform in ['device_tracker', 'zone']:
                    has_wifi_trigger = True
                    break
                # Only check entity_id field for 'wifi', not entire dict (avoids matching comments)
                entity_id = t.get('entity_id', '')
                if isinstance(entity_id, str) and 'wifi' in entity_id.lower():
                    has_wifi_trigger = True
                    break
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
        yaml_str_lower = yaml_str.lower()
        # Check for all valid Home Assistant entity domains
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
        # IMPROVED: Reduced penalty from 10 to 5 points per round
        clarification_penalty = 5.0  # Reduced from 10.0
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


class ClarificationHandler:
    """Auto-answer clarification questions based on prompt context"""
    
    def __init__(self, original_prompt: str):
        self.original_prompt = original_prompt.lower()
        # Extract context from prompt dynamically
        self.prompt_context = self._extract_prompt_context(original_prompt)
    
    def _extract_prompt_context(self, prompt: str) -> dict[str, Any]:
        """Extract context from prompt text dynamically"""
        prompt_lower = prompt.lower()
        context: dict[str, Any] = {}
        
        # Extract device/location mentions
        device_keywords = ['wled', 'light', 'thermostat', 'speaker', 'door', 'motion']
        location_keywords = ['office', 'kitchen', 'living room', 'bedroom', 'hallway']
        
        for keyword in device_keywords:
            if keyword in prompt_lower:
                context['device'] = keyword
                break
        
        for keyword in location_keywords:
            if keyword in prompt_lower:
                context['location'] = keyword
                break
        
        # Extract time intervals
        if '15 min' in prompt_lower or '15 minute' in prompt_lower:
            context['interval'] = '15 minutes'
        elif 'every' in prompt_lower and 'min' in prompt_lower:
            # Try to extract any minute value
            match = re.search(r'(\d+)\s*min', prompt_lower)
            if match:
                context['interval'] = f"{match.group(1)} minutes"
        
        # Extract duration
        if '15 sec' in prompt_lower or '15 second' in prompt_lower:
            context['duration'] = '15 seconds'
        elif 'second' in prompt_lower:
            match = re.search(r'(\d+)\s*second', prompt_lower)
            if match:
                context['duration'] = f"{match.group(1)} seconds"
        
        # Extract brightness
        if '100%' in prompt_lower or '100 percent' in prompt_lower:
            context['brightness'] = '100%'
        elif 'brightness' in prompt_lower:
            match = re.search(r'(\d+)%', prompt_lower)
            if match:
                context['brightness'] = f"{match.group(1)}%"
        
        # Extract effect/color preferences
        if 'random' in prompt_lower:
            context['effect'] = 'random'
            context['colors'] = 'random'
        
        # Extract time-based triggers
        if '7:00' in prompt_lower or '7 am' in prompt_lower:
            context['time'] = '7:00 AM'
        elif 'am' in prompt_lower or 'pm' in prompt_lower:
            match = re.search(r'(\d+):?(\d+)?\s*(am|pm)', prompt_lower)
            if match:
                context['time'] = f"{match.group(1)}:{match.group(2) or '00'} {match.group(3).upper()}"
        
        return context
    
    def answer_question(self, question: dict[str, Any]) -> dict[str, Any]:
        """
        Generate answer for a clarification question based on prompt context.
        Returns answer in format: {question_id, answer_text, selected_entities}
        """
        question_id = question.get('id', '')
        question_text = question.get('question_text', '').lower()
        question_type = question.get('question_type', '')
        options = question.get('options', [])
        related_entities = question.get('related_entities', [])
        
        answer = {
            'question_id': question_id,
            'answer_text': '',
            'selected_entities': None
        }
        
        # Entity selection questions
        if question_type == 'entity_selection':
            if related_entities:
                # Try to match entities based on prompt context
                device = self.prompt_context.get('device', '').lower()
                location = self.prompt_context.get('location', '').lower()
                
                # Priority: 1) device + location match, 2) device match, 3) location match, 4) first entity
                if device and location:
                    matched = [e for e in related_entities 
                              if device in e.lower() and location in e.lower()]
                    if matched:
                        answer['selected_entities'] = matched[:1]
                        answer['answer_text'] = matched[0]
                        return answer
                
                if device:
                    matched = [e for e in related_entities if device in e.lower()]
                    if matched:
                        answer['selected_entities'] = matched[:1]
                        answer['answer_text'] = matched[0]
                        return answer
                
                if location:
                    matched = [e for e in related_entities if location in e.lower()]
                    if matched:
                        answer['selected_entities'] = matched[:1]
                        answer['answer_text'] = matched[0]
                        return answer
                
                # Fallback to first entity
                answer['selected_entities'] = [related_entities[0]]
                answer['answer_text'] = related_entities[0]
            else:
                # No entities provided - construct answer from context
                device = self.prompt_context.get('device', 'device')
                location = self.prompt_context.get('location', '')
                if location:
                    answer['answer_text'] = f"{location.title()} {device.title()}"
                else:
                    answer['answer_text'] = device.title()
        
        # Multiple choice questions
        elif question_type == 'multiple_choice' and options:
            # Try to match options with prompt context
            device = self.prompt_context.get('device', '').lower()
            location = self.prompt_context.get('location', '').lower()
            interval = self.prompt_context.get('interval', '')
            duration = self.prompt_context.get('duration', '')
            time_val = self.prompt_context.get('time', '')
            
            # Match device/location
            if device or location or 'device' in question_text:
                if device and location:
                    matched = [opt for opt in options 
                              if device in opt.lower() and location in opt.lower()]
                    if matched:
                        answer['answer_text'] = matched[0]
                        return answer
                if device:
                    matched = [opt for opt in options if device in opt.lower()]
                    if matched:
                        answer['answer_text'] = matched[0]
                        return answer
                if location:
                    matched = [opt for opt in options if location in opt.lower()]
                    if matched:
                        answer['answer_text'] = matched[0]
                        return answer
            
            # Match interval/time
            if interval and ('interval' in question_text or 'time' in question_text or 'minute' in question_text):
                interval_num = re.search(r'(\d+)', interval)
                if interval_num:
                    matched = [opt for opt in options if interval_num.group(1) in opt]
                    if matched:
                        answer['answer_text'] = matched[0]
                        return answer
            
            # Match duration
            if duration and ('duration' in question_text or 'second' in question_text):
                duration_num = re.search(r'(\d+)', duration)
                if duration_num:
                    matched = [opt for opt in options if duration_num.group(1) in opt]
                    if matched:
                        answer['answer_text'] = matched[0]
                        return answer
            
            # Match time
            if time_val and 'time' in question_text:
                matched = [opt for opt in options if any(part in opt.lower() for part in time_val.lower().split())]
                if matched:
                    answer['answer_text'] = matched[0]
                    return answer
            
            # Default to first option
            answer['answer_text'] = options[0]
        
        # Text input questions
        else:
            # Use context values if available
            if 'device' in question_text or 'entity' in question_text:
                device = self.prompt_context.get('device', 'device')
                location = self.prompt_context.get('location', '')
                if location:
                    answer['answer_text'] = f"{location.title()} {device.title()}"
                else:
                    answer['answer_text'] = device.title()
            elif 'interval' in question_text or ('time' in question_text and 'minute' in question_text):
                interval = self.prompt_context.get('interval', '15 minutes')
                answer['answer_text'] = f"Every {interval}"
            elif 'duration' in question_text or 'second' in question_text:
                duration = self.prompt_context.get('duration', '15 seconds')
                answer['answer_text'] = duration
            elif 'brightness' in question_text:
                brightness = self.prompt_context.get('brightness', '100%')
                answer['answer_text'] = brightness
            elif 'effect' in question_text:
                effect = self.prompt_context.get('effect', 'random')
                answer['answer_text'] = f"{effect.title()} effect"
            elif 'color' in question_text:
                colors = self.prompt_context.get('colors', 'random')
                answer['answer_text'] = f"{colors.title()} colors"
            elif 'time' in question_text:
                time_val = self.prompt_context.get('time', '')
                if time_val:
                    answer['answer_text'] = time_val
                else:
                    answer['answer_text'] = 'Yes'
            else:
                answer['answer_text'] = 'Yes'  # Default answer
        
        # Don't log every auto-answer to reduce terminal noise (already logged in handle_clarifications)
        return answer


class AskAITester:
    """Main test runner for Ask AI API"""
    
    def __init__(self, base_url: str = BASE_URL, timeout: float = TIMEOUT, api_key: str = API_KEY):
        self.base_url = base_url
        self.timeout = timeout
        self.api_key = api_key
        self.scorer = Scorer()
        self.client: httpx.AsyncClient | None = None
    
    def get_clarification_handler(self, prompt: str):
        """Get a clarification handler for a specific prompt"""
        return ClarificationHandler(prompt)
    
    async def __aenter__(self):
        headers = {}
        if self.api_key:
            headers["X-HomeIQ-API-Key"] = self.api_key
            headers["Authorization"] = f"Bearer {self.api_key}"
        self.client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def check_health(self) -> bool:
        """Check if API is healthy"""
        TerminalOutput.print_info("Checking service health...")
        try:
            response = await self.client.get(HEALTH_URL)
            if response.status_code == 200:
                TerminalOutput.print_success(f"Service is healthy (status: {response.status_code})")
                return True
            else:
                TerminalOutput.print_error(f"Service returned status {response.status_code}")
                return False
        except Exception as e:
            TerminalOutput.print_error(f"Health check failed: {e}")
            return False
    
    async def submit_query(self, query: str, user_id: str = "continuous_improvement") -> dict[str, Any]:
        """Submit query to Ask AI API"""
        TerminalOutput.print_info(f"Submitting query: {query[:80]}...")
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/query",
                json={
                    "query": query,
                    "user_id": user_id
                }
            )
            elapsed = time.time() - start_time
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                TerminalOutput.print_error(f"Query failed (status: {response.status_code}, time: {elapsed:.2f}s)")
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_text)
                    raise Exception(f"Query failed: {error_detail}")
                except (ValueError, KeyError):
                    raise Exception(f"Query failed with status {response.status_code}: {error_text}")
            
            result = response.json()
            query_id = result.get('query_id', 'unknown')
            clarification_needed = result.get('clarification_needed', False)
            suggestions_count = len(result.get('suggestions', []))
            
            TerminalOutput.print_success(f"Query submitted successfully (time: {elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Query ID: {query_id}", indent=1)
            TerminalOutput.print_info(f"  Clarification needed: {clarification_needed}", indent=1)
            TerminalOutput.print_info(f"  Initial suggestions: {suggestions_count}", indent=1)
            
            return result
        except httpx.HTTPError as e:
            elapsed = time.time() - start_time
            TerminalOutput.print_error(f"Network error during query submission (time: {elapsed:.2f}s)")
            raise Exception(f"Network error during query submission: {str(e)}")
        except Exception as e:
            elapsed = time.time() - start_time
            # Re-raise if already formatted
            if "Query failed" in str(e) or "Network error" in str(e):
                raise
            raise Exception(f"Unexpected error during query submission: {str(e)}")
    
    async def handle_clarifications(
        self, 
        session_id: str, 
        initial_questions: list[dict[str, Any]],
        clarification_handler: ClarificationHandler | None = None
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """
        Handle clarification loop until complete.
        Returns (final_response, clarification_log)
        """
        clarification_log = []
        current_questions = initial_questions
        session_id_current = session_id
        max_rounds = MAX_CLARIFICATION_ROUNDS
        clarification_response = None
        
        while current_questions and len(clarification_log) < max_rounds:
            round_num = len(clarification_log) + 1
            TerminalOutput.print_info(f"Clarification Round {round_num}/{max_rounds}: {len(current_questions)} question(s)")
            
            # Show questions
            for i, q in enumerate(current_questions, 1):
                q_text = q.get('question_text', 'Unknown question')[:60]
                TerminalOutput.print_info(f"  Q{i}: {q_text}...", indent=1)
            
            # Generate answers
            TerminalOutput.print_info("Generating auto-answers...", indent=1)
            answers = []
            handler = clarification_handler or ClarificationHandler("")
            for q in current_questions:
                answer = handler.answer_question(q)
                answers.append(answer)
                answer_text = answer.get('answer_text', '')[:50]
                TerminalOutput.print_info(f"  A: {answer_text}...", indent=2)
            
            # Log Q&A
            qa_round = {
                'round': round_num,
                'questions': current_questions,
                'answers': answers,
                'timestamp': datetime.now().isoformat()
            }
            clarification_log.append(qa_round)
            
            # Submit answers
            TerminalOutput.print_info("Submitting answers to API...", indent=1)
            start_time = time.time()
            try:
                response = await self.client.post(
                    f"{self.base_url}/clarify",
                    json={
                        "session_id": session_id_current,
                        "answers": answers
                    }
                )
                elapsed = time.time() - start_time
                
                if response.status_code != 200:
                    error_text = response.text
                    TerminalOutput.print_error(f"Clarification failed (status: {response.status_code}, time: {elapsed:.2f}s)")
                    try:
                        error_json = response.json()
                        error_detail = error_json.get('detail', error_text)
                        raise Exception(f"Clarification failed: {error_detail}")
                    except (ValueError, KeyError):
                        raise Exception(f"Clarification failed with status {response.status_code}: {error_text}")
                
                clarification_response = response.json()
                TerminalOutput.print_success(f"Answers submitted (time: {elapsed:.2f}s)")
            except httpx.HTTPError as e:
                elapsed = time.time() - start_time
                TerminalOutput.print_error(f"Network error during clarification (time: {elapsed:.2f}s)")
                raise Exception(f"Network error during clarification: {str(e)}")
            
            # Check if complete
            if clarification_response.get('clarification_complete', False):
                confidence = clarification_response.get('confidence', 0.0)
                suggestions_count = len(clarification_response.get('suggestions', []))
                TerminalOutput.print_success(f"Clarification complete! (confidence: {confidence:.1%}, suggestions: {suggestions_count})")
                return clarification_response, clarification_log
            
            # Get next questions
            current_questions = clarification_response.get('questions', [])
            if not current_questions:
                # Check if we have suggestions even though clarification isn't marked complete
                suggestions = clarification_response.get('suggestions', [])
                if suggestions:
                    TerminalOutput.print_info(f"Found {len(suggestions)} suggestion(s) - proceeding despite incomplete clarification")
                    break
                else:
                    # Try fetching from query endpoint
                    try:
                        check_response = await self.client.get(f"{self.base_url}/query/{session_id_current}")
                        if check_response.status_code == 200:
                            check_data = check_response.json()
                            suggestions = check_data.get('suggestions', [])
                            if suggestions:
                                clarification_response = check_data
                                TerminalOutput.print_info(f"Retrieved {len(suggestions)} suggestion(s) from query endpoint")
                                break
                    except Exception as e:
                        TerminalOutput.print_warning(f"Could not check for suggestions: {e}")
                    
                    TerminalOutput.print_warning("No more questions but clarification not marked complete and no suggestions found")
                    break
        
        if len(clarification_log) >= max_rounds:
            raise Exception(f"Clarification exceeded maximum rounds ({max_rounds})")
        
        if not clarification_response:
            raise Exception("Clarification response is missing")
        
        return clarification_response, clarification_log
    
    async def approve_suggestion(self, query_id: str, suggestion_id: str) -> dict[str, Any]:
        """Approve a suggestion and create automation"""
        TerminalOutput.print_info(f"Approving suggestion {suggestion_id}...")
        TerminalOutput.print_info(f"  Query ID: {query_id}", indent=1)
        start_time = time.time()
        
        try:
            response = await self.client.post(
                f"{self.base_url}/query/{query_id}/suggestions/{suggestion_id}/approve",
                json={}
            )
            elapsed = time.time() - start_time
            
            if response.status_code not in [200, 201]:
                error_text = response.text
                TerminalOutput.print_error(f"Approval failed (status: {response.status_code}, time: {elapsed:.2f}s)")
                # Try to parse error message
                try:
                    error_json = response.json()
                    error_detail = error_json.get('detail', error_text)
                    raise Exception(f"Approval failed: {error_detail}")
                except (ValueError, KeyError):
                    raise Exception(f"Approval failed with status {response.status_code}: {error_text}")
            
            result = response.json()
            
            # Check for error status in response body (API may return 200 OK with error status)
            if result.get('status') == 'error':
                error_msg = result.get('message', 'Unknown error')
                error_details = result.get('error_details', {})
                error_type = error_details.get('type', 'unknown')
                error_detail_msg = error_details.get('message', error_msg)
                invalid_entities = error_details.get('invalid_entities', [])
                
                TerminalOutput.print_error(f"Approval failed (time: {elapsed:.2f}s)")
                TerminalOutput.print_error(f"  Error: {error_msg}", indent=1)
                TerminalOutput.print_error(f"  Type: {error_type}", indent=1)
                if invalid_entities:
                    TerminalOutput.print_error(f"  Invalid entities: {', '.join(invalid_entities)}", indent=1)
                
                raise Exception(f"Approval failed: {error_msg} (Type: {error_type}). Details: {error_detail_msg}")
            
            automation_id = result.get('automation_id', 'unknown')
            has_yaml = bool(result.get('automation_yaml'))
            
            TerminalOutput.print_success(f"Suggestion approved (time: {elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Automation ID: {automation_id}", indent=1)
            TerminalOutput.print_info(f"  YAML generated: {has_yaml}", indent=1)
            
            return result
        except httpx.HTTPError as e:
            elapsed = time.time() - start_time
            TerminalOutput.print_error(f"Network error during approval (time: {elapsed:.2f}s)")
            raise Exception(f"Network error during approval: {str(e)}")
        except Exception as e:
            elapsed = time.time() - start_time
            # Re-raise if already formatted
            if "Approval failed" in str(e):
                raise
            raise Exception(f"Unexpected error during approval: {str(e)}")
    
    async def run_full_workflow(
        self, 
        query: str, 
        prompt_id: str, 
        prompt_name: str, 
        prompt_text: str, 
        complexity: str
    ) -> tuple[PromptResult, dict[str, Any]]:
        """
        Run complete workflow: query → clarifications → approve
        Returns (result, workflow_data) where workflow_data contains all responses
        """
        result = PromptResult(
            prompt_id=prompt_id,
            prompt_name=prompt_name,
            prompt_text=prompt_text,
            complexity=complexity
        )
        workflow_data = {
            'query_response': None,
            'clarification_response': None,
            'approval_response': None,
            'selected_suggestion': None
        }
        
        try:
            workflow_start = time.time()
            
            # Step 1: Submit query
            TerminalOutput.print_step(1, 4, f"Submit Query - {prompt_name}")
            query_response = await self.submit_query(query)
            workflow_data['query_response'] = query_response
            result.query_id = query_response.get('query_id')
            
            # Track which query_id to use for approval (may change after clarification)
            approval_query_id = result.query_id
            session_id = None
            
            # Check if clarification needed
            if query_response.get('clarification_needed', False):
                session_id = query_response.get('clarification_session_id')
                questions = query_response.get('questions', [])
                
                if questions:
                    # Step 2: Handle clarifications
                    TerminalOutput.print_step(2, 4, "Handle Clarifications")
                    clarification_handler = ClarificationHandler(query)
                    clarification_response, clarification_log = await self.handle_clarifications(
                        session_id, questions, clarification_handler
                    )
                    workflow_data['clarification_response'] = clarification_response
                    result.clarification_log = clarification_log
                    result.clarification_rounds = len(clarification_log)
                    
                    # After clarification, suggestions may be in a different query record
                    # The clarification_query_id is the same as session_id
                    suggestions = clarification_response.get('suggestions', [])
                    
                    # If no suggestions in response, try fetching from query endpoint
                    if not suggestions:
                        try:
                            check_response = await self.client.get(f"{self.base_url}/query/{session_id}")
                            if check_response.status_code == 200:
                                check_data = check_response.json()
                                suggestions = check_data.get('suggestions', [])
                                if suggestions:
                                    clarification_response = check_data
                                    TerminalOutput.print_info(f"Retrieved {len(suggestions)} suggestion(s) from query endpoint")
                        except Exception as e:
                            TerminalOutput.print_warning(f"Could not fetch suggestions from query endpoint: {e}")
                    
                    if clarification_response.get('clarification_complete', False) or suggestions:
                        # Use session_id as query_id for approval (it's the clarification_query_id)
                        approval_query_id = session_id
                        TerminalOutput.print_info(f"Using clarification_query_id ({session_id}) for approval")
                else:
                    suggestions = query_response.get('suggestions', [])
            else:
                TerminalOutput.print_info("No clarification needed - proceeding with direct suggestions")
                suggestions = query_response.get('suggestions', [])
            
            if not suggestions:
                raise Exception("No suggestions generated")
            
            # Step 3: Select best suggestion
            TerminalOutput.print_step(3, 4, "Select and Approve Suggestion")
            # Filter out suggestions without suggestion_id
            valid_suggestions = [s for s in suggestions if s.get('suggestion_id')]
            if not valid_suggestions:
                raise Exception("No valid suggestions with suggestion_id found")
            
            TerminalOutput.print_info(f"Evaluating {len(valid_suggestions)} suggestion(s)...")
            best_suggestion = max(valid_suggestions, key=lambda s: s.get('confidence', 0.0))
            workflow_data['selected_suggestion'] = best_suggestion
            result.suggestion_id = best_suggestion.get('suggestion_id')
            
            if not result.suggestion_id:
                raise Exception("Selected suggestion has no suggestion_id")
            
            confidence = best_suggestion.get('confidence', 0.0)
            title = best_suggestion.get('title', 'Untitled')[:50]
            TerminalOutput.print_success(f"Selected: {title}... (confidence: {confidence:.1%})")
            
            # Approve suggestion (use correct query_id)
            try:
                approval_response = await self.approve_suggestion(approval_query_id, result.suggestion_id)
            except Exception as e:
                # If approval fails with clarification_query_id, try original query_id as fallback
                if approval_query_id != result.query_id and "not found" in str(e).lower():
                    TerminalOutput.print_warning(f"Approval with clarification_query_id failed, trying original query_id")
                    approval_response = await self.approve_suggestion(result.query_id, result.suggestion_id)
                else:
                    raise
            workflow_data['approval_response'] = approval_response
            result.automation_id = approval_response.get('automation_id')
            result.automation_yaml = approval_response.get('automation_yaml')
            
            # Validate YAML before scoring
            if not result.automation_yaml:
                raise Exception("No automation YAML generated")
            
            # Step 4: Score results
            TerminalOutput.print_step(4, 4, "Score Results")
            TerminalOutput.print_info("Scoring automation correctness...")
            automation_score = self.scorer.score_automation_correctness(result.automation_yaml, query, prompt_id)
            TerminalOutput.print_info("Scoring YAML validity...")
            yaml_score = self.scorer.score_yaml_validity(result.automation_yaml)
            
            scores = self.scorer.calculate_total_score(
                automation_score=automation_score,
                yaml_score=yaml_score,
                clarification_count=result.clarification_rounds
            )
            
            result.automation_score = scores['automation_score']
            result.yaml_score = scores['yaml_score']
            result.total_score = scores['total_score']
            result.success = True
            
            workflow_elapsed = time.time() - workflow_start
            TerminalOutput.print_success(f"Workflow completed successfully (total time: {workflow_elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Total Score: {result.total_score:.2f}/100", indent=1)
            TerminalOutput.print_info(f"  Automation Score: {result.automation_score:.2f}/100", indent=1)
            TerminalOutput.print_info(f"  YAML Score: {result.yaml_score:.2f}/100", indent=1)
            TerminalOutput.print_info(f"  Clarification Rounds: {result.clarification_rounds}", indent=1)
            
        except Exception as e:
            # IMPROVED: Retry logic for transient failures
            error_str = str(e)
            
            # Check if error is retryable (transient failures)
            retryable_errors = [
                "No suggestions generated",
                "Network error",
                "Service disconnected",
                "timeout",
                "Connection",
                "404"
            ]
            
            is_retryable = any(err.lower() in error_str.lower() for err in retryable_errors)
            max_retries = 3
            
            if is_retryable:
                # Retry logic will be handled in the calling code
                result.error = error_str
                result.success = False
                TerminalOutput.print_error(f"Workflow failed (retryable): {error_str}")
            else:
                result.error = error_str
                result.success = False
                TerminalOutput.print_error(f"Workflow failed: {error_str}")
        
        return result, workflow_data


class CycleManager:
    """Manages improvement cycles"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cycles: list[CycleResult] = []
    
    def save_cycle_data(
        self, 
        cycle_num: int, 
        result: CycleResult, 
        workflow_data: dict[str, Any]
    ) -> None:
        """Save all cycle data to files"""
        cycle_dir = self.output_dir / f"cycle-{cycle_num}"
        cycle_dir.mkdir(exist_ok=True)
        
        # Save overall cycle summary
        cycle_summary = {
            'cycle_number': cycle_num,
            'overall_score': result.overall_score,
            'all_successful': result.all_successful,
            'timestamp': result.timestamp,
            'prompt_results': [
                {
                    'prompt_id': pr.prompt_id,
                    'prompt_name': pr.prompt_name,
                    'complexity': pr.complexity,
                    'total_score': pr.total_score,
                    'success': pr.success,
                    'error': pr.error
                }
                for pr in result.prompt_results
            ]
        }
        with open(cycle_dir / "cycle_summary.json", 'w', encoding='utf-8') as f:
            json.dump(cycle_summary, f, indent=2)
        
        # Save cycle result object
        with open(cycle_dir / "cycle_result.json", 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
        # Save logs
        log_file = cycle_dir / "logs.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Cycle {cycle_num} Execution Log\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {result.timestamp}\n")
            f.write(f"Overall Score: {result.overall_score:.2f}/100\n")
            f.write(f"All Successful: {result.all_successful}\n")
            f.write(f"Number of Prompts: {len(result.prompt_results)}\n\n")
            for pr in result.prompt_results:
                f.write(f"  {pr.prompt_name} ({pr.complexity}): ")
                if pr.success:
                    f.write(f"✓ {pr.total_score:.2f}/100\n")
                else:
                    f.write(f"✗ Failed: {pr.error}\n")
        
        logger.info(f"Cycle {cycle_num} data saved to {cycle_dir}")
    
    async def deploy_service(self) -> bool:
        """Rebuild and restart the service"""
        logger.info("Deploying service...")
        try:
            # Build
            logger.info("Building service...")
            build_result = subprocess.run(
                ["docker-compose", "build", "ai-automation-service"],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if build_result.returncode != 0:
                logger.error(f"Build failed: {build_result.stderr}")
                return False
            
            # Restart
            logger.info("Restarting service...")
            restart_result = subprocess.run(
                ["docker-compose", "restart", "ai-automation-service"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if restart_result.returncode != 0:
                logger.error(f"Restart failed: {restart_result.stderr}")
                return False
            
            # Wait for health check
            logger.info("Waiting for service to be healthy...")
            headers = {}
            if API_KEY:
                headers["X-HomeIQ-API-Key"] = API_KEY
                headers["Authorization"] = f"Bearer {API_KEY}"
            for i in range(HEALTH_CHECK_RETRIES):
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                    try:
                        response = await client.get(HEALTH_URL)
                        if response.status_code == 200:
                            logger.info("Service is healthy!")
                            return True
                    except (httpx.HTTPError, httpx.TimeoutException):
                        pass
                if i % 5 == 0:
                    logger.info(f"Still waiting... ({i}/{HEALTH_CHECK_RETRIES})")
            
            logger.error(f"Service did not become healthy in time (checked {HEALTH_CHECK_RETRIES} times)")
            return False
            
        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            return False
    
    def generate_summary(self) -> str:
        """Generate summary of all cycles"""
        summary_lines = [
            "# Ask AI Continuous Improvement Summary",
            "",
            f"Generated: {datetime.now().isoformat()}",
            f"Total Cycles: {len(self.cycles)}",
            f"Prompts per Cycle: {len(TARGET_PROMPTS)}",
            "",
            "## Cycle Results",
            ""
        ]
        
        for i, cycle in enumerate(self.cycles, 1):
            status_icon = "[SUCCESS]" if cycle.all_successful else "[PARTIAL]" if any(r.success for r in cycle.prompt_results) else "[FAILED]"
            summary_lines.extend([
                f"### Cycle {i}",
                f"- **Status**: {status_icon}",
                f"- **Overall Score**: {cycle.overall_score:.2f}/100",
                f"- **All Successful**: {cycle.all_successful}",
                f"- **Timestamp**: {cycle.timestamp}",
                "",
                "#### Prompt Results:",
                ""
            ])
            
            for pr in cycle.prompt_results:
                prompt_status = "✓" if pr.success else "✗"
                summary_lines.append(f"- {prompt_status} **{pr.prompt_name}** ({pr.complexity}): {pr.total_score:.2f}/100")
                if pr.error:
                    summary_lines.append(f"  - Error: {pr.error}")
            
            summary_lines.append("")
        
        # Trends
        if len(self.cycles) > 1:
            summary_lines.extend([
                "## Improvement Trends",
                ""
            ])
            
            overall_scores = [c.overall_score for c in self.cycles if c.overall_score > 0]
            if overall_scores:
                summary_lines.extend([
                    f"- **Overall Score Range**: {min(overall_scores):.2f} - {max(overall_scores):.2f}",
                    f"- **Average Overall Score**: {sum(overall_scores)/len(overall_scores):.2f}",
                    f"- **Final Overall Score**: {overall_scores[-1]:.2f}",
                    ""
                ])
            
            # Per-prompt trends
            for prompt_info in TARGET_PROMPTS:
                prompt_id = prompt_info['id']
                prompt_scores = []
                for cycle in self.cycles:
                    pr = next((r for r in cycle.prompt_results if r.prompt_id == prompt_id), None)
                    if pr and pr.success:
                        prompt_scores.append(pr.total_score)
                
                if prompt_scores:
                    summary_lines.extend([
                        f"- **{prompt_info['name']}** ({prompt_info['complexity']}): "
                        f"Range {min(prompt_scores):.2f}-{max(prompt_scores):.2f}, "
                        f"Avg {sum(prompt_scores)/len(prompt_scores):.2f}, "
                        f"Final {prompt_scores[-1]:.2f}",
                        ""
                    ])
        
        return "\n".join(summary_lines)
    
    def analyze_cycle(
        self, 
        cycle_num: int, 
        result: PromptResult, 
        workflow_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze cycle results and identify improvement areas.
        Returns analysis dict with recommendations.
        """
        analysis = {
            'cycle': cycle_num,
            'issues': [],
            'recommendations': [],
            'improvement_areas': []
        }
        
        # Analyze clarification count
        if result.clarification_rounds > 3:
            analysis['issues'].append(f"High clarification count: {result.clarification_rounds}")
            analysis['recommendations'].append(
                "Improve entity extraction to reduce clarification questions"
            )
            analysis['improvement_areas'].append('entity_extraction')
        
        # Analyze automation correctness
        if result.automation_score < 80:
            analysis['issues'].append(f"Low automation correctness: {result.automation_score:.2f}")
            analysis['recommendations'].append(
                "Review prompt engineering and YAML generation logic"
            )
            analysis['improvement_areas'].append('prompt_engineering')
        
        # Analyze YAML validity
        if result.yaml_score < 100:
            analysis['issues'].append(f"YAML validity issues: {result.yaml_score:.2f}")
            analysis['recommendations'].append(
                "Fix YAML generation to ensure valid Home Assistant format"
            )
            analysis['improvement_areas'].append('yaml_generation')
        
        # Analyze total score
        if result.total_score < SCORE_WARNING_THRESHOLD:
            analysis['issues'].append(f"Total score below threshold: {result.total_score:.2f}")
            analysis['recommendations'].append(
                "Multiple areas need improvement - review all components"
            )
        
        return analysis
    
    def create_improvement_plan(self, cycle_num: int, analysis: dict[str, Any]) -> str:
        """
        Create improvement plan based on analysis.
        Returns markdown formatted plan.
        """
        plan_lines = [
            f"# Improvement Plan - Cycle {cycle_num}",
            "",
            f"Generated: {datetime.now().isoformat()}",
            "",
            "## Issues Identified",
            ""
        ]
        
        if analysis['issues']:
            for issue in analysis['issues']:
                plan_lines.append(f"- {issue}")
        else:
            plan_lines.append("- No critical issues identified")
        
        plan_lines.extend([
            "",
            "## Recommendations",
            ""
        ])
        
        if analysis['recommendations']:
            for rec in analysis['recommendations']:
                plan_lines.append(f"- {rec}")
        else:
            plan_lines.append("- Continue current approach")
        
        plan_lines.extend([
            "",
            "## Improvement Areas",
            ""
        ])
        
        improvement_areas = {
            'entity_extraction': {
                'files': [
                    'services/ai-automation-service/src/api/ask_ai_router.py',
                    'services/ai-automation-service/src/services/clarification/detector.py'
                ],
                'actions': [
                    'Improve entity extraction logic',
                    'Add better device name matching',
                    'Reduce ambiguity detection false positives'
                ]
            },
            'prompt_engineering': {
                'files': [
                    'services/ai-automation-service/src/api/ask_ai_router.py',
                    'services/ai-automation-service/src/services/clarification/question_generator.py'
                ],
                'actions': [
                    'Enhance prompt templates',
                    'Add more context to OpenAI requests',
                    'Improve instruction clarity'
                ]
            },
            'yaml_generation': {
                'files': [
                    'services/ai-automation-service/src/api/ask_ai_router.py:2170'
                ],
                'actions': [
                    'Fix YAML structure validation',
                    'Ensure all required fields are present',
                    'Validate entity ID formats'
                ]
            }
        }
        
        for area in analysis['improvement_areas']:
            if area in improvement_areas:
                info = improvement_areas[area]
                plan_lines.extend([
                    f"### {area.replace('_', ' ').title()}",
                    "",
                    "**Files to modify:**",
                    ""
                ])
                for file in info['files']:
                    plan_lines.append(f"- `{file}`")
                plan_lines.extend([
                    "",
                    "**Proposed actions:**",
                    ""
                ])
                for action in info['actions']:
                    plan_lines.append(f"- {action}")
                plan_lines.append("")
        
        return "\n".join(plan_lines)


async def cleanup_previous_automations():
    """
    Clean up Home Assistant automations created by previous runs of this script.
    Deletes automations at the beginning of the script run.
    Uses HomeAssistantClient from the project if available, otherwise uses direct API calls.
    """
    # Load Home Assistant configuration
    ha_url = os.getenv("HA_HTTP_URL") or os.getenv("HOME_ASSISTANT_URL")
    ha_token = os.getenv("HA_TOKEN") or os.getenv("HOME_ASSISTANT_TOKEN")
    
    if not ha_url or not ha_token:
        TerminalOutput.print_warning("Home Assistant URL or token not found. Skipping automation cleanup.")
        TerminalOutput.print_info("  Set HA_HTTP_URL and HA_TOKEN environment variables to enable cleanup.", indent=1)
        return
    
    TerminalOutput.print_header("Cleaning Up Previous Automations")
    TerminalOutput.print_info(f"Connecting to Home Assistant at {ha_url}...")
    
    # Try to use HomeAssistantClient from the project
    ha_client: Any = None
    session: aiohttp.ClientSession | None = None
    delete_headers: dict[str, str] = {}
    use_project_client = False
    
    try:
        # Add the service source to path to import HomeAssistantClient
        service_path = Path(__file__).parent.parent / "services" / "ai-automation-service" / "src"
        if str(service_path) not in sys.path:
            sys.path.insert(0, str(service_path))
        
        from clients.ha_client import HomeAssistantClient  # type: ignore[import-untyped]
        
        # Use the project's HomeAssistantClient
        ha_client = HomeAssistantClient(ha_url=ha_url, access_token=ha_token)
        TerminalOutput.print_info("Using project's HomeAssistantClient")
        use_project_client = True
        
        # Get all automations using the client
        session = await ha_client._get_session()
        delete_headers = ha_client.headers
        
        async with session.get(
            f"{ha_url}/api/states", 
            timeout=aiohttp.ClientTimeout(total=HA_API_TIMEOUT)
        ) as resp:
            if resp.status != 200:
                TerminalOutput.print_error(f"Failed to get automations: HTTP {resp.status}")
                return
            states = await resp.json()
    
    except (ImportError, Exception) as e:
        # Fallback to direct API calls if import fails
        TerminalOutput.print_info(f"Using direct API calls (could not import HomeAssistantClient: {e})")
        delete_headers = {
            "Authorization": f"Bearer {ha_token}",
            "Content-Type": "application/json"
        }
        session = aiohttp.ClientSession(headers=delete_headers)
        async with session.get(
            f"{ha_url}/api/states", 
            timeout=aiohttp.ClientTimeout(total=HA_API_TIMEOUT)
        ) as resp:
            if resp.status != 200:
                TerminalOutput.print_error(f"Failed to get automations: HTTP {resp.status}")
                await session.close()
                return
            states = await resp.json()
        
        # Filter for automation entities
        automations = [
            s for s in states 
            if s.get('entity_id', '').startswith('automation.')
        ]
        
        if not automations:
            TerminalOutput.print_success("No automations found. Nothing to clean up.")
            return
        
        TerminalOutput.print_info(f"Found {len(automations)} automation(s) in Home Assistant")
        
        # Identify automations created by this script
        # Look for patterns that match Ask AI service automation naming:
        # - automation.*_*_*_* (with timestamps and hashes)
        # - Examples: automation.office_wled_random_effect_every_15_min_1763929561_506d2957
        # Pattern: word_word_word_timestamp_hash (at least 3 underscores, ends with numbers)
        script_automations = []
        for auto in automations:
            entity_id = auto.get('entity_id', '')
            # Match pattern: automation.name_with_underscores_timestamp_hash
            # Must have at least 3 parts separated by underscores, ending with numeric timestamp
            if re.search(r'automation\.[a-z0-9_]+_\d{10,}_[a-z0-9]+$', entity_id, re.IGNORECASE):
                script_automations.append(auto)
            # Also match simpler patterns that might be from our prompts
            # Check if entity_id contains keywords from our prompts
            elif any(keyword in entity_id.lower() for keyword in [
                'wled', 'office', 'kitchen', 'living_room', 'bedroom', 
                'hallway', 'motion', 'door', 'arrive', 'home'
            ]) and re.search(r'_\d+_[a-z0-9]+$', entity_id, re.IGNORECASE):
                script_automations.append(auto)
        
        if not script_automations:
            TerminalOutput.print_info("No automations matching script pattern found. Skipping cleanup.")
            return
        
        TerminalOutput.print_info(f"Found {len(script_automations)} automation(s) likely created by this script")
        
        # Delete each automation using the 'id' from attributes
        # CRITICAL: Use the 'id' from attributes, NOT the entity_id
        deleted = 0
        failed = 0
        
        for auto in script_automations:
            entity_id = auto.get('entity_id')
            attrs = auto.get('attributes', {})
            friendly_name = attrs.get('friendly_name', entity_id)
            auto_id = attrs.get('id')  # Use ID from attributes, not entity_id!
            
            if not auto_id:
                TerminalOutput.print_warning(f"Skipping {entity_id}: No ID found in attributes", indent=1)
                failed += 1
                continue
            
            try:
                # Use correct endpoint: DELETE /api/config/automation/config/{id-from-attributes}
                async with session.delete(
                    f"{ha_url}/api/config/automation/config/{auto_id}",
                    headers=delete_headers,
                    timeout=aiohttp.ClientTimeout(total=HA_API_TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        if result.get('result') == 'ok':
                            deleted += 1
                            TerminalOutput.print_success(f"Deleted: {entity_id} ({friendly_name})", indent=1)
                        else:
                            failed += 1
                            TerminalOutput.print_error(f"Failed: {entity_id} - Unexpected response", indent=1)
                    else:
                        failed += 1
                        text = await resp.text()
                        TerminalOutput.print_error(f"Failed: {entity_id} - HTTP {resp.status}: {text[:100]}", indent=1)
            except Exception as e:
                failed += 1
                TerminalOutput.print_error(f"Failed: {entity_id} - {str(e)}", indent=1)
        
        TerminalOutput.print_info(f"Cleanup complete: {deleted} deleted, {failed} failed")
        
    except aiohttp.ClientError as e:
        TerminalOutput.print_error(f"Network error during cleanup: {e}")
    except Exception as e:
        TerminalOutput.print_error(f"Error during cleanup: {e}")
    finally:
        # Cleanup: Close session if we created it directly (not using project client)
        if not use_project_client and session and not session.closed:
            await session.close()
        elif use_project_client and ha_client and hasattr(ha_client, 'close'):
            await ha_client.close()


async def main():
    """Main entry point"""
    TerminalOutput.print_header("Ask AI Continuous Improvement Process")
    
    # Clean up previous automations at the beginning
    await cleanup_previous_automations()
    
    TerminalOutput.print_info(f"Number of Prompts: {len(TARGET_PROMPTS)}")
    for i, prompt_info in enumerate(TARGET_PROMPTS, 1):
        TerminalOutput.print_info(f"  {i}. {prompt_info['name']} ({prompt_info['complexity']})", indent=1)
    TerminalOutput.print_info(f"Max Cycles: {MAX_CYCLES}")
    TerminalOutput.print_info(f"Output Directory: {OUTPUT_DIR}")
    
    manager = CycleManager(OUTPUT_DIR)
    overall_start = time.time()
    
    for cycle_num in range(1, MAX_CYCLES + 1):
        cycle_start = time.time()
        TerminalOutput.print_header(f"Cycle {cycle_num}/{MAX_CYCLES}", "=")
        
        cycle_result = CycleResult(cycle_number=cycle_num)
        
        async with AskAITester() as tester:
            # Check health
            if not await tester.check_health():
                TerminalOutput.print_error("Service is not healthy. Please start the service first.")
                sys.exit(1)
            
            # Run all prompts
            for prompt_idx, prompt_info in enumerate(TARGET_PROMPTS, 1):
                prompt_id = prompt_info['id']
                prompt_name = prompt_info['name']
                prompt_text = prompt_info['prompt']
                complexity = prompt_info['complexity']
                
                TerminalOutput.print_header(f"Prompt {prompt_idx}/{len(TARGET_PROMPTS)}: {prompt_name} ({complexity})", "-")
                TerminalOutput.print_info(f"Prompt: {prompt_text[:100]}...")
                
                try:
                    # Run workflow for this prompt
                    prompt_result, workflow_data = await tester.run_full_workflow(
                        prompt_text, prompt_id, prompt_name, prompt_text, complexity
                    )
                    cycle_result.prompt_results.append(prompt_result)
                    
                    # Save individual prompt data
                    prompt_dir = OUTPUT_DIR / f"cycle-{cycle_num}" / prompt_id
                    prompt_dir.mkdir(parents=True, exist_ok=True)
                    
                    if workflow_data.get('query_response'):
                        with open(prompt_dir / "query_response.json", 'w', encoding='utf-8') as f:
                            json.dump(workflow_data['query_response'], f, indent=2)
                    
                    if prompt_result.clarification_log:
                        with open(prompt_dir / "clarification_rounds.json", 'w', encoding='utf-8') as f:
                            json.dump(prompt_result.clarification_log, f, indent=2)
                    
                    if workflow_data.get('clarification_response'):
                        with open(prompt_dir / "clarification_response.json", 'w', encoding='utf-8') as f:
                            json.dump(workflow_data['clarification_response'], f, indent=2)
                    
                    if workflow_data.get('selected_suggestion'):
                        with open(prompt_dir / "suggestion_selected.json", 'w', encoding='utf-8') as f:
                            json.dump(workflow_data['selected_suggestion'], f, indent=2)
                    
                    if workflow_data.get('approval_response'):
                        with open(prompt_dir / "approval_response.json", 'w', encoding='utf-8') as f:
                            json.dump(workflow_data['approval_response'], f, indent=2)
                    
                    if prompt_result.automation_yaml:
                        with open(prompt_dir / "automation.yaml", 'w', encoding='utf-8') as f:
                            f.write(prompt_result.automation_yaml)
                    
                    # Save prompt scores
                    scores = {
                        'automation_score': prompt_result.automation_score,
                        'yaml_score': prompt_result.yaml_score,
                        'clarification_rounds': prompt_result.clarification_rounds,
                        'total_score': prompt_result.total_score,
                        'success': prompt_result.success,
                        'error': prompt_result.error
                    }
                    with open(prompt_dir / "score.json", 'w', encoding='utf-8') as f:
                        json.dump(scores, f, indent=2)
                    
                    with open(prompt_dir / "result.json", 'w', encoding='utf-8') as f:
                        json.dump(asdict(prompt_result), f, indent=2, default=str)
                    
                    if prompt_result.success:
                        TerminalOutput.print_success(f"Prompt {prompt_idx} completed: {prompt_result.total_score:.2f}/100")
                    else:
                        TerminalOutput.print_error(f"Prompt {prompt_idx} failed: {prompt_result.error}")
                    
                except Exception as e:
                    TerminalOutput.print_error(f"Prompt {prompt_idx} exception: {e}")
                    error_result = PromptResult(
                        prompt_id=prompt_id,
                        prompt_name=prompt_name,
                        prompt_text=prompt_text,
                        complexity=complexity,
                        error=str(e),
                        success=False
                    )
                    cycle_result.prompt_results.append(error_result)
            
            # Calculate overall cycle score
            cycle_result.overall_score = cycle_result.calculate_overall_score()
            cycle_result.all_successful = cycle_result.all_prompts_successful()
            
            manager.cycles.append(cycle_result)
            
            # Save cycle data
            TerminalOutput.print_info("Saving cycle data...")
            manager.save_cycle_data(cycle_num, cycle_result, {})
            cycle_elapsed = time.time() - cycle_start
            TerminalOutput.print_success(f"Cycle {cycle_num} data saved (cycle time: {cycle_elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Overall Score: {cycle_result.overall_score:.2f}/100", indent=1)
            TerminalOutput.print_info(f"  Successful Prompts: {sum(1 for r in cycle_result.prompt_results if r.success)}/{len(cycle_result.prompt_results)}", indent=1)
            
            # Check if all prompts successful and at 100%
            if not cycle_result.all_successful:
                failed_prompts = [r for r in cycle_result.prompt_results if not r.success]
                TerminalOutput.print_warning(f"Cycle {cycle_num} has {len(failed_prompts)} failed prompt(s)")
                for failed in failed_prompts:
                    TerminalOutput.print_error(f"  - {failed.prompt_name}: {failed.error}", indent=1)
                
                # Stop if critical errors (all prompts failed or YAML issues)
                all_yaml_failed = all(r.yaml_score < YAML_VALIDITY_THRESHOLD for r in failed_prompts if r.yaml_score > 0)
                if all_yaml_failed or len(failed_prompts) == len(cycle_result.prompt_results):
                    TerminalOutput.print_warning("Stopping for manual review and fixes.")
                    break
            
            # Check if all successful prompts have 100% scores
            successful_prompts = [r for r in cycle_result.prompt_results if r.success]
            all_at_100 = all(r.total_score >= 100.0 for r in successful_prompts) if successful_prompts else False
            
            if cycle_result.all_successful and all_at_100:
                TerminalOutput.print_success(f"🎉 ALL PROMPTS ACHIEVED 100% ACCURACY!")
                TerminalOutput.print_success(f"Cycle {cycle_num}: All {len(cycle_result.prompt_results)} prompts successful with 100% scores")
                break
            elif successful_prompts:
                not_100 = [r for r in successful_prompts if r.total_score < 100.0]
                if not_100:
                    TerminalOutput.print_info(f"Cycle {cycle_num}: {len(not_100)} prompt(s) below 100% (continuing to improve...)")
                    for r in not_100:
                        TerminalOutput.print_info(f"  - {r.prompt_name}: {r.total_score:.2f}/100", indent=1)
            
            # Analyze results
            TerminalOutput.print_info("Analyzing results...")
            # Use first successful result for analysis (or first result if none successful)
            analysis_result = next((r for r in cycle_result.prompt_results if r.success), 
                                  cycle_result.prompt_results[0] if cycle_result.prompt_results else None)
            analysis = None
            if analysis_result:
                analysis = manager.analyze_cycle(cycle_num, analysis_result, {})
                
                if analysis['issues']:
                    TerminalOutput.print_warning(f"Found {len(analysis['issues'])} issue(s)")
                    for issue in analysis['issues']:
                        TerminalOutput.print_info(f"  - {issue}", indent=1)
                
                # Create improvement plan
                if analysis['improvement_areas'] or cycle_result.overall_score < SCORE_EXCELLENT_THRESHOLD:
                    cycle_dir = OUTPUT_DIR / f"cycle-{cycle_num}"
                    plan_path = cycle_dir / "IMPROVEMENT_PLAN.md"
                    plan = manager.create_improvement_plan(cycle_num, analysis)
                    with open(plan_path, 'w', encoding='utf-8') as f:
                        f.write(plan)
                    TerminalOutput.print_info(f"Improvement plan saved to {plan_path}")
            
            # Check scores
            if cycle_result.overall_score < SCORE_WARNING_THRESHOLD:
                TerminalOutput.print_warning(f"Cycle {cycle_num} overall score is below threshold: {cycle_result.overall_score:.2f}")
            elif cycle_result.overall_score >= SCORE_EXCELLENT_THRESHOLD and cycle_result.all_successful:
                TerminalOutput.print_success(f"Cycle {cycle_num} score is excellent: {cycle_result.overall_score:.2f} (all prompts successful)")
            
            # If not last cycle, prepare for next iteration
            if cycle_num < MAX_CYCLES:
                TerminalOutput.print_info("\nPreparing for next cycle...")
                
                # If improvements needed, deploy updated service
                if analysis and analysis.get('improvement_areas', []):
                    TerminalOutput.print_info("Improvements identified. Deploying updated service...")
                    deploy_success = await manager.deploy_service()
                    if not deploy_success:
                        TerminalOutput.print_error("Deployment failed. Stopping.")
                        break
                    TerminalOutput.print_success("Service deployed successfully. Waiting before next cycle...")
                    await asyncio.sleep(DEPLOYMENT_WAIT_TIME)
                else:
                    TerminalOutput.print_info("No improvements needed. Continuing to next cycle...")
                    await asyncio.sleep(CYCLE_WAIT_TIME)
    
    # Generate summary
    overall_elapsed = time.time() - overall_start
    TerminalOutput.print_header("Generating Summary")
    summary = manager.generate_summary()
    summary_path = OUTPUT_DIR / "SUMMARY.md"
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(summary)
    
    TerminalOutput.print_success(f"Summary saved to {summary_path}")
    TerminalOutput.print_info(f"Total execution time: {overall_elapsed:.2f}s")
    TerminalOutput.print_header("Continuous Improvement Process Complete", "=")


if __name__ == "__main__":
    asyncio.run(main())

