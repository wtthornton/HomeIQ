"""
Learning services for Q&A enhancement and pattern quality learning.

Provides services for learning from Q&A sessions, user preferences,
question quality, automation outcomes, and pattern feedback.

Created: January 2025
Story: Q&A Learning Enhancement Plan, Epic AI-13 Pattern Quality Learning
"""

from .qa_outcome_tracker import QAOutcomeTracker
from .user_preference_learner import UserPreferenceLearner
from .question_quality_tracker import QuestionQualityTracker
from .ambiguity_learner import AmbiguityLearner
from .pattern_learner import PatternLearner
from .metrics_collector import MetricsCollector
from .pattern_feedback_tracker import PatternFeedbackTracker
from .feedback_aggregator import PatternFeedbackAggregator

__all__ = [
    'QAOutcomeTracker',
    'UserPreferenceLearner',
    'QuestionQualityTracker',
    'AmbiguityLearner',
    'PatternLearner',
    'MetricsCollector',
    'PatternFeedbackTracker',
    'PatternFeedbackAggregator',
]

