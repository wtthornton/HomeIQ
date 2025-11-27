"""
Pattern Quality Scorer

Epic 39, Story 39.7: Pattern Learning & RLHF Migration
Assesses the quality of detected patterns using multiple factors.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PatternQualityScorer:
    """
    Calculate quality scores for detected patterns.
    
    Epic 39, Story 39.7: Extracted to pattern service.
    """
    
    def __init__(self, blueprint_validator=None, ground_truth_patterns=None, home_type: str | None = None):
        """
        Initialize pattern quality scorer.
        
        Args:
            blueprint_validator: Optional PatternBlueprintValidator for blueprint correlation
            ground_truth_patterns: Optional list of ground truth patterns for validation
            home_type: Optional home type classification for relevance weighting
        """
        self.blueprint_validator = blueprint_validator
        self.ground_truth_patterns = ground_truth_patterns or []
        self.home_type = home_type
    
    def calculate_quality_score(self, pattern: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate comprehensive quality score for a pattern.
        
        Quality Score Formula:
        - Base Quality (0.0-1.0):
          * Confidence (40%)
          * Occurrence Frequency (30%)
          * Temporal Consistency (20%)
          * Device Relationship (10%)
        
        - Validation Boost (0.0-0.3):
          * Blueprint match: +0.2
          * Ground truth match: +0.3
          * Pattern support: +0.1
        
        Final Quality = min(1.0, base_quality + validation_boost)
        
        Args:
            pattern: Pattern dictionary
        
        Returns:
            Dictionary with quality score and breakdown
        """
        # Calculate base quality components
        confidence_score = self._score_confidence(pattern)
        frequency_score = self._score_frequency(pattern)
        temporal_score = self._score_temporal_consistency(pattern)
        relationship_score = self._score_device_relationship(pattern)
        
        # Calculate base quality (weighted average)
        base_quality = (
            confidence_score * 0.40 +
            frequency_score * 0.30 +
            temporal_score * 0.20 +
            relationship_score * 0.10
        )
        
        # Calculate validation boost
        validation_boost = self._calculate_validation_boost(pattern)
        
        # Final quality score
        base_quality = max(0.0, min(1.0, base_quality))
        capped_validation_boost = min(0.3, validation_boost)
        quality_score = min(1.0, base_quality + capped_validation_boost)
        
        # Determine quality tier
        if quality_score >= 0.75:
            quality_tier = 'high'
        elif quality_score >= 0.50:
            quality_tier = 'medium'
        else:
            quality_tier = 'low'
        
        return {
            'quality_score': quality_score,
            'base_quality': base_quality,
            'validation_boost': validation_boost,
            'breakdown': {
                'confidence': confidence_score,
                'frequency': frequency_score,
                'temporal': temporal_score,
                'relationship': relationship_score
            },
            'quality_tier': quality_tier,
            'is_high_quality': quality_score >= 0.6
        }
    
    def _score_confidence(self, pattern: dict[str, Any]) -> float:
        """Score based on pattern confidence (0.0-1.0)"""
        confidence = pattern.get('confidence', 0.0)
        return max(0.0, min(1.0, float(confidence)))
    
    def _score_frequency(self, pattern: dict[str, Any]) -> float:
        """Score based on occurrence frequency"""
        occurrences = pattern.get('occurrences', pattern.get('count', 0))
        occurrences = max(0, int(occurrences))
        
        if occurrences == 0:
            return 0.0
        elif occurrences <= 2:
            return 0.3
        elif occurrences <= 5:
            return 0.6
        elif occurrences <= 10:
            return 0.8
        else:
            return 1.0
    
    def _score_temporal_consistency(self, pattern: dict[str, Any]) -> float:
        """Score based on temporal consistency"""
        pattern_type = pattern.get('pattern_type', '')
        
        if pattern_type == 'time_of_day':
            time_range = pattern.get('time_range', pattern.get('time', ''))
            if time_range:
                return 0.9
            return 0.5
        elif pattern_type == 'co_occurrence':
            window_minutes = pattern.get('window_minutes', 5)
            if 1 <= window_minutes <= 10:
                return 0.8
            elif window_minutes <= 30:
                return 0.6
            else:
                return 0.4
        
        return 0.5
    
    def _score_device_relationship(self, pattern: dict[str, Any]) -> float:
        """Score based on device relationship strength"""
        score = 0.0
        
        # Check for same area
        area1 = pattern.get('area1', pattern.get('area', ''))
        area2 = pattern.get('area2', '')
        if area1 and area2 and area1 == area2:
            score += 0.5
        
        # Check for logical pairing
        device1 = pattern.get('device1', '')
        device2 = pattern.get('device2', '')
        
        if device1 and device2:
            if 'motion' in device1.lower() and 'light' in device2.lower():
                score += 0.3
            elif 'door' in device1.lower() and 'lock' in device2.lower():
                score += 0.3
            elif 'temperature' in device1.lower() and 'climate' in device2.lower():
                score += 0.3
        
        return min(1.0, score)
    
    def _calculate_validation_boost(self, pattern: dict[str, Any]) -> float:
        """Calculate validation boost from external sources"""
        boost = 0.0
        
        # Blueprint validation
        if self.blueprint_validator:
            try:
                blueprint_match = pattern.get('blueprint_match', False)
                if blueprint_match:
                    boost += 0.2
            except Exception as e:
                logger.debug(f"Blueprint validation check failed: {e}")
        
        # Ground truth match
        if self.ground_truth_patterns:
            for gt_pattern in self.ground_truth_patterns:
                if self._patterns_match(pattern, gt_pattern):
                    boost += 0.3
                    break
        
        # Pattern support
        pattern_support = pattern.get('pattern_support_score', 0.0)
        if pattern_support > 0.7:
            boost += 0.1
        
        return min(0.3, boost)
    
    def _patterns_match(self, pattern1: dict[str, Any], pattern2: dict[str, Any]) -> bool:
        """Check if two patterns match"""
        type1 = pattern1.get('pattern_type', '')
        type2 = pattern2.get('pattern_type', '')
        if type1 != type2:
            return False
        
        devices1 = set()
        devices2 = set()
        
        for field in ['device1', 'device2', 'entity_id']:
            if pattern1.get(field):
                devices1.add(pattern1[field])
            if pattern2.get(field):
                devices2.add(pattern2[field])
        
        return len(devices1.intersection(devices2)) > 0

