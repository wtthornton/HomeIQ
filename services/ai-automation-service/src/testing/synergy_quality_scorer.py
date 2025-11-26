"""
Synergy Quality Scorer

Assesses the quality of detected synergies using multiple factors:
- Impact score
- Confidence
- Pattern support
- Device compatibility
- Automation feasibility
- User benefit
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class SynergyQualityScorer:
    """Calculate quality scores for detected synergies"""
    
    def __init__(self, pattern_validator=None, ground_truth_synergies=None):
        """
        Initialize synergy quality scorer.
        
        Args:
            pattern_validator: Optional PatternSynergyValidator for pattern support
            ground_truth_synergies: Optional list of ground truth synergies
        """
        self.pattern_validator = pattern_validator
        self.ground_truth_synergies = ground_truth_synergies or []
    
    def calculate_quality_score(self, synergy: dict[str, Any]) -> dict[str, Any]:
        """
        Calculate comprehensive quality score for a synergy.
        
        Quality Score Formula:
        - Base Quality (0.0-1.0):
          * Impact Score (35%)
          * Confidence (25%)
          * Pattern Support Score (25%)
          * Device Compatibility (15%)
        
        - Validation Boost (0.0-0.3):
          * Pattern validation: +0.2
          * Blueprint match: +0.15
          * Low complexity: +0.1
        
        Final Quality = min(1.0, base_quality + validation_boost)
        
        Args:
            synergy: Synergy dictionary with fields like:
                - impact_score: float (0.0-1.0)
                - confidence: float (0.0-1.0)
                - pattern_support_score: float (0.0-1.0)
                - validated_by_patterns: bool
                - complexity: str ('low' | 'medium' | 'high')
                - relationship_type: str
                - trigger_entity, action_entity: str
        
        Returns:
            Dictionary with:
            - quality_score: float (0.0-1.0)
            - base_quality: float
            - validation_boost: float
            - breakdown: dict with component scores
            - quality_tier: str ('high' | 'medium' | 'low')
        """
        # Calculate base quality components
        impact_score = self._score_impact(synergy)
        confidence_score = self._score_confidence(synergy)
        pattern_support_score = self._score_pattern_support(synergy)
        compatibility_score = self._score_device_compatibility(synergy)
        
        # Calculate base quality (weighted average)
        base_quality = (
            impact_score * 0.35 +
            confidence_score * 0.25 +
            pattern_support_score * 0.25 +
            compatibility_score * 0.15
        )
        
        # Calculate validation boost
        validation_boost = self._calculate_validation_boost(synergy)
        
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
            'breakdown': {
                'impact': impact_score,
                'confidence': confidence_score,
                'pattern_support': pattern_support_score,
                'compatibility': compatibility_score
            },
            'quality_tier': quality_tier,
            'is_high_quality': quality_score >= 0.6
        }
    
    def _score_impact(self, synergy: dict[str, Any]) -> float:
        """Score based on impact/benefit score (0.0-1.0)"""
        impact_score = synergy.get('impact_score', synergy.get('benefit_score', 0.5))
        # Clamp to [0.0, 1.0] range
        return max(0.0, min(1.0, float(impact_score)))
    
    def _score_confidence(self, synergy: dict[str, Any]) -> float:
        """Score based on synergy confidence (0.0-1.0)"""
        confidence = synergy.get('confidence', 0.7)
        # Clamp to [0.0, 1.0] range
        return max(0.0, min(1.0, float(confidence)))
    
    def _score_pattern_support(self, synergy: dict[str, Any]) -> float:
        """Score based on pattern support score (0.0-1.0)"""
        pattern_support = synergy.get('pattern_support_score', 0.0)
        # Clamp to [0.0, 1.0] range
        return max(0.0, min(1.0, float(pattern_support)))
    
    def _score_device_compatibility(self, synergy: dict[str, Any]) -> float:
        """
        Score based on device compatibility.
        
        Factors:
        - Same area: +0.5
        - Logical relationship (motion → light): +0.3
        - Device type compatibility: +0.2
        """
        score = 0.0
        
        # Check for same area
        area = synergy.get('area', '')
        if area and area != 'unknown':
            score += 0.5
        
        # Check for logical relationship
        relationship_type = synergy.get('relationship_type', '')
        if relationship_type:
            # Known good relationships
            good_relationships = [
                'motion_to_light',
                'door_to_lock',
                'temperature_to_climate',
                'presence_to_light',
                'time_to_light'
            ]
            if relationship_type in good_relationships:
                score += 0.3
        
        # Check device types
        trigger_entity = synergy.get('trigger_entity', synergy.get('opportunity_metadata', {}).get('trigger_entity_id', ''))
        action_entity = synergy.get('action_entity', synergy.get('opportunity_metadata', {}).get('action_entity_id', ''))
        
        if trigger_entity and action_entity:
            # Binary sensor → Light (common)
            if 'binary_sensor' in trigger_entity or 'sensor' in trigger_entity:
                if 'light' in action_entity:
                    score += 0.2
        
        return min(1.0, score)
    
    def _calculate_validation_boost(self, synergy: dict[str, Any]) -> float:
        """
        Calculate validation boost from external sources.
        
        Sources:
        - Pattern validation: +0.2
        - Blueprint match: +0.15
        - Low complexity: +0.1
        """
        boost = 0.0
        
        # Pattern validation
        validated_by_patterns = synergy.get('validated_by_patterns', False)
        if validated_by_patterns:
            boost += 0.2
        
        # Blueprint match (if available)
        blueprint_match = synergy.get('blueprint_match', False)
        if blueprint_match:
            boost += 0.15
        
        # Complexity bonus
        complexity = synergy.get('complexity', 'medium').lower()
        if complexity == 'low':
            boost += 0.1
        
        return min(0.3, boost)  # Cap at 0.3
    
    def assess_synergy_value(self, synergy: dict[str, Any]) -> dict[str, Any]:
        """
        Assess if a synergy provides real value (beyond just quality score).
        
        Returns:
            Dictionary with:
            - has_value: bool
            - reasons: list of reasons why/why not
            - recommendations: list of recommendations
        """
        reasons = []
        recommendations = []
        
        quality = self.calculate_quality_score(synergy)
        quality_score = quality['quality_score']
        
        # Check quality threshold
        if quality_score < 0.5:
            reasons.append(f"Low quality score ({quality_score:.2f})")
            recommendations.append("Review synergy - may not provide sufficient value")
        
        # Check impact score
        impact_score = synergy.get('impact_score', 0.0)
        if impact_score < 0.5:
            reasons.append(f"Low impact score ({impact_score:.2f})")
            recommendations.append("Synergy may not provide significant benefit")
        
        # Check pattern support
        pattern_support = synergy.get('pattern_support_score', 0.0)
        if pattern_support < 0.5:
            reasons.append(f"Low pattern support ({pattern_support:.2f})")
            recommendations.append("Gather more pattern evidence before deploying")
        
        # Check complexity
        complexity = synergy.get('complexity', 'medium')
        if complexity == 'high':
            reasons.append("High complexity")
            recommendations.append("Consider if complexity is worth the benefit")
        
        # Check automation feasibility
        validated = synergy.get('validated_by_patterns', False)
        if not validated:
            reasons.append("Not validated by patterns")
            recommendations.append("Validate with pattern evidence before deploying")
        
        # Determine if has value
        has_value = (
            quality_score >= 0.6 and
            impact_score >= 0.5 and
            pattern_support >= 0.5 and
            complexity != 'high'
        )
        
        if has_value:
            reasons.append("Synergy meets all value criteria")
        
        return {
            'has_value': has_value,
            'reasons': reasons,
            'recommendations': recommendations,
            'quality_score': quality_score
        }


def calculate_synergy_quality_distribution(
    synergies: list[dict[str, Any]],
    scorer: SynergyQualityScorer | None = None
) -> dict[str, Any]:
    """
    Calculate quality distribution statistics for a list of synergies.
    
    Args:
        synergies: List of synergy dictionaries
        scorer: Optional SynergyQualityScorer (creates new one if not provided)
    
    Returns:
        Dictionary with quality statistics
    """
    if not scorer:
        scorer = SynergyQualityScorer()
    
    quality_scores = []
    quality_tiers = {'high': 0, 'medium': 0, 'low': 0}
    
    for synergy in synergies:
        quality = scorer.calculate_quality_score(synergy)
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

