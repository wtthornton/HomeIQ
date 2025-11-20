"""
Clarification Service for Ask AI

Provides conversational clarification system for ambiguous automation requests.

2025 Best Practices:
- Full type hints (PEP 484/526)
- Async/await for database operations
- Calibrated confidence scores
- Adaptive thresholds
"""

from .models import (
    ClarificationQuestion,
    ClarificationAnswer,
    ClarificationSession,
    Ambiguity
)
from .detector import ClarificationDetector
from .question_generator import QuestionGenerator
from .answer_validator import AnswerValidator
from .confidence_calculator import ConfidenceCalculator
from .confidence_calibrator import ClarificationConfidenceCalibrator
from .outcome_tracker import ClarificationOutcomeTracker
from .rl_calibrator import RLConfidenceCalibrator, RLCalibrationConfig, RLFeedback
from .uncertainty_quantification import (
    ConfidenceWithUncertainty,
    UncertaintyQuantifier
)

__all__ = [
    'ClarificationQuestion',
    'ClarificationAnswer',
    'ClarificationSession',
    'Ambiguity',
    'ClarificationDetector',
    'QuestionGenerator',
    'AnswerValidator',
    'ConfidenceCalculator',
    'ClarificationConfidenceCalibrator',
    'ClarificationOutcomeTracker',
    'RLConfidenceCalibrator',
    'RLCalibrationConfig',
    'RLFeedback',
    'ConfidenceWithUncertainty',
    'UncertaintyQuantifier',
]

