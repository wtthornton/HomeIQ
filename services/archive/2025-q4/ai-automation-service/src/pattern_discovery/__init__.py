"""
Pattern Discovery Module

Automatically discovers automation patterns from community data.
"""

from .community_pattern_learner import CommunityPatternLearner, get_pattern_learner

__all__ = [
    'CommunityPatternLearner',
    'get_pattern_learner',
]
