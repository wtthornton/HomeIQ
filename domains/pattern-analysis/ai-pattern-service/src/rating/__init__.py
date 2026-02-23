"""
Blueprint Rating Module

Enables user feedback on automations and blueprints to improve recommendations.
Integrates with RL optimizer and pattern detection for continuous improvement.

Target: 4.0+ average user satisfaction rating
"""

from .rating_service import AutomationRating, BlueprintRating, RatingService

__all__ = [
    "RatingService",
    "AutomationRating",
    "BlueprintRating",
]
