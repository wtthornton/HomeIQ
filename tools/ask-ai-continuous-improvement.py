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
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import logging

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
TARGET_PROMPT = (
    "Every 15 mins choose a random effect on the Office WLED device. "
    "Play the effect for 15 secs. Choose random effect, random colors and brightness to 100%. "
    "At the end of the 15 sec the WLED light needs to return to exactly what it was before it started."
)
OUTPUT_DIR = Path("implementation/continuous-improvement")
MAX_CYCLES = 5
TIMEOUT = 300.0  # 5 minutes timeout for API calls

# API Key for authentication (read from environment or use default)
API_KEY = os.getenv("AI_AUTOMATION_API_KEY", "hs_P3rU9kQ2xZp6vL1fYc7bN4sTqD8mA0wR")


@dataclass
class CycleResult:
    """Results from a single improvement cycle"""
    cycle_number: int
    query_id: Optional[str] = None
    suggestion_id: Optional[str] = None
    automation_id: Optional[str] = None
    automation_yaml: Optional[str] = None
    clarification_rounds: int = 0
    clarification_log: List[Dict[str, Any]] = None
    automation_score: float = 0.0
    yaml_score: float = 0.0
    total_score: float = 0.0
    error: Optional[str] = None
    success: bool = False
    timestamp: str = None
    
    def __post_init__(self):
        if self.clarification_log is None:
            self.clarification_log = []
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class Scorer:
    """Scoring system for automation correctness, YAML validity, and clarification count"""
    
    @staticmethod
    def score_automation_correctness(yaml_str: str, prompt: str) -> float:
        """
        Score automation correctness based on prompt requirements.
        Returns score 0-100.
        """
        if not yaml_str:
            return 0.0
        
        try:
            yaml_data = yaml.safe_load(yaml_str)
        except yaml.YAMLError:
            return 0.0
        
        if not isinstance(yaml_data, dict):
            return 0.0
        
        score = 0.0
        max_score = 100.0
        checks = []
        
        # Check 1: 15-minute interval trigger (20 points)
        trigger = yaml_data.get('trigger', [])
        trigger_found = False
        if isinstance(trigger, list) and len(trigger) > 0:
            for t in trigger:
                if isinstance(t, dict) and t.get('platform') == 'time_pattern':
                    minutes = str(t.get('minutes', ''))
                    if '/15' in minutes:
                        score += 20.0
                        checks.append("✓ 15-minute interval trigger")
                        trigger_found = True
                        break
            
            if not trigger_found:
                 # Check for alternate format (minutes: 15 or similar)
                 checks.append(f"✗ 15-minute interval trigger not found in {trigger}")
        else:
            checks.append("✗ No trigger found")
        
        # Helper to search actions recursively
        def find_in_actions(actions, predicate):
            if not isinstance(actions, list):
                return False
            for action in actions:
                if predicate(action):
                    return True
                # Check nested sequences
                if 'sequence' in action:
                    if find_in_actions(action['sequence'], predicate):
                        return True
                if 'choose' in action:
                    for choice in action['choose']:
                        if find_in_actions(choice.get('sequence', []), predicate):
                            return True
                    if 'default' in action:
                         if find_in_actions(action['default'], predicate):
                            return True
            return False

        # Check 2: Random effect selection (15 points)
        def check_random_effect(action):
            data = action.get('data', {})
            return (
                action.get('service') == 'light.turn_on' and 
                ('random' in str(data.get('effect', '')).lower() or 
                 'random' in str(data.get('color_name', '')).lower())
            )
            
        if find_in_actions(yaml_data.get('action', []), check_random_effect):
            score += 15.0
            checks.append("✓ Random effect selection")
        else:
            checks.append("✗ Random effect selection not found")
        
        # Check 3: 15-second duration (15 points)
        def check_duration(action):
            if 'delay' in action:
                delay = str(action['delay'])
                return '15' in delay or '00:00:15' in delay
            return False

        if find_in_actions(yaml_data.get('action', []), check_duration):
            score += 15.0
            checks.append("✓ 15-second duration")
        else:
            checks.append("✗ 15-second duration not found")
        
        # Check 4: Brightness 100% (15 points)
        def check_brightness(action):
            data = action.get('data', {})
            return str(data.get('brightness_pct', '')) == '100'

        if find_in_actions(yaml_data.get('action', []), check_brightness):
            score += 15.0
            checks.append("✓ Brightness 100%")
        else:
            checks.append("✗ Brightness 100% not found")
        
        # Check 5: State restoration (20 points)
        # Look for scene.create (snapshot) AND scene.turn_on (restore)
        has_snapshot = find_in_actions(yaml_data.get('action', []), 
            lambda a: a.get('service') == 'scene.create')
        has_restore = find_in_actions(yaml_data.get('action', []), 
            lambda a: a.get('service') == 'scene.turn_on')
            
        if has_snapshot and has_restore:
            score += 20.0
            checks.append("✓ State restoration logic (snapshot & restore)")
        elif has_snapshot or has_restore:
            score += 10.0
            checks.append("⚠ Partial state restoration (found one part)")
        else:
            checks.append("✗ State restoration not found")
        
        # Check 6: Office WLED device entity (15 points)
        def check_entity(action):
            target = action.get('target', {})
            entity_id = target.get('entity_id', '')
            if isinstance(entity_id, list):
                entity_id = ' '.join(entity_id)
            return 'office' in entity_id.lower() and ('wled' in entity_id.lower() or 'light' in entity_id.lower())

        if find_in_actions(yaml_data.get('action', []), check_entity):
            score += 15.0
            checks.append("✓ Office WLED device")
        else:
            checks.append("✗ Office WLED device not found")
        
        # Log checks (but don't print all details in terminal to reduce noise)
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
        if re.search(r'light\.\w+|entity_id:\s*light\.\w+', yaml_str):
            score += 10.0
            checks.append("✓ Valid entity ID format")
        else:
            checks.append("✗ No valid entity IDs found")
        
        # Log checks (but don't print all details in terminal to reduce noise)
        if score < max_score:
            TerminalOutput.print_info(f"YAML validity: {score:.1f}/100 ({len([c for c in checks if c.startswith('✓')])}/{len(checks)} checks passed)")
        return min(score, max_score)
    
    @staticmethod
    def count_clarifications(session_log: List[Dict[str, Any]]) -> int:
        """Count clarification rounds"""
        return len(session_log)
    
    @staticmethod
    def calculate_total_score(automation_score: float, yaml_score: float, 
                             clarification_count: int) -> Dict[str, Any]:
        """
        Calculate weighted total score.
        Weights: automation (50%), YAML (30%), clarifications (20% - lower is better)
        """
        # Clarification score: 100 - (count * 10), minimum 0
        clarification_score = max(0.0, 100.0 - (clarification_count * 10.0))
        
        # Weighted total
        total = (
            automation_score * 0.5 +
            yaml_score * 0.3 +
            clarification_score * 0.2
        )
        
        return {
            'automation_score': automation_score,
            'yaml_score': yaml_score,
            'clarification_count': clarification_count,
            'clarification_score': clarification_score,
            'total_score': total,
            'weights': {
                'automation': 0.5,
                'yaml': 0.3,
                'clarifications': 0.2
            }
        }


class ClarificationHandler:
    """Auto-answer clarification questions based on prompt context"""
    
    def __init__(self, original_prompt: str):
        self.original_prompt = original_prompt.lower()
        self.prompt_context = {
            'device': 'WLED Office Light',
            'location': 'office',
            'interval': '15 minutes',
            'duration': '15 seconds',
            'brightness': '100%',
            'effect': 'random',
            'colors': 'random',
            'restore_state': True
        }
    
    def answer_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
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
            # Prioritize WLED Office Light - look for entities with "wled" first, then "office" + "light"
            # Priority order: 1) Contains "wled" + "office", 2) Contains "wled", 3) Contains "office" + "light", 4) Fallback
            if related_entities:
                wled_office_entities = [
                    e for e in related_entities 
                    if 'wled' in e.lower() and 'office' in e.lower()
                ]
                if wled_office_entities:
                    answer['selected_entities'] = wled_office_entities[:1]
                    answer['answer_text'] = wled_office_entities[0]
                else:
                    # Look for any WLED device (even if not explicitly "office")
                    wled_entities = [
                        e for e in related_entities 
                        if 'wled' in e.lower()
                    ]
                    if wled_entities:
                        answer['selected_entities'] = wled_entities[:1]
                        answer['answer_text'] = wled_entities[0]
                    else:
                        # Look for Office + Light (but not TV)
                        office_light_entities = [
                            e for e in related_entities 
                            if 'office' in e.lower() and 'light' in e.lower() and 'tv' not in e.lower()
                        ]
                        if office_light_entities:
                            answer['selected_entities'] = office_light_entities[:1]
                            answer['answer_text'] = office_light_entities[0]
                        else:
                            # Fallback to first entity - ALWAYS select something if entities are available
                            answer['selected_entities'] = [related_entities[0]]
                            answer['answer_text'] = related_entities[0]
            else:
                # No entities provided - use text answer
                answer['answer_text'] = 'WLED Office Light'
        
        # Multiple choice questions
        elif question_type == 'multiple_choice' and options:
            # Try to match options with prompt context
            if 'office' in question_text or 'device' in question_text or 'wled' in question_text:
                # Prioritize WLED Office Light
                wled_office_options = [opt for opt in options if 'wled' in opt.lower() and 'office' in opt.lower()]
                if wled_office_options:
                    answer['answer_text'] = wled_office_options[0]
                else:
                    wled_options = [opt for opt in options if 'wled' in opt.lower()]
                    if wled_options:
                        answer['answer_text'] = wled_options[0]
                    else:
                        office_light_options = [opt for opt in options if 'office' in opt.lower() and 'light' in opt.lower() and 'tv' not in opt.lower()]
                        if office_light_options:
                            answer['answer_text'] = office_light_options[0]
                        else:
                            office_options = [opt for opt in options if 'office' in opt.lower()]
                            if office_options:
                                answer['answer_text'] = office_options[0]
                            else:
                                answer['answer_text'] = options[0]
            elif 'interval' in question_text or 'time' in question_text or 'minute' in question_text:
                time_options = [opt for opt in options if '15' in opt or 'minute' in opt.lower()]
                if time_options:
                    answer['answer_text'] = time_options[0]
                else:
                    answer['answer_text'] = options[0]
            elif 'duration' in question_text or 'second' in question_text:
                duration_options = [opt for opt in options if '15' in opt or 'second' in opt.lower()]
                if duration_options:
                    answer['answer_text'] = duration_options[0]
                else:
                    answer['answer_text'] = options[0]
            else:
                answer['answer_text'] = options[0]  # Default to first option
        
        # Text input questions
        else:
            if 'office' in question_text or 'device' in question_text or 'wled' in question_text:
                answer['answer_text'] = 'WLED Office Light'
            elif 'interval' in question_text or 'time' in question_text:
                answer['answer_text'] = 'Every 15 minutes'
            elif 'duration' in question_text:
                answer['answer_text'] = '15 seconds'
            elif 'brightness' in question_text:
                answer['answer_text'] = '100%'
            elif 'effect' in question_text:
                answer['answer_text'] = 'Random effect'
            elif 'color' in question_text:
                answer['answer_text'] = 'Random colors'
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
        self.clarification_handler = ClarificationHandler(TARGET_PROMPT)
        self.client: Optional[httpx.AsyncClient] = None
    
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
    
    async def submit_query(self, query: str, user_id: str = "continuous_improvement") -> Dict[str, Any]:
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
                except:
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
    
    async def handle_clarifications(self, session_id: str, 
                                   initial_questions: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Handle clarification loop until complete.
        Returns (final_response, clarification_log)
        """
        clarification_log = []
        current_questions = initial_questions
        session_id_current = session_id
        max_rounds = 10  # Safety limit to prevent infinite loops
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
            for q in current_questions:
                answer = self.clarification_handler.answer_question(q)
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
                    except:
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
                TerminalOutput.print_warning("No more questions but clarification not marked complete")
                break
        
        if len(clarification_log) >= max_rounds:
            raise Exception(f"Clarification exceeded maximum rounds ({max_rounds})")
        
        if not clarification_response:
            raise Exception("Clarification response is missing")
        
        return clarification_response, clarification_log
    
    async def approve_suggestion(self, query_id: str, suggestion_id: str) -> Dict[str, Any]:
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
                except:
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
    
    async def run_full_workflow(self, query: str) -> Tuple[CycleResult, Dict[str, Any]]:
        """
        Run complete workflow: query → clarifications → approve
        Returns (result, workflow_data) where workflow_data contains all responses
        """
        result = CycleResult(cycle_number=0)  # Will be set by caller
        workflow_data = {
            'query_response': None,
            'clarification_response': None,
            'approval_response': None,
            'selected_suggestion': None
        }
        
        try:
            workflow_start = time.time()
            
            # Step 1: Submit query
            TerminalOutput.print_step(1, 4, "Submit Query")
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
                    clarification_response, clarification_log = await self.handle_clarifications(
                        session_id, questions
                    )
                    workflow_data['clarification_response'] = clarification_response
                    result.clarification_log = clarification_log
                    result.clarification_rounds = len(clarification_log)
                    
                    # After clarification, suggestions may be in a different query record
                    # The clarification_query_id is the same as session_id
                    if clarification_response.get('clarification_complete', False):
                        # Use session_id as query_id for approval (it's the clarification_query_id)
                        approval_query_id = session_id
                        TerminalOutput.print_info(f"Using clarification_query_id ({session_id}) for approval")
                    
                    # Get suggestions from clarification response
                    suggestions = clarification_response.get('suggestions', [])
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
            automation_score = self.scorer.score_automation_correctness(result.automation_yaml, query)
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
            result.error = str(e)
            result.success = False
            TerminalOutput.print_error(f"Workflow failed: {e}")
        
        return result, workflow_data


class CycleManager:
    """Manages improvement cycles"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cycles: List[CycleResult] = []
    
    def save_cycle_data(self, cycle_num: int, result: CycleResult, 
                       workflow_data: Dict[str, Any]):
        """Save all cycle data to files"""
        cycle_dir = self.output_dir / f"cycle-{cycle_num}"
        cycle_dir.mkdir(exist_ok=True)
        
        # Save query response
        if workflow_data.get('query_response'):
            with open(cycle_dir / "query_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['query_response'], f, indent=2)
        
        # Save clarification rounds
        if result.clarification_log:
            with open(cycle_dir / "clarification_rounds.json", 'w', encoding='utf-8') as f:
                json.dump(result.clarification_log, f, indent=2)
        
        # Save clarification response
        if workflow_data.get('clarification_response'):
            with open(cycle_dir / "clarification_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['clarification_response'], f, indent=2)
        
        # Save selected suggestion
        if workflow_data.get('selected_suggestion'):
            with open(cycle_dir / "suggestion_selected.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['selected_suggestion'], f, indent=2)
        
        # Save approval response
        if workflow_data.get('approval_response'):
            with open(cycle_dir / "approval_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['approval_response'], f, indent=2)
        
        # Save automation YAML
        if result.automation_yaml:
            with open(cycle_dir / "automation.yaml", 'w', encoding='utf-8') as f:
                f.write(result.automation_yaml)
        
        # Save scores
        scores = {
            'automation_score': result.automation_score,
            'yaml_score': result.yaml_score,
            'clarification_rounds': result.clarification_rounds,
            'total_score': result.total_score,
            'success': result.success,
            'error': result.error
        }
        with open(cycle_dir / "score.json", 'w', encoding='utf-8') as f:
            json.dump(scores, f, indent=2)
        
        # Save result object
        with open(cycle_dir / "result.json", 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
        # Save logs
        log_file = cycle_dir / "logs.txt"
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"Cycle {cycle_num} Execution Log\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Timestamp: {result.timestamp}\n")
            f.write(f"Status: {'Success' if result.success else 'Failed'}\n")
            f.write(f"Total Score: {result.total_score:.2f}/100\n")
            f.write(f"Automation Score: {result.automation_score:.2f}/100\n")
            f.write(f"YAML Score: {result.yaml_score:.2f}/100\n")
            f.write(f"Clarification Rounds: {result.clarification_rounds}\n")
            if result.error:
                f.write(f"\nError: {result.error}\n")
        
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
            for i in range(30):  # Wait up to 30 seconds
                await asyncio.sleep(1)
                async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
                    try:
                        response = await client.get(HEALTH_URL)
                        if response.status_code == 200:
                            logger.info("Service is healthy!")
                            return True
                    except:
                        pass
                if i % 5 == 0:
                    logger.info(f"Still waiting... ({i}/30)")
            
            logger.error("Service did not become healthy in time")
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
            "",
            "## Cycle Results",
            ""
        ]
        
        for i, cycle in enumerate(self.cycles, 1):
            status_icon = "[SUCCESS]" if cycle.success else "[FAILED]"
            summary_lines.extend([
                f"### Cycle {i}",
                f"- **Status**: {status_icon}",
                f"- **Total Score**: {cycle.total_score:.2f}/100",
                f"- **Automation Score**: {cycle.automation_score:.2f}/100",
                f"- **YAML Score**: {cycle.yaml_score:.2f}/100",
                f"- **Clarification Rounds**: {cycle.clarification_rounds}",
                f"- **Timestamp**: {cycle.timestamp}",
            ])
            
            if cycle.error:
                summary_lines.append(f"- **Error**: {cycle.error}")
            
            summary_lines.append("")
        
        # Trends
        if len(self.cycles) > 1:
            summary_lines.extend([
                "## Improvement Trends",
                ""
            ])
            
            scores = [c.total_score for c in self.cycles if c.success]
            if scores:
                summary_lines.extend([
                    f"- **Score Range**: {min(scores):.2f} - {max(scores):.2f}",
                    f"- **Average Score**: {sum(scores)/len(scores):.2f}",
                    f"- **Final Score**: {scores[-1]:.2f}",
                    ""
                ])
            
            clarification_counts = [c.clarification_rounds for c in self.cycles if c.success]
            if clarification_counts:
                summary_lines.extend([
                    f"- **Clarification Rounds**: {min(clarification_counts)} - {max(clarification_counts)}",
                    f"- **Average Rounds**: {sum(clarification_counts)/len(clarification_counts):.2f}",
                    ""
                ])
        
        # Final automation YAML
        final_cycle = next((c for c in reversed(self.cycles) if c.success), None)
        if final_cycle and final_cycle.automation_yaml:
            summary_lines.extend([
                "## Final Automation YAML",
                "",
                "```yaml",
                final_cycle.automation_yaml,
                "```",
                ""
            ])
        
        return "\n".join(summary_lines)
    
    def analyze_cycle(self, cycle_num: int, result: CycleResult, 
                     workflow_data: Dict[str, Any]) -> Dict[str, Any]:
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
        if result.total_score < 70:
            analysis['issues'].append(f"Total score below threshold: {result.total_score:.2f}")
            analysis['recommendations'].append(
                "Multiple areas need improvement - review all components"
            )
        
        return analysis
    
    def create_improvement_plan(self, cycle_num: int, analysis: Dict[str, Any]) -> str:
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


async def main():
    """Main entry point"""
    TerminalOutput.print_header("Ask AI Continuous Improvement Process")
    TerminalOutput.print_info(f"Target Prompt: {TARGET_PROMPT[:80]}...")
    TerminalOutput.print_info(f"Max Cycles: {MAX_CYCLES}")
    TerminalOutput.print_info(f"Output Directory: {OUTPUT_DIR}")
    
    manager = CycleManager(OUTPUT_DIR)
    overall_start = time.time()
    
    for cycle_num in range(1, MAX_CYCLES + 1):
        cycle_start = time.time()
        TerminalOutput.print_header(f"Cycle {cycle_num}/{MAX_CYCLES}", "=")
        
        async with AskAITester() as tester:
            # Check health
            if not await tester.check_health():
                TerminalOutput.print_error("Service is not healthy. Please start the service first.")
                sys.exit(1)
            
            # Run workflow
            result, workflow_data = await tester.run_full_workflow(TARGET_PROMPT)
            result.cycle_number = cycle_num
            manager.cycles.append(result)
            
            # Save cycle data
            TerminalOutput.print_info("Saving cycle data...")
            manager.save_cycle_data(cycle_num, result, workflow_data)
            cycle_elapsed = time.time() - cycle_start
            TerminalOutput.print_success(f"Cycle {cycle_num} data saved (cycle time: {cycle_elapsed:.2f}s)")
            
            # Check for errors - stop if critical error
            if result.error:
                TerminalOutput.print_error(f"Cycle {cycle_num} failed: {result.error}")
                
                # Create error report
                cycle_dir = OUTPUT_DIR / f"cycle-{cycle_num}"
                error_report = cycle_dir / "ERROR_REPORT.md"
                with open(error_report, 'w', encoding='utf-8') as f:
                    f.write(f"# Error Report - Cycle {cycle_num}\n\n")
                    f.write(f"**Timestamp**: {result.timestamp}\n\n")
                    f.write(f"**Error**: {result.error}\n\n")
                    f.write("## Next Steps\n\n")
                    f.write("1. Review the error message above\n")
                    f.write("2. Check service logs: `docker-compose logs ai-automation-service`\n")
                    f.write("3. Fix the issue in the code\n")
                    f.write("4. Deploy: `docker-compose build ai-automation-service && docker-compose restart ai-automation-service`\n")
                    f.write("5. Re-run this script\n")
                
                TerminalOutput.print_info(f"Error report saved to {error_report}")
                TerminalOutput.print_warning("Stopping for manual review and fixes.")
                break
            
            # Validate YAML - stop if invalid
            if result.yaml_score < 50:
                TerminalOutput.print_error(f"Cycle {cycle_num} generated invalid YAML (score: {result.yaml_score:.2f})")
                cycle_dir = OUTPUT_DIR / f"cycle-{cycle_num}"
                error_report = cycle_dir / "ERROR_REPORT.md"
                with open(error_report, 'w', encoding='utf-8') as f:
                    f.write(f"# YAML Validation Error - Cycle {cycle_num}\n\n")
                    f.write(f"**YAML Score**: {result.yaml_score:.2f}/100\n\n")
                    f.write("## Issue\n\n")
                    f.write("Generated YAML is invalid or severely malformed.\n\n")
                    f.write("## Next Steps\n\n")
                    f.write("1. Review the generated YAML in `automation.yaml`\n")
                    f.write("2. Check YAML generation logic in `ask_ai_router.py`\n")
                    f.write("3. Fix YAML generation code\n")
                    f.write("4. Deploy and re-run\n")
                
                TerminalOutput.print_info(f"Error report saved to {error_report}")
                TerminalOutput.print_warning("Stopping for manual review and fixes.")
                break
            
            # Analyze results
            TerminalOutput.print_info("Analyzing results...")
            analysis = manager.analyze_cycle(cycle_num, result, workflow_data)
            
            if analysis['issues']:
                TerminalOutput.print_warning(f"Found {len(analysis['issues'])} issue(s)")
                for issue in analysis['issues']:
                    TerminalOutput.print_info(f"  - {issue}", indent=1)
            
            # Create improvement plan
            if analysis['improvement_areas'] or result.total_score < 85:
                cycle_dir = OUTPUT_DIR / f"cycle-{cycle_num}"
                plan_path = cycle_dir / "IMPROVEMENT_PLAN.md"
                plan = manager.create_improvement_plan(cycle_num, analysis)
                with open(plan_path, 'w', encoding='utf-8') as f:
                    f.write(plan)
                TerminalOutput.print_info(f"Improvement plan saved to {plan_path}")
            
            # Check scores
            if result.total_score < 70:
                TerminalOutput.print_warning(f"Cycle {cycle_num} score is below threshold: {result.total_score:.2f}")
            elif result.total_score >= 85:
                TerminalOutput.print_success(f"Cycle {cycle_num} score is excellent: {result.total_score:.2f}")
            
            # If not last cycle, prepare for next iteration
            if cycle_num < MAX_CYCLES:
                TerminalOutput.print_info("\nPreparing for next cycle...")
                
                # If improvements needed, deploy updated service
                if analysis['improvement_areas']:
                    TerminalOutput.print_info("Improvements identified. Deploying updated service...")
                    deploy_success = await manager.deploy_service()
                    if not deploy_success:
                        TerminalOutput.print_error("Deployment failed. Stopping.")
                        break
                    TerminalOutput.print_success("Service deployed successfully. Waiting before next cycle...")
                    await asyncio.sleep(5)
                else:
                    TerminalOutput.print_info("No improvements needed. Continuing to next cycle...")
                    await asyncio.sleep(2)
    
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

