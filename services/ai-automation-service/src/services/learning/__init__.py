"""
Active Learning Services

Epic AI-12, Phase 2: Active Learning
Services for learning from user feedback to improve entity resolution.
"""

from .active_learner import ActiveLearner
from .feedback_tracker import FeedbackTracker, FeedbackType, EntityResolutionFeedback
from .feedback_processor import FeedbackProcessor

__all__ = [
    'ActiveLearner',
    'FeedbackTracker',
    'FeedbackType',
    'EntityResolutionFeedback',
    'FeedbackProcessor'
]
