"""
Data models for clarification system
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum


class AmbiguityType(str, Enum):
    """Types of ambiguities that can be detected"""
    DEVICE = "device"
    TRIGGER = "trigger"
    ACTION = "action"
    TIMING = "timing"
    CONDITION = "condition"


class AmbiguitySeverity(str, Enum):
    """Severity levels for ambiguities"""
    CRITICAL = "critical"  # Must be clarified before proceeding
    IMPORTANT = "important"  # Should be clarified
    OPTIONAL = "optional"  # Nice to have but not required


class QuestionType(str, Enum):
    """Types of clarification questions"""
    MULTIPLE_CHOICE = "multiple_choice"
    TEXT = "text"
    ENTITY_SELECTION = "entity_selection"
    BOOLEAN = "boolean"


@dataclass
class Ambiguity:
    """Represents an ambiguity detected in a query"""
    id: str
    type: AmbiguityType
    severity: AmbiguitySeverity
    description: str
    context: Dict[str, Any] = field(default_factory=dict)
    related_entities: Optional[List[str]] = None
    detected_text: Optional[str] = None


@dataclass
class ClarificationQuestion:
    """Structured clarification question"""
    id: str
    category: str  # 'device', 'trigger', 'action', 'timing', 'condition'
    question_text: str  # Human-readable question
    question_type: QuestionType
    options: Optional[List[str]] = None  # For multiple choice
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context
    priority: int = 2  # 1=critical, 2=important, 3=optional
    related_entities: Optional[List[str]] = None  # Entity IDs mentioned
    ambiguity_id: Optional[str] = None  # Related ambiguity ID


@dataclass
class ClarificationAnswer:
    """User's answer to a clarification question"""
    question_id: str
    answer_text: str
    selected_entities: Optional[List[str]] = None  # For entity selection
    confidence: float = 0.0  # How confident we are in interpreting the answer
    validated: bool = False  # Whether answer was validated
    validation_errors: Optional[List[str]] = None  # Validation error messages


@dataclass
class ClarificationSession:
    """Multi-round clarification conversation"""
    session_id: str
    original_query: str
    questions: List[ClarificationQuestion] = field(default_factory=list)
    answers: List[ClarificationAnswer] = field(default_factory=list)
    current_confidence: float = 0.0
    confidence_threshold: float = 0.85  # Default threshold
    rounds_completed: int = 0
    max_rounds: int = 3  # Maximum clarification rounds
    status: str = "in_progress"  # 'in_progress', 'complete', 'abandoned'
    ambiguities: List[Ambiguity] = field(default_factory=list)
    query_id: Optional[str] = None  # Related AskAI query ID

