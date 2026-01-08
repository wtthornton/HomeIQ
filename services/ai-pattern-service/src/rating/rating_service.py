"""
Rating Service

Manages user ratings for automations and blueprints.
Integrates with RL optimizer to improve recommendations based on feedback.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class RatingCategory(str, Enum):
    """Categories for rating feedback."""
    
    OVERALL = "overall"
    RELEVANCE = "relevance"
    RELIABILITY = "reliability"
    EASE_OF_USE = "ease_of_use"
    PERFORMANCE = "performance"


@dataclass
class AutomationRating:
    """Rating for a deployed automation."""
    
    automation_id: str
    synergy_id: str | None
    blueprint_id: str | None
    
    # Ratings (1-5 scale)
    overall_rating: float
    relevance_rating: float | None = None
    reliability_rating: float | None = None
    ease_of_use_rating: float | None = None
    
    # Feedback
    feedback_text: str | None = None
    would_recommend: bool | None = None
    
    # Metadata
    rated_at: datetime = field(default_factory=datetime.utcnow)
    rated_by: str = "user"
    
    # Computed
    @property
    def average_rating(self) -> float:
        """Calculate average across all provided ratings."""
        ratings = [self.overall_rating]
        if self.relevance_rating:
            ratings.append(self.relevance_rating)
        if self.reliability_rating:
            ratings.append(self.reliability_rating)
        if self.ease_of_use_rating:
            ratings.append(self.ease_of_use_rating)
        return sum(ratings) / len(ratings)


@dataclass
class BlueprintRating:
    """Aggregated rating for a blueprint."""
    
    blueprint_id: str
    
    # Aggregated metrics
    total_ratings: int = 0
    average_overall: float = 0.0
    average_relevance: float = 0.0
    average_reliability: float = 0.0
    average_ease_of_use: float = 0.0
    
    # Recommendation metrics
    recommendation_rate: float = 0.0  # % who would recommend
    
    # Individual ratings
    ratings: list[AutomationRating] = field(default_factory=list)
    
    # Computed
    @property
    def composite_score(self) -> float:
        """Calculate composite score for blueprint ranking."""
        if self.total_ratings == 0:
            return 0.0
        
        # Weight: overall (40%), reliability (30%), relevance (20%), ease (10%)
        score = (
            self.average_overall * 0.4 +
            self.average_reliability * 0.3 +
            self.average_relevance * 0.2 +
            self.average_ease_of_use * 0.1
        )
        
        # Boost for high recommendation rate
        if self.recommendation_rate > 0.8:
            score *= 1.1
        
        return min(5.0, score)


class RatingService:
    """
    Service for managing automation and blueprint ratings.
    
    Integrates with:
    - RL Optimizer: Provides feedback signals for reinforcement learning
    - Pattern Detection: Adjusts pattern confidence based on ratings
    - Blueprint Opportunity: Updates fit scores based on community ratings
    """
    
    def __init__(self, min_ratings_for_confidence: int = 5):
        """
        Initialize rating service.
        
        Args:
            min_ratings_for_confidence: Minimum ratings before affecting recommendations
        """
        self.min_ratings_for_confidence = min_ratings_for_confidence
        self._automation_ratings: dict[str, list[AutomationRating]] = defaultdict(list)
        self._blueprint_ratings: dict[str, BlueprintRating] = {}
        self._device_feedback: dict[str, list[float]] = defaultdict(list)  # device_id -> ratings
        
        logger.info(
            f"RatingService initialized (min_ratings={min_ratings_for_confidence})"
        )
    
    def submit_rating(
        self,
        automation_id: str,
        overall_rating: float,
        synergy_id: str | None = None,
        blueprint_id: str | None = None,
        relevance_rating: float | None = None,
        reliability_rating: float | None = None,
        ease_of_use_rating: float | None = None,
        feedback_text: str | None = None,
        would_recommend: bool | None = None,
        rated_by: str = "user",
    ) -> AutomationRating:
        """
        Submit a rating for an automation.
        
        Args:
            automation_id: Home Assistant automation entity ID
            overall_rating: Overall rating (1-5)
            synergy_id: Optional synergy that created this automation
            blueprint_id: Optional blueprint used
            relevance_rating: How relevant was the suggestion (1-5)
            reliability_rating: How reliable is the automation (1-5)
            ease_of_use_rating: How easy to set up (1-5)
            feedback_text: Optional text feedback
            would_recommend: Would user recommend this automation
            rated_by: User identifier
            
        Returns:
            AutomationRating object
        """
        rating = AutomationRating(
            automation_id=automation_id,
            synergy_id=synergy_id,
            blueprint_id=blueprint_id,
            overall_rating=overall_rating,
            relevance_rating=relevance_rating,
            reliability_rating=reliability_rating,
            ease_of_use_rating=ease_of_use_rating,
            feedback_text=feedback_text,
            would_recommend=would_recommend,
            rated_by=rated_by,
        )
        
        # Store automation rating
        self._automation_ratings[automation_id].append(rating)
        
        # Update blueprint rating if applicable
        if blueprint_id:
            self._update_blueprint_rating(blueprint_id, rating)
        
        logger.info(
            f"Rating submitted: automation={automation_id}, "
            f"overall={overall_rating}, blueprint={blueprint_id}"
        )
        
        return rating
    
    def get_automation_ratings(self, automation_id: str) -> list[AutomationRating]:
        """Get all ratings for an automation."""
        return self._automation_ratings.get(automation_id, [])
    
    def get_automation_average_rating(self, automation_id: str) -> float | None:
        """Get average rating for an automation."""
        ratings = self._automation_ratings.get(automation_id, [])
        if not ratings:
            return None
        return sum(r.overall_rating for r in ratings) / len(ratings)
    
    def get_blueprint_rating(self, blueprint_id: str) -> BlueprintRating | None:
        """Get aggregated rating for a blueprint."""
        return self._blueprint_ratings.get(blueprint_id)
    
    def get_blueprint_score(self, blueprint_id: str) -> float:
        """
        Get blueprint score for ranking (0-5 scale).
        
        Returns 0 if not enough ratings for confidence.
        """
        bp_rating = self._blueprint_ratings.get(blueprint_id)
        if not bp_rating or bp_rating.total_ratings < self.min_ratings_for_confidence:
            return 0.0
        return bp_rating.composite_score
    
    def get_device_feedback_score(self, device_id: str) -> float:
        """
        Get feedback score for a device based on automation ratings.
        
        Used by pattern detection to adjust confidence.
        
        Returns:
            Score from 0.5 (negative) to 1.5 (positive), 1.0 is neutral
        """
        ratings = self._device_feedback.get(device_id, [])
        if len(ratings) < self.min_ratings_for_confidence:
            return 1.0  # Neutral
        
        avg_rating = sum(ratings) / len(ratings)
        
        # Map 1-5 rating to 0.5-1.5 multiplier
        # 1.0 -> 0.5, 3.0 -> 1.0, 5.0 -> 1.5
        return 0.5 + (avg_rating - 1.0) / 4.0
    
    def record_device_feedback(
        self,
        device_id: str,
        rating: float,
    ) -> None:
        """
        Record feedback for a device (from automation ratings).
        
        Used to adjust pattern confidence for devices.
        """
        self._device_feedback[device_id].append(rating)
    
    def get_feedback_for_rl_optimizer(
        self,
        synergy_id: str,
    ) -> dict[str, Any] | None:
        """
        Get feedback data formatted for RL optimizer.
        
        Returns:
            Dictionary with reward signal and context for RL
        """
        # Find ratings for this synergy
        synergy_ratings = []
        for ratings in self._automation_ratings.values():
            for rating in ratings:
                if rating.synergy_id == synergy_id:
                    synergy_ratings.append(rating)
        
        if not synergy_ratings:
            return None
        
        # Calculate reward signal (normalized to -1 to 1)
        avg_rating = sum(r.overall_rating for r in synergy_ratings) / len(synergy_ratings)
        reward = (avg_rating - 3.0) / 2.0  # Maps 1-5 to -1 to 1
        
        # Calculate recommendation rate
        recommendations = [r.would_recommend for r in synergy_ratings if r.would_recommend is not None]
        rec_rate = sum(recommendations) / len(recommendations) if recommendations else 0.5
        
        return {
            "synergy_id": synergy_id,
            "reward": reward,
            "average_rating": avg_rating,
            "recommendation_rate": rec_rate,
            "num_ratings": len(synergy_ratings),
            "feedback_texts": [r.feedback_text for r in synergy_ratings if r.feedback_text],
        }
    
    def get_top_rated_blueprints(self, limit: int = 10) -> list[BlueprintRating]:
        """
        Get top-rated blueprints.
        
        Args:
            limit: Maximum number of blueprints to return
            
        Returns:
            List of BlueprintRating sorted by composite score
        """
        # Filter blueprints with enough ratings
        qualified = [
            bp for bp in self._blueprint_ratings.values()
            if bp.total_ratings >= self.min_ratings_for_confidence
        ]
        
        # Sort by composite score
        qualified.sort(key=lambda bp: bp.composite_score, reverse=True)
        
        return qualified[:limit]
    
    def get_satisfaction_summary(self, days: int = 30) -> dict[str, Any]:
        """
        Get user satisfaction summary for the period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with satisfaction metrics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        # Collect all ratings in period
        period_ratings = []
        for ratings in self._automation_ratings.values():
            for rating in ratings:
                if rating.rated_at >= cutoff:
                    period_ratings.append(rating)
        
        if not period_ratings:
            return {
                "period_days": days,
                "total_ratings": 0,
                "average_overall": 0.0,
                "target": 4.0,
                "achieved": False,
            }
        
        avg_overall = sum(r.overall_rating for r in period_ratings) / len(period_ratings)
        
        # Calculate category averages
        relevance_ratings = [r.relevance_rating for r in period_ratings if r.relevance_rating]
        reliability_ratings = [r.reliability_rating for r in period_ratings if r.reliability_rating]
        ease_ratings = [r.ease_of_use_rating for r in period_ratings if r.ease_of_use_rating]
        
        recommendations = [r.would_recommend for r in period_ratings if r.would_recommend is not None]
        
        return {
            "period_days": days,
            "total_ratings": len(period_ratings),
            "average_overall": avg_overall,
            "average_relevance": sum(relevance_ratings) / len(relevance_ratings) if relevance_ratings else None,
            "average_reliability": sum(reliability_ratings) / len(reliability_ratings) if reliability_ratings else None,
            "average_ease_of_use": sum(ease_ratings) / len(ease_ratings) if ease_ratings else None,
            "recommendation_rate": sum(recommendations) / len(recommendations) if recommendations else None,
            "target": 4.0,
            "achieved": avg_overall >= 4.0,
            "progress_pct": min(100, avg_overall / 4.0 * 100),
        }
    
    def _update_blueprint_rating(
        self,
        blueprint_id: str,
        rating: AutomationRating,
    ) -> None:
        """Update aggregated blueprint rating with new automation rating."""
        if blueprint_id not in self._blueprint_ratings:
            self._blueprint_ratings[blueprint_id] = BlueprintRating(
                blueprint_id=blueprint_id
            )
        
        bp_rating = self._blueprint_ratings[blueprint_id]
        bp_rating.ratings.append(rating)
        bp_rating.total_ratings = len(bp_rating.ratings)
        
        # Recalculate averages
        bp_rating.average_overall = sum(r.overall_rating for r in bp_rating.ratings) / bp_rating.total_ratings
        
        relevance_ratings = [r.relevance_rating for r in bp_rating.ratings if r.relevance_rating]
        if relevance_ratings:
            bp_rating.average_relevance = sum(relevance_ratings) / len(relevance_ratings)
        
        reliability_ratings = [r.reliability_rating for r in bp_rating.ratings if r.reliability_rating]
        if reliability_ratings:
            bp_rating.average_reliability = sum(reliability_ratings) / len(reliability_ratings)
        
        ease_ratings = [r.ease_of_use_rating for r in bp_rating.ratings if r.ease_of_use_rating]
        if ease_ratings:
            bp_rating.average_ease_of_use = sum(ease_ratings) / len(ease_ratings)
        
        # Calculate recommendation rate
        recommendations = [r.would_recommend for r in bp_rating.ratings if r.would_recommend is not None]
        if recommendations:
            bp_rating.recommendation_rate = sum(recommendations) / len(recommendations)
