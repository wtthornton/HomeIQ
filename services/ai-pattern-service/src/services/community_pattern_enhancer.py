"""
Community Pattern Enhancer Service

Uses community patterns to improve pattern detection by learning from patterns
that work well for other users. Boosts confidence for patterns similar to community favorites.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md - Recommendation 5.2
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# Constants for boost calculation
BASE_BOOST = 0.05
MAX_BOOST = 0.15

# Confidence thresholds
HIGH_CONFIDENCE_THRESHOLD = 0.8
MEDIUM_CONFIDENCE_THRESHOLD = 0.6

# Occurrence thresholds
HIGH_OCCURRENCE_THRESHOLD = 100
MEDIUM_OCCURRENCE_THRESHOLD = 50
LOW_OCCURRENCE_THRESHOLD = 10


@dataclass
class BoostFactors:
    """Factors used to calculate confidence boost."""
    
    base: float = BASE_BOOST
    quality: float = 0.0
    popularity: float = 0.0
    
    @property
    def total(self) -> float:
        """Calculate total boost, capped at MAX_BOOST."""
        return min(MAX_BOOST, self.base + self.quality + self.popularity)


class CommunityPatternEnhancer:
    """
    Use community patterns to improve detection.
    
    Features:
        - Learn from patterns that work well for other users
        - Boost confidence for patterns similar to community favorites
        - Suggest community-validated patterns
    
    Example:
        >>> enhancer = CommunityPatternEnhancer(community_patterns=[...])
        >>> enhanced_confidence = enhancer.enhance_pattern_confidence(pattern)
    """
    
    def __init__(self, community_patterns: list[dict[str, Any]] | None = None):
        """
        Initialize community pattern enhancer.
        
        Args:
            community_patterns: Optional list of community patterns to use for enhancement
        """
        self.community_patterns = community_patterns or []
        logger.info(
            f"CommunityPatternEnhancer initialized with "
            f"{len(self.community_patterns)} community patterns"
        )
    
    def enhance_pattern_confidence(
        self,
        pattern: dict[str, Any],
        community_patterns: list[dict[str, Any]] | None = None
    ) -> float:
        """
        Boost pattern confidence if similar to community favorites.
        
        Recommendation 5.2: Community Pattern Learning
        - Learn from patterns that work well for other users
        - Boost confidence for patterns similar to community favorites
        
        Args:
            pattern: Pattern dictionary to enhance
            community_patterns: Optional list of community patterns (uses instance patterns if None)
            
        Returns:
            Enhanced confidence score (0.0-1.0)
        """
        patterns_to_use = community_patterns if community_patterns is not None else self.community_patterns
        original_confidence = pattern.get('confidence', 0.0)
        
        if not patterns_to_use:
            return original_confidence
        
        similar_patterns = self._find_similar_community_patterns(pattern, patterns_to_use)
        
        if not similar_patterns:
            return original_confidence
        
        boost = self._calculate_community_boost(similar_patterns)
        enhanced_confidence = min(1.0, original_confidence + boost)
        
        self._log_enhancement(pattern, original_confidence, enhanced_confidence, boost, len(similar_patterns))
        
        return enhanced_confidence
    
    def _find_similar_community_patterns(
        self,
        pattern: dict[str, Any],
        community_patterns: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Find community patterns similar to the given pattern.
        
        Args:
            pattern: Pattern to find similar patterns for
            community_patterns: List of community patterns to search
            
        Returns:
            List of similar community patterns
        """
        pattern_type = pattern.get('pattern_type', 'unknown')
        device_id = pattern.get('device_id', '')
        
        return [
            cp for cp in community_patterns
            if self._is_similar_pattern(pattern_type, device_id, cp)
        ]
    
    def _is_similar_pattern(
        self,
        pattern_type: str,
        device_id: str,
        community_pattern: dict[str, Any]
    ) -> bool:
        """
        Check if a community pattern is similar to the given pattern.
        
        Args:
            pattern_type: Type of the pattern
            device_id: Device ID of the pattern
            community_pattern: Community pattern to compare
            
        Returns:
            True if patterns are similar
        """
        if community_pattern.get('pattern_type') != pattern_type:
            return False
        
        community_device_id = community_pattern.get('device_id', '')
        
        if pattern_type == 'co_occurrence':
            return self._check_co_occurrence_similarity(device_id, community_device_id)
        
        return self._check_device_similarity(device_id, community_device_id)
    
    def _check_co_occurrence_similarity(self, device_id: str, community_device_id: str) -> bool:
        """Check similarity for co-occurrence patterns."""
        if '+' in device_id and '+' in community_device_id:
            pattern_devices = set(device_id.split('+'))
            community_devices = set(community_device_id.split('+'))
            return bool(pattern_devices & community_devices)
        
        return device_id == community_device_id
    
    def _check_device_similarity(self, device_id: str, community_device_id: str) -> bool:
        """Check similarity for non-co-occurrence patterns."""
        if device_id == community_device_id:
            return True
        
        if not device_id or not community_device_id:
            return False
        
        # Check domain match (e.g., "light.bedroom" vs "light.kitchen")
        pattern_domain = device_id.split('.')[0] if '.' in device_id else device_id
        community_domain = community_device_id.split('.')[0] if '.' in community_device_id else community_device_id
        
        return pattern_domain == community_domain
    
    def _calculate_community_boost(self, similar_patterns: list[dict[str, Any]]) -> float:
        """
        Calculate confidence boost based on community pattern popularity and success.
        
        Args:
            similar_patterns: List of similar community patterns
            
        Returns:
            Confidence boost value (0.0-0.15)
        """
        if not similar_patterns:
            return 0.0
        
        avg_confidence, avg_occurrences = self._calculate_averages(similar_patterns)
        
        boost = BoostFactors(
            base=BASE_BOOST,
            quality=self._get_quality_boost(avg_confidence),
            popularity=self._get_popularity_boost(avg_occurrences)
        )
        
        return boost.total
    
    def _calculate_averages(
        self,
        patterns: list[dict[str, Any]]
    ) -> tuple[float, float]:
        """Calculate average confidence and occurrences."""
        count = len(patterns)
        if count == 0:
            return 0.0, 0.0
        
        total_confidence = sum(p.get('confidence', 0.0) for p in patterns)
        total_occurrences = sum(p.get('occurrences', 0) for p in patterns)
        
        return total_confidence / count, total_occurrences / count
    
    def _get_quality_boost(self, avg_confidence: float) -> float:
        """Get quality boost based on average confidence."""
        if avg_confidence > HIGH_CONFIDENCE_THRESHOLD:
            return 0.10
        if avg_confidence > MEDIUM_CONFIDENCE_THRESHOLD:
            return 0.05
        return 0.02
    
    def _get_popularity_boost(self, avg_occurrences: float) -> float:
        """Get popularity boost based on average occurrences."""
        if avg_occurrences > HIGH_OCCURRENCE_THRESHOLD:
            return 0.05
        if avg_occurrences > MEDIUM_OCCURRENCE_THRESHOLD:
            return 0.03
        if avg_occurrences > LOW_OCCURRENCE_THRESHOLD:
            return 0.01
        return 0.0
    
    def _log_enhancement(
        self,
        pattern: dict[str, Any],
        original: float,
        enhanced: float,
        boost: float,
        similar_count: int
    ) -> None:
        """Log pattern enhancement details."""
        pattern_type = pattern.get('pattern_type', 'unknown')
        device_id = pattern.get('device_id', '')
        
        logger.debug(
            f"Enhanced pattern confidence: {pattern_type}:{device_id} "
            f"{original:.2f} → {enhanced:.2f} "
            f"(boost: +{boost:.2f} from {similar_count} community patterns)"
        )
    
    def enhance_patterns_batch(
        self,
        patterns: list[dict[str, Any]],
        community_patterns: list[dict[str, Any]] | None = None
    ) -> list[dict[str, Any]]:
        """
        Enhance confidence for a batch of patterns using community patterns.
        
        Args:
            patterns: List of patterns to enhance
            community_patterns: Optional list of community patterns
            
        Returns:
            List of enhanced patterns with updated confidence scores
        """
        enhanced_patterns = []
        
        for pattern in patterns:
            enhanced_pattern = pattern.copy()
            enhanced_pattern['confidence'] = self.enhance_pattern_confidence(
                pattern,
                community_patterns=community_patterns
            )
            enhanced_pattern['community_enhanced'] = True
            enhanced_patterns.append(enhanced_pattern)
        
        logger.info(f"✅ Enhanced {len(enhanced_patterns)} patterns using community patterns")
        
        return enhanced_patterns
