"""
Data models for clarification system

2025 Best Practices:
- Dataclasses for type-safe data structures
- Enum types for type-safe constants
- Full type hints (PEP 484/526)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


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
    context: dict[str, Any] = field(default_factory=dict)
    related_entities: list[str] | None = None
    detected_text: str | None = None


@dataclass
class ClarificationQuestion:
    """Structured clarification question"""
    id: str
    category: str  # 'device', 'trigger', 'action', 'timing', 'condition'
    question_text: str  # Human-readable question
    question_type: QuestionType
    options: list[str] | None = None  # For multiple choice
    context: dict[str, Any] = field(default_factory=dict)  # Additional context
    priority: int = 2  # 1=critical, 2=important, 3=optional
    related_entities: list[str] | None = None  # Entity IDs mentioned
    ambiguity_id: str | None = None  # Related ambiguity ID


@dataclass
class ClarificationAnswer:
    """User's answer to a clarification question"""
    question_id: str
    answer_text: str
    selected_entities: list[str] | None = None  # For entity selection
    confidence: float = 0.0  # How confident we are in interpreting the answer
    validated: bool = False  # Whether answer was validated
    validation_errors: list[str] | None = None  # Validation error messages


@dataclass
class ClarificationSession:
    """
    Multi-round clarification conversation.
    
    Uses 2025 best practices: dataclass for type-safe structure.
    """
    session_id: str
    original_query: str
    questions: list[ClarificationQuestion] = field(default_factory=list)
    answers: list[ClarificationAnswer] = field(default_factory=list)
    current_confidence: float = 0.0
    confidence_threshold: float = 0.85  # Default threshold (can be adaptive)
    rounds_completed: int = 0
    max_rounds: int = 3  # Maximum clarification rounds
    status: Literal["in_progress", "complete", "abandoned"] = "in_progress"  # Type-safe status
    ambiguities: list[Ambiguity] = field(default_factory=list)
    query_id: str | None = None  # Related AskAI query ID

