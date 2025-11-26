"""
Pattern Quality Scorer

Assesses the quality of detected patterns using multiple factors:
- Confidence score
- Occurrence frequency
- Temporal consistency
- Device relationship strength
- Blueprint correlation
- Ground truth matching
"""

import logging
from typing import Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PatternQualityScorer:
    """Calculate quality scores for detected patterns"""
    
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
            pattern: Pattern dictionary with fields like:
                - confidence: float (0.0-1.0)
                - occurrences: int
                - device1, device2: str (for co-occurrence)
                - entity_id: str (for time-of-day)
                - time, time_range: str (for temporal patterns)
                - pattern_type: str
        
        Returns:
            Dictionary with:
            - quality_score: float (0.0-1.0)
            - base_quality: float
            - validation_boost: float
            - breakdown: dict with component scores
            - quality_tier: str ('high' | 'medium' | 'low')
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
        
        # Apply home type relevance boost (Home Type Integration)
        home_type_relevance = 0.0
        if self.home_type:
            home_type_relevance = self._calculate_home_type_relevance(pattern)
            # Boost quality score by up to 10% based on home type relevance
            base_quality = base_quality * (1.0 + home_type_relevance * 0.1)
        
        # Final quality score with improved normalization
        # Cap validation boost at 0.3 (absolute cap) and ensure base_quality is in [0, 1]
        base_quality = max(0.0, min(1.0, base_quality))  # Clamp base_quality first
        capped_validation_boost = min(0.3, validation_boost)  # Absolute cap at 0.3
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
            'home_type_relevance': home_type_relevance if self.home_type else None,
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
        # Clamp to [0.0, 1.0] range
        return max(0.0, min(1.0, float(confidence)))
    
    def _score_frequency(self, pattern: dict[str, Any]) -> float:
        """
        Score based on occurrence frequency.
        
        Normalized to [0.0, 1.0] range.
        
        Scoring:
        - 0 occurrences: 0.0
        - 1-2 occurrences: 0.3
        - 3-5 occurrences: 0.6
        - 6-10 occurrences: 0.8
        - 11+ occurrences: 1.0
        """
        occurrences = pattern.get('occurrences', pattern.get('count', 0))
        
        # Ensure occurrences is non-negative integer
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
        """
        Score based on temporal consistency.
        
        For time-of-day patterns: Check if time is consistent
        For co-occurrence: Check if timing window is consistent
        """
        pattern_type = pattern.get('pattern_type', '')
        
        if pattern_type == 'time_of_day':
            # Time-of-day patterns should have consistent times
            time_range = pattern.get('time_range', pattern.get('time', ''))
            if time_range:
                return 0.9  # High score for explicit time patterns
            return 0.5  # Medium score if time not specified
        
        elif pattern_type == 'co_occurrence':
            # Co-occurrence patterns: Check if window is reasonable
            window_minutes = pattern.get('window_minutes', 5)
            if 1 <= window_minutes <= 10:
                return 0.8  # Good window size
            elif window_minutes <= 30:
                return 0.6  # Acceptable window
            else:
                return 0.4  # Large window, less consistent
        
        # Default: medium score for unknown types
        return 0.5
    
    def _score_device_relationship(self, pattern: dict[str, Any]) -> float:
        """
        Score based on device relationship strength.
        
        Factors:
        - Same area: +0.5
        - Logical pairing (motion → light): +0.3
        - Device type compatibility: +0.2
        """
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
            # Motion sensor → Light (common automation)
            if 'motion' in device1.lower() and 'light' in device2.lower():
                score += 0.3
            # Door sensor → Lock
            elif 'door' in device1.lower() and 'lock' in device2.lower():
                score += 0.3
            # Temperature sensor → Climate
            elif 'temperature' in device1.lower() and 'climate' in device2.lower():
                score += 0.3
        
        # Device type compatibility (both same type or complementary)
        device_type1 = pattern.get('device_type1', '')
        device_type2 = pattern.get('device_type2', '')
        if device_type1 and device_type2:
            if device_type1 == device_type2:
                score += 0.1  # Same type
            elif (device_type1 == 'binary_sensor' and device_type2 == 'light'):
                score += 0.2  # Complementary
        
        return min(1.0, score)
    
    def _calculate_validation_boost(self, pattern: dict[str, Any]) -> float:
        """
        Calculate validation boost from external sources.
        
        Sources:
        - Blueprint match: +0.2
        - Ground truth match: +0.3
        - Pattern support: +0.1
        """
        boost = 0.0
        
        # Blueprint validation
        if self.blueprint_validator:
            try:
                # Check if pattern matches a blueprint
                # This is a simplified check - full implementation would use blueprint_validator
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
                    break  # Only count first match
        
        # Pattern support (if pattern is supported by other patterns)
        pattern_support = pattern.get('pattern_support_score', 0.0)
        if pattern_support > 0.7:
            boost += 0.1
        
        return min(0.3, boost)  # Cap at 0.3
    
    def _patterns_match(self, pattern1: dict[str, Any], pattern2: dict[str, Any]) -> bool:
        """
        Check if two patterns match (simplified).
        
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
        
        for field in ['device1', 'device2', 'entity_id']:
            if pattern1.get(field):
                devices1.add(pattern1[field])
            if pattern2.get(field):
                devices2.add(pattern2[field])
        
        # Match if devices overlap
        return len(devices1.intersection(devices2)) > 0
    
    def _calculate_home_type_relevance(self, pattern: dict[str, Any]) -> float:
        """
        Calculate how relevant pattern is to home type.
        
        Returns:
            Relevance score (0.0 to 1.0)
        """
        if not self.home_type:
            return 0.0
        
        # Check if pattern matches home type preferences
        pattern_type = pattern.get('pattern_type', '')
        device_domain = pattern.get('device_domain', pattern.get('domain', ''))
        device_class = pattern.get('device_class', '')
        
        # Security-focused homes prefer security patterns
        if self.home_type == 'security_focused':
            if pattern_type in ['motion', 'door', 'lock'] or device_domain == 'binary_sensor':
                if device_class in ['motion', 'door', 'window']:
                    return 0.8
            # Security devices get higher relevance
            if 'lock' in str(pattern.get('device1', '')) or 'lock' in str(pattern.get('device2', '')):
                return 0.7
            if 'alarm' in str(pattern.get('device1', '')) or 'alarm' in str(pattern.get('device2', '')):
                return 0.7
        
        # Climate-controlled homes prefer climate patterns
        elif self.home_type == 'climate_controlled':
            if pattern_type in ['temperature', 'humidity'] or device_domain == 'climate':
                return 0.8
            if device_class in ['temperature', 'humidity']:
                return 0.7
            # Climate devices get higher relevance
            if 'thermostat' in str(pattern.get('device1', '')) or 'thermostat' in str(pattern.get('device2', '')):
                return 0.7
        
        # High-activity homes prefer lighting/appliance patterns
        elif self.home_type == 'high_activity':
            if device_domain in ['light', 'switch', 'media_player']:
                return 0.6
            if pattern_type == 'time_of_day' and device_domain == 'light':
                return 0.7
        
        # Smart home prefers automation/integration patterns
        elif self.home_type == 'smart_home':
            if pattern_type in ['co_occurrence', 'session']:
                return 0.6
            # Multi-device patterns are more relevant
            if pattern.get('device1') and pattern.get('device2'):
                return 0.5
        
        # Default relevance for other home types
        return 0.3
    
    def assess_pattern_meaningfulness(self, pattern: dict[str, Any]) -> dict[str, Any]:
        """
        Assess if a pattern is meaningful (beyond just quality score).
        
        Returns:
            Dictionary with:
            - is_meaningful: bool
            - reasons: list of reasons why/why not
            - recommendations: list of recommendations
        """
        reasons = []
        recommendations = []
        
        quality = self.calculate_quality_score(pattern)
        quality_score = quality['quality_score']
        
        # Check quality threshold
        if quality_score < 0.5:
            reasons.append(f"Low quality score ({quality_score:.2f})")
            recommendations.append("Review pattern - may be false positive")
        
        # Check confidence
        confidence = pattern.get('confidence', 0.0)
        if confidence < 0.7:
            reasons.append(f"Low confidence ({confidence:.2f})")
            recommendations.append("Increase confidence threshold or gather more data")
        
        # Check frequency
        occurrences = pattern.get('occurrences', 0)
        if occurrences < 3:
            reasons.append(f"Low occurrence count ({occurrences})")
            recommendations.append("Need at least 3 occurrences for reliable pattern")
        
        # Check device relationship
        relationship_score = quality['breakdown']['relationship']
        if relationship_score < 0.3:
            reasons.append("Weak device relationship")
            recommendations.append("Verify devices are related (same area, logical pairing)")
        
        # Determine if meaningful
        is_meaningful = (
            quality_score >= 0.6 and
            confidence >= 0.7 and
            occurrences >= 3 and
            relationship_score >= 0.3
        )
        
        if is_meaningful:
            reasons.append("Pattern meets all quality criteria")
        
        return {
            'is_meaningful': is_meaningful,
            'reasons': reasons,
            'recommendations': recommendations,
            'quality_score': quality_score
        }


def calculate_pattern_quality_distribution(
    patterns: list[dict[str, Any]],
    scorer: PatternQualityScorer | None = None
) -> dict[str, Any]:
    """
    Calculate quality distribution statistics for a list of patterns.
    
    Args:
        patterns: List of pattern dictionaries
        scorer: Optional PatternQualityScorer (creates new one if not provided)
    
    Returns:
        Dictionary with quality statistics
    """
    if not scorer:
        scorer = PatternQualityScorer()
    
    quality_scores = []
    quality_tiers = {'high': 0, 'medium': 0, 'low': 0}
    
    for pattern in patterns:
        quality = scorer.calculate_quality_score(pattern)
        quality_scores.append(quality['quality_score'])
        quality_tiers[quality['quality_tier']] += 1
    
    if not quality_scores:
        return {
            'count': 0,
            'mean': 0.0,
            'median': 0.0,
            'min': 0.0,
            'max': 0.0,
            'tiers': quality_tiers,
            'high_quality_count': 0,
            'high_quality_percentage': 0.0
        }
    
    quality_scores.sort()
    n = len(quality_scores)
    
    return {
        'count': n,
        'mean': sum(quality_scores) / n,
        'median': quality_scores[n // 2] if n > 0 else 0.0,
        'min': quality_scores[0],
        'max': quality_scores[-1],
        'tiers': quality_tiers,
        'high_quality_count': sum(1 for s in quality_scores if s >= 0.6),
        'high_quality_percentage': (sum(1 for s in quality_scores if s >= 0.6) / n) * 100
    }

