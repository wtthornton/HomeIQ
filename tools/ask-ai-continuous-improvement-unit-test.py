#!/usr/bin/env python3
"""
Ask AI Continuous Improvement Process - Unit Test Version

Unit test version that directly imports and tests the code modules instead of
making HTTP requests. This eliminates deployment time and runs much faster.

Differences from HTTP version:
- Directly imports and calls router functions
- Uses in-memory SQLite database
- Mocks external clients (HA, OpenAI, Device Intelligence)
- No docker-compose deployment steps
- Much faster execution
"""

import asyncio
import json
import yaml
import os
import sys
import time
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
from unittest.mock import AsyncMock, MagicMock, patch
import logging

# Initialize basic logger for .env loading
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load .env file from project root before setting any environment variables
def load_env_file():
    """Load environment variables from .env file"""
    # Try multiple locations for .env file
    env_files = [
        Path(__file__).parent.parent / ".env",  # Project root
        Path(__file__).parent / ".env",  # Tools directory
    ]
    
    loaded_from = None
    for env_file in env_files:
        if env_file.exists():
            try:
                # Try using python-dotenv if available
                try:
                    from dotenv import load_dotenv
                    load_dotenv(env_file, override=False)  # Don't override existing env vars
                    loaded_from = env_file
                    logger.info(f"✅ Loaded environment from {env_file} (using python-dotenv)")
                    break
                except ImportError:
                    # Fallback: manual parsing
                    logger.info(f"📁 Loading environment from {env_file} (manual parsing)")
                    with open(env_file, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                try:
                                    key, value = line.split('=', 1)
                                    key = key.strip()
                                    value = value.strip().strip('"\'')
                                    # Only set if not already in environment
                                    if key not in os.environ and '\x00' not in value:
                                        os.environ[key] = value
                                except Exception as e:
                                    logger.warning(f"⚠️  Error parsing line {line_num}: {line} - {e}")
                    loaded_from = env_file
                    logger.info(f"✅ Loaded environment from {env_file}")
                    break
            except Exception as e:
                logger.warning(f"⚠️  Error loading {env_file}: {e}")
                continue
    
    if not loaded_from:
        logger.warning("⚠️  No .env file found - using system environment variables only")
    
    return loaded_from

# Load .env file first
load_env_file()

# Add service path to sys.path for imports
# Add parent directory so 'src' is recognized as a package for relative imports
service_parent = Path(__file__).parent.parent / "services" / "ai-automation-service"
sys.path.insert(0, str(service_parent))

# Set default environment variables (only if not already set from .env)
# These defaults will be used if .env file doesn't have these values
# For Docker services, use localhost or Docker service names as appropriate
os.environ.setdefault('HA_URL', os.getenv('HA_URL') or os.getenv('HOME_ASSISTANT_URL') or 'http://localhost:8123')
os.environ.setdefault('HA_TOKEN', os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN') or '')
os.environ.setdefault('MQTT_BROKER', os.getenv('MQTT_BROKER') or 'localhost')
os.environ.setdefault('OPENAI_API_KEY', os.getenv('OPENAI_API_KEY') or '')
os.environ.setdefault('OPENVINO_SERVICE_URL', os.getenv('OPENVINO_SERVICE_URL') or 'http://localhost:8019')
os.environ.setdefault('DATA_API_URL', os.getenv('DATA_API_URL') or 'http://localhost:8006')
os.environ.setdefault('INFLUXDB_URL', os.getenv('INFLUXDB_URL') or 'http://localhost:8086')

# Database setup for testing
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

# Import router functions and models
from src.api.ask_ai_router import (
    process_natural_language_query,
    provide_clarification,
    approve_suggestion_from_query,
    AskAIQueryRequest,
    ClarificationRequest,
    ApproveSuggestionRequest,
    set_device_intelligence_client,
    _clarification_sessions
)
from src.database.models import Base, AskAIQuery as AskAIQueryModel
from src.clients.ha_client import HomeAssistantClient
from src.clients.device_intelligence_client import DeviceIntelligenceClient
from src.llm.openai_client import OpenAIClient

# Logger is already initialized above for .env loading

# Terminal output helpers (same as HTTP version)
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

# Configuration
TARGET_PROMPT = (
    "Every 15 mins choose a random effect on the Office WLED device. "
    "Play the effect for 15 secs. Choose random effect, random colors and brightness to 100%. "
    "At the end of the 15 sec the WLED light needs to return to exactly what it was before it started."
)
OUTPUT_DIR = Path("implementation/continuous-improvement-unit-test")
MAX_CYCLES = 25


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


# Reuse Scorer class from HTTP version
class Scorer:
    """Scoring system for automation correctness, YAML validity, and clarification count"""
    
    @staticmethod
    def score_automation_correctness(yaml_str: str, prompt: str) -> float:
        """Score automation correctness based on prompt requirements. Returns score 0-100."""
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
        
        if score < max_score:
            TerminalOutput.print_info(f"Automation correctness: {score:.1f}/100 ({len([c for c in checks if c.startswith('✓')])}/{len(checks)} checks passed)")
        return min(score, max_score)
    
    @staticmethod
    def score_yaml_validity(yaml_str: str) -> float:
        """Score YAML validity and Home Assistant structure. Returns score 0-100."""
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
        for field in required_fields:
            if field in yaml_data:
                score += 7.5
                checks.append(f"✓ Required field '{field}' present")
            else:
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
        if re.search(r'light\.\w+|entity_id:\s*light\.\w+', yaml_str):
            score += 10.0
            checks.append("✓ Valid entity ID format")
        else:
            checks.append("✗ No valid entity IDs found")
        
        if score < max_score:
            TerminalOutput.print_info(f"YAML validity: {score:.1f}/100 ({len([c for c in checks if c.startswith('✓')])}/{len(checks)} checks passed)")
        return min(score, max_score)
    
    @staticmethod
    def calculate_total_score(automation_score: float, yaml_score: float, 
                             clarification_count: int) -> Dict[str, Any]:
        """Calculate weighted total score."""
        clarification_score = max(0.0, 100.0 - (clarification_count * 10.0))
        
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
    
    def answer_question(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """Generate answer for a clarification question based on prompt context."""
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
                wled_office_entities = [
                    e for e in related_entities 
                    if 'wled' in e.lower() and 'office' in e.lower()
                ]
                if wled_office_entities:
                    answer['selected_entities'] = wled_office_entities[:1]
                    answer['answer_text'] = wled_office_entities[0]
                else:
                    wled_entities = [
                        e for e in related_entities 
                        if 'wled' in e.lower()
                    ]
                    if wled_entities:
                        answer['selected_entities'] = wled_entities[:1]
                        answer['answer_text'] = wled_entities[0]
                    else:
                        office_light_entities = [
                            e for e in related_entities 
                            if 'office' in e.lower() and 'light' in e.lower() and 'tv' not in e.lower()
                        ]
                        if office_light_entities:
                            answer['selected_entities'] = office_light_entities[:1]
                            answer['answer_text'] = office_light_entities[0]
                        else:
                            answer['selected_entities'] = [related_entities[0]]
                            answer['answer_text'] = related_entities[0]
            else:
                answer['answer_text'] = 'WLED Office Light'
        
        # Multiple choice questions
        elif question_type == 'multiple_choice' and options:
            if 'office' in question_text or 'device' in question_text or 'wled' in question_text:
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
                answer['answer_text'] = options[0]
        
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
                answer['answer_text'] = 'Yes'
        
        return answer


class TestDatabase:
    """In-memory test database setup"""
    
    def __init__(self):
        self.engine = None
        self.async_session = None
    
    async def setup(self):
        """Create in-memory database"""
        self.engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def get_session(self) -> AsyncSession:
        """Get new database session"""
        return self.async_session()
    
    async def cleanup(self):
        """Clean up database"""
        if self.engine:
            await self.engine.dispose()


class RealClients:
    """Create real clients that connect to Docker services"""
    
    @staticmethod
    def create_ha_client() -> HomeAssistantClient:
        """Create real Home Assistant client"""
        ha_url = os.getenv('HA_URL') or os.getenv('HOME_ASSISTANT_URL') or 'http://localhost:8123'
        ha_token = os.getenv('HA_TOKEN') or os.getenv('HOME_ASSISTANT_TOKEN') or ''
        return HomeAssistantClient(ha_url, ha_token)
    
    @staticmethod
    def create_openai_client() -> OpenAIClient:
        """Create real OpenAI client"""
        openai_key = os.getenv('OPENAI_API_KEY') or ''
        return OpenAIClient(api_key=openai_key)
    
    @staticmethod
    def create_device_intelligence_client() -> DeviceIntelligenceClient:
        """Create real Device Intelligence client"""
        device_intelligence_url = os.getenv('DEVICE_INTELLIGENCE_URL') or os.getenv('OPENVINO_SERVICE_URL') or 'http://localhost:8019'
        return DeviceIntelligenceClient(base_url=device_intelligence_url)


class AskAITester:
    """Main test runner using direct function calls"""
    
    def __init__(self):
        self.scorer = Scorer()
        self.clarification_handler = ClarificationHandler(TARGET_PROMPT)
        self.db = TestDatabase()
        self.ha_client = None
        self.openai_client = None
        self.device_intelligence_client = None
    
    async def __aenter__(self):
        await self.db.setup()
        self.ha_client = RealClients.create_ha_client()
        self.openai_client = RealClients.create_openai_client()
        self.device_intelligence_client = RealClients.create_device_intelligence_client()
        set_device_intelligence_client(self.device_intelligence_client)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.db.cleanup()
        # Clear clarification sessions
        _clarification_sessions.clear()
    
    async def check_health(self) -> bool:
        """Check if test setup is ready"""
        TerminalOutput.print_info("Checking test setup...")
        if self.db.engine:
            TerminalOutput.print_success("Test database ready")
            return True
        return False
    
    async def submit_query(self, query: str, user_id: str = "continuous_improvement") -> Dict[str, Any]:
        """Submit query using direct function call"""
        TerminalOutput.print_info(f"Submitting query: {query[:80]}...")
        start_time = time.time()
        
        try:
            db_session = await self.db.get_session()
            request = AskAIQueryRequest(query=query, user_id=user_id)
            
            # Call the router function directly
            response = await process_natural_language_query(
                request=request,
                db=db_session
            )
            
            elapsed = time.time() - start_time
            TerminalOutput.print_success(f"Query submitted successfully (time: {elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Query ID: {response.query_id}", indent=1)
            TerminalOutput.print_info(f"  Clarification needed: {response.clarification_needed}", indent=1)
            TerminalOutput.print_info(f"  Initial suggestions: {len(response.suggestions)}", indent=1)
            
            # Convert response to dict format
            return {
                'query_id': response.query_id,
                'clarification_needed': response.clarification_needed,
                'clarification_session_id': response.clarification_session_id,
                'questions': response.questions or [],
                'suggestions': response.suggestions
            }
        except Exception as e:
            elapsed = time.time() - start_time
            TerminalOutput.print_error(f"Query failed (time: {elapsed:.2f}s): {e}")
            raise
    
    async def handle_clarifications(self, session_id: str, 
                                   initial_questions: List[Dict[str, Any]]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Handle clarification loop until complete"""
        clarification_log = []
        current_questions = initial_questions
        max_rounds = 10
        clarification_response = None
        
        while current_questions and len(clarification_log) < max_rounds:
            round_num = len(clarification_log) + 1
            TerminalOutput.print_info(f"Clarification Round {round_num}/{max_rounds}: {len(current_questions)} question(s)")
            
            for i, q in enumerate(current_questions, 1):
                q_text = q.get('question_text', 'Unknown question')[:60]
                TerminalOutput.print_info(f"  Q{i}: {q_text}...", indent=1)
            
            TerminalOutput.print_info("Generating auto-answers...", indent=1)
            answers = []
            for q in current_questions:
                answer = self.clarification_handler.answer_question(q)
                answers.append(answer)
                answer_text = answer.get('answer_text', '')[:50]
                TerminalOutput.print_info(f"  A: {answer_text}...", indent=2)
            
            qa_round = {
                'round': round_num,
                'questions': current_questions,
                'answers': answers,
                'timestamp': datetime.now().isoformat()
            }
            clarification_log.append(qa_round)
            
            TerminalOutput.print_info("Submitting answers...", indent=1)
            start_time = time.time()
            try:
                db_session = await self.db.get_session()
                request = ClarificationRequest(session_id=session_id, answers=answers)
                
                clarification_response = await provide_clarification(
                    request=request,
                    db=db_session,
                    ha_client=self.ha_client
                )
                
                elapsed = time.time() - start_time
                TerminalOutput.print_success(f"Answers submitted (time: {elapsed:.2f}s)")
            except Exception as e:
                elapsed = time.time() - start_time
                TerminalOutput.print_error(f"Clarification failed (time: {elapsed:.2f}s): {e}")
                raise
            
            if clarification_response.clarification_complete:
                TerminalOutput.print_success(f"Clarification complete! (confidence: {clarification_response.confidence:.1%}, suggestions: {len(clarification_response.suggestions or [])})")
                return {
                    'clarification_complete': True,
                    'confidence': clarification_response.confidence,
                    'suggestions': clarification_response.suggestions or [],
                    'questions': []
                }, clarification_log
            
            current_questions = clarification_response.questions or []
            if not current_questions:
                TerminalOutput.print_warning("No more questions but clarification not marked complete")
                break
        
        if len(clarification_log) >= max_rounds:
            raise Exception(f"Clarification exceeded maximum rounds ({max_rounds})")
        
        if not clarification_response:
            raise Exception("Clarification response is missing")
        
        return {
            'clarification_complete': clarification_response.clarification_complete,
            'confidence': clarification_response.confidence,
            'suggestions': clarification_response.suggestions or [],
            'questions': clarification_response.questions or []
        }, clarification_log
    
    async def approve_suggestion(self, query_id: str, suggestion_id: str) -> Dict[str, Any]:
        """Approve suggestion using direct function call"""
        TerminalOutput.print_info(f"Approving suggestion {suggestion_id}...")
        TerminalOutput.print_info(f"  Query ID: {query_id}", indent=1)
        start_time = time.time()
        
        try:
            db_session = await self.db.get_session()
            request = ApproveSuggestionRequest()
            
            result = await approve_suggestion_from_query(
                query_id=query_id,
                suggestion_id=suggestion_id,
                request=request,
                db=db_session,
                ha_client=self.ha_client,
                openai_client=self.openai_client
            )
            
            elapsed = time.time() - start_time
            TerminalOutput.print_success(f"Suggestion approved (time: {elapsed:.2f}s)")
            TerminalOutput.print_info(f"  Automation ID: {result.get('automation_id', 'unknown')}", indent=1)
            TerminalOutput.print_info(f"  YAML generated: {bool(result.get('automation_yaml'))}", indent=1)
            
            return result
        except Exception as e:
            elapsed = time.time() - start_time
            TerminalOutput.print_error(f"Approval failed (time: {elapsed:.2f}s): {e}")
            raise
    
    async def run_full_workflow(self, query: str) -> Tuple[CycleResult, Dict[str, Any]]:
        """Run complete workflow: query → clarifications → approve"""
        result = CycleResult(cycle_number=0)
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
                    
                    if clarification_response.get('clarification_complete', False):
                        approval_query_id = session_id
                        TerminalOutput.print_info(f"Using clarification_query_id ({session_id}) for approval")
                    
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
            
            # Approve suggestion
            try:
                approval_response = await self.approve_suggestion(approval_query_id, result.suggestion_id)
            except Exception as e:
                if approval_query_id != result.query_id and "not found" in str(e).lower():
                    TerminalOutput.print_warning(f"Approval with clarification_query_id failed, trying original query_id")
                    approval_response = await self.approve_suggestion(result.query_id, result.suggestion_id)
                else:
                    raise
            workflow_data['approval_response'] = approval_response
            result.automation_id = approval_response.get('automation_id')
            result.automation_yaml = approval_response.get('automation_yaml')
            
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
    """Manages improvement cycles (same as HTTP version but without deployment)"""
    
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cycles: List[CycleResult] = []
    
    def save_cycle_data(self, cycle_num: int, result: CycleResult, 
                       workflow_data: Dict[str, Any]):
        """Save all cycle data to files"""
        cycle_dir = self.output_dir / f"cycle-{cycle_num}"
        cycle_dir.mkdir(exist_ok=True)
        
        if workflow_data.get('query_response'):
            with open(cycle_dir / "query_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['query_response'], f, indent=2)
        
        if result.clarification_log:
            with open(cycle_dir / "clarification_rounds.json", 'w', encoding='utf-8') as f:
                json.dump(result.clarification_log, f, indent=2)
        
        if workflow_data.get('clarification_response'):
            with open(cycle_dir / "clarification_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['clarification_response'], f, indent=2)
        
        if workflow_data.get('selected_suggestion'):
            with open(cycle_dir / "suggestion_selected.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['selected_suggestion'], f, indent=2)
        
        if workflow_data.get('approval_response'):
            with open(cycle_dir / "approval_response.json", 'w', encoding='utf-8') as f:
                json.dump(workflow_data['approval_response'], f, indent=2)
        
        if result.automation_yaml:
            with open(cycle_dir / "automation.yaml", 'w', encoding='utf-8') as f:
                f.write(result.automation_yaml)
        
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
        
        with open(cycle_dir / "result.json", 'w', encoding='utf-8') as f:
            json.dump(asdict(result), f, indent=2, default=str)
        
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
    
    def generate_summary(self) -> str:
        """Generate summary of all cycles"""
        summary_lines = [
            "# Ask AI Continuous Improvement Summary (Unit Test Version)",
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


async def main():
    """Main entry point"""
    TerminalOutput.print_header("Ask AI Continuous Improvement Process - Unit Test Version")
    TerminalOutput.print_info(f"Target Prompt: {TARGET_PROMPT[:80]}...")
    TerminalOutput.print_info(f"Max Cycles: {MAX_CYCLES}")
    TerminalOutput.print_info(f"Output Directory: {OUTPUT_DIR}")
    TerminalOutput.print_info("Environment: Loaded from .env file (AI tokens and keys)")
    TerminalOutput.print_info("NOTE: This version uses direct function calls and connects to real Docker services!")
    
    manager = CycleManager(OUTPUT_DIR)
    overall_start = time.time()
    
    for cycle_num in range(1, MAX_CYCLES + 1):
        cycle_start = time.time()
        TerminalOutput.print_header(f"Cycle {cycle_num}/{MAX_CYCLES}", "=")
        
        async with AskAITester() as tester:
            # Check setup
            if not await tester.check_health():
                TerminalOutput.print_error("Test setup failed. Please check configuration.")
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
            
            # Check for errors
            if result.error:
                TerminalOutput.print_error(f"Cycle {cycle_num} failed: {result.error}")
                cycle_dir = OUTPUT_DIR / f"cycle-{cycle_num}"
                error_report = cycle_dir / "ERROR_REPORT.md"
                with open(error_report, 'w', encoding='utf-8') as f:
                    f.write(f"# Error Report - Cycle {cycle_num}\n\n")
                    f.write(f"**Timestamp**: {result.timestamp}\n\n")
                    f.write(f"**Error**: {result.error}\n\n")
                    f.write("## Next Steps\n\n")
                    f.write("1. Review the error message above\n")
                    f.write("2. Check the code for issues\n")
                    f.write("3. Fix the issue and re-run\n")
                TerminalOutput.print_info(f"Error report saved to {error_report}")
                TerminalOutput.print_warning("Stopping for manual review and fixes.")
                break
            
            # Validate YAML
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
                    f.write("2. Check YAML generation logic\n")
                    f.write("3. Fix YAML generation code\n")
                    f.write("4. Re-run\n")
                TerminalOutput.print_info(f"Error report saved to {error_report}")
                TerminalOutput.print_warning("Stopping for manual review and fixes.")
                break
            
            # Check scores
            if result.total_score < 70:
                TerminalOutput.print_warning(f"Cycle {cycle_num} score is below threshold: {result.total_score:.2f}")
            elif result.total_score >= 85:
                TerminalOutput.print_success(f"Cycle {cycle_num} score is excellent: {result.total_score:.2f}")
            
            # Brief pause between cycles
            if cycle_num < MAX_CYCLES:
                TerminalOutput.print_info("\nPreparing for next cycle...")
                await asyncio.sleep(1)
    
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

