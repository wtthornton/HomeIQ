"""
Feedback-Based Validation Learning (FBVL) for Quality Scoring

Uses validation data for both evaluation and real-time feedback to guide weight adjustments.
"""

import logging
from typing import Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class FBVLQualityScorer:
    """
    Feedback-Based Validation Learning for quality scoring.
    
    Uses validation data (ground truth, user feedback) to provide
    real-time feedback during quality calculation.
    """
    
    def __init__(self, validation_data: list[dict[str, Any]] | None = None):
        """
        Initialize FBVL quality scorer.
        
        Args:
            validation_data: List of validation patterns/synergies with known quality
        """
        self.validation_data = validation_data or []
        self.feedback_history: list[dict[str, Any]] = []
    
    def calculate_quality_with_feedback(
        self,
        pattern: dict[str, Any],
        base_quality: float
    ) -> dict[str, Any]:
        """
        Calculate quality with real-time validation feedback.
        
        Args:
            pattern: Pattern dictionary
            base_quality: Base quality score (from standard scorer)
        
        Returns:
            Dictionary with quality score and feedback
        """
        # Get validation feedback
        validation_feedback = self._get_validation_feedback(pattern)
        
        # Adjust quality based on feedback
        adjusted_quality = self._apply_feedback(base_quality, validation_feedback)
        
        result = {
            'quality_score': adjusted_quality,
            'base_quality': base_quality,
            'validation_feedback': validation_feedback,
            'adjustment': adjusted_quality - base_quality
        }
        
        # Store in history
        self.feedback_history.append({
            'pattern': pattern,
            'base_quality': base_quality,
            'adjusted_quality': adjusted_quality,
            'validation_feedback': validation_feedback,
            'timestamp': datetime.now(timezone.utc)
        })
        
        return result
    
    def _get_validation_feedback(self, pattern: dict[str, Any]) -> dict[str, Any]:
        """
        Get feedback from validation data.
        
        Returns:
            Dictionary with feedback information
        """
        feedback = {
            'ground_truth_match': False,
            'user_acceptance_rate': 0.0,
            'similar_pattern_quality': 0.0,
            'similar_pattern_count': 0
        }
        
        # Check ground truth
        for gt_pattern in self.validation_data:
            if self._patterns_match(pattern, gt_pattern):
                feedback['ground_truth_match'] = True
                feedback['similar_pattern_quality'] = gt_pattern.get('quality', 0.5)
                break
        
        # Check user acceptance for similar patterns
        similar_patterns = self._find_similar_patterns(pattern)
        if similar_patterns:
            acceptance_count = sum(
                1 for p in similar_patterns if p.get('user_accepted', False)
            )
            feedback['user_acceptance_rate'] = acceptance_count / len(similar_patterns)
            feedback['similar_pattern_count'] = len(similar_patterns)
        
        return feedback
    
    def _apply_feedback(
        self,
        base_quality: float,
        validation_feedback: dict[str, Any]
    ) -> float:
        """
        Apply validation feedback to adjust quality score.
        
        Args:
            base_quality: Base quality score
            validation_feedback: Validation feedback dictionary
        
        Returns:
            Adjusted quality score
        """
        adjustment = 0.0
        
        # Ground truth match: boost quality
        if validation_feedback.get('ground_truth_match', False):
            adjustment += 0.2
        
        # User acceptance rate: adjust based on acceptance
        acceptance_rate = validation_feedback.get('user_acceptance_rate', 0.0)
        if acceptance_rate > 0.7:
            # High acceptance: boost
            adjustment += 0.1
        elif acceptance_rate < 0.3:
            # Low acceptance: reduce
            adjustment -= 0.1
        
        # Similar pattern quality: adjust towards similar patterns
        similar_quality = validation_feedback.get('similar_pattern_quality', 0.0)
        if similar_quality > 0:
            # Move towards similar pattern quality (weighted average)
            adjustment += (similar_quality - base_quality) * 0.1
        
        # Apply adjustment and clamp to [0.0, 1.0]
        adjusted_quality = base_quality + adjustment
        return max(0.0, min(1.0, adjusted_quality))
    
    def _patterns_match(
        self,
        pattern1: dict[str, Any],
        pattern2: dict[str, Any]
    ) -> bool:
        """
        Check if two patterns match.
        
        Matches if:
        - Same pattern type
        - Same devices/entities
        """
        # Check pattern type
        type1 = pattern1.get('pattern_type', '')
        type2 = pattern2.get('pattern_type', '')
        if type1 != type2:
            return False
        
        # Check devices/entities
        devices1 = set()
        devices2 = set()
        
        for field in ['device1', 'device2', 'entity_id', 'device_id']:
            if pattern1.get(field):
                devices1.add(str(pattern1[field]))
            if pattern2.get(field):
                devices2.add(str(pattern2[field]))
        
        # Match if devices overlap
        return len(devices1.intersection(devices2)) > 0
    
    def _find_similar_patterns(
        self,
        pattern: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Find similar patterns in validation data.
        
        Returns:
            List of similar patterns
        """
        similar = []
        
        for val_pattern in self.validation_data:
            if self._patterns_match(pattern, val_pattern):
                similar.append(val_pattern)
        
        return similar
    
    def add_validation_data(self, pattern: dict[str, Any], quality: float, user_accepted: bool = False):
        """
        Add pattern to validation data.
        
        Args:
            pattern: Pattern dictionary
            quality: Known quality score
            user_accepted: Whether user accepted this pattern
        """
        validation_entry = {
            **pattern,
            'quality': quality,
            'user_accepted': user_accepted
        }
        self.validation_data.append(validation_entry)
    
    def get_feedback_statistics(self) -> dict[str, Any]:
        """Get feedback statistics"""
        if not self.feedback_history:
            return {
                'total_feedback': 0,
                'average_adjustment': 0.0,
                'ground_truth_matches': 0
            }
        
        adjustments = [f['adjustment'] for f in self.feedback_history]
        ground_truth_matches = sum(
            1 for f in self.feedback_history
            if f['validation_feedback'].get('ground_truth_match', False)
        )
        
        return {
            'total_feedback': len(self.feedback_history),
            'average_adjustment': sum(adjustments) / len(adjustments) if adjustments else 0.0,
            'ground_truth_matches': ground_truth_matches,
            'validation_data_size': len(self.validation_data)
        }

