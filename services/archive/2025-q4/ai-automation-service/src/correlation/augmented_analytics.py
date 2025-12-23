"""
Augmented Correlation Analytics

Epic 38, Story 38.5: Augmented Analytics Foundation
Provides automated pattern detection and correlation explanations for correlation analysis.

Single-home NUC optimized:
- Memory: <20MB (lightweight analysis engine)
- Performance: <100ms per analysis
- Automated insights without heavy ML models
"""

import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np

from .correlation_service import CorrelationService
from .feature_extractor import CorrelationFeatureExtractor

from shared.logging_config import get_logger

logger = get_logger(__name__)


class AugmentedCorrelationAnalytics:
    """
    Provides augmented analytics for correlation analysis.
    
    Features:
    - Automated pattern detection
    - Correlation explanation generation
    - Insight extraction from correlation data
    - Natural language explanations
    
    Single-home optimization:
    - Lightweight analysis (no heavy ML models)
    - Rule-based pattern detection
    - Efficient explanation generation
    """
    
    def __init__(
        self,
        correlation_service: CorrelationService,
        feature_extractor: Optional[CorrelationFeatureExtractor] = None
    ):
        """
        Initialize augmented analytics.
        
        Args:
            correlation_service: Correlation service instance
            feature_extractor: Optional feature extractor for enhanced analysis
        """
        self.correlation_service = correlation_service
        self.feature_extractor = feature_extractor or correlation_service.feature_extractor
        
        logger.info("AugmentedCorrelationAnalytics initialized")
    
    def detect_patterns(
        self,
        entity1_id: str,
        entity2_id: str,
        entity1_metadata: Optional[Dict] = None,
        entity2_metadata: Optional[Dict] = None,
        correlation_score: Optional[float] = None
    ) -> Dict:
        """
        Detect patterns in correlation between two entities.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            entity1_metadata: Optional entity 1 metadata
            entity2_metadata: Optional entity 2 metadata
            correlation_score: Optional correlation score (if already computed)
        
        Returns:
            Dict with detected patterns:
            {
                'pattern_type': str,  # 'complementary', 'sequential', 'temporal', etc.
                'strength': float,  # 0.0-1.0
                'confidence': float,  # 0.0-1.0
                'indicators': List[str],  # Pattern indicators
                'description': str  # Human-readable description
            }
        """
        try:
            # Get correlation if not provided
            if correlation_score is None:
                correlation_score = self.correlation_service.get_correlation(
                    entity1_id, entity2_id, entity1_metadata, entity2_metadata
                ) or 0.0
            
            # Extract features for pattern detection
            if entity1_metadata and entity2_metadata:
                features = self.feature_extractor.extract_pair_features(
                    entity1_metadata, entity2_metadata
                )
            else:
                features = {}
            
            # Detect pattern type
            pattern_type, strength, indicators = self._detect_pattern_type(
                entity1_id, entity2_id, correlation_score, features
            )
            
            # Calculate confidence
            confidence = self._calculate_pattern_confidence(
                correlation_score, strength, indicators
            )
            
            # Generate description
            description = self._generate_pattern_description(
                pattern_type, entity1_id, entity2_id, strength, indicators
            )
            
            return {
                'pattern_type': pattern_type,
                'strength': strength,
                'confidence': confidence,
                'indicators': indicators,
                'description': description,
                'correlation_score': correlation_score
            }
        
        except Exception as e:
            logger.error("Failed to detect patterns: %s", e)
            return {
                'pattern_type': 'unknown',
                'strength': 0.0,
                'confidence': 0.0,
                'indicators': [],
                'description': 'Pattern detection failed',
                'error': str(e)
            }
    
    def explain_correlation(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation_score: float,
        entity1_metadata: Optional[Dict] = None,
        entity2_metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Generate natural language explanation for correlation.
        
        Args:
            entity1_id: Entity 1 ID
            entity2_id: Entity 2 ID
            correlation_score: Correlation score (-1.0 to 1.0)
            entity1_metadata: Optional entity 1 metadata
            entity2_metadata: Optional entity 2 metadata
        
        Returns:
            Dict with explanation:
            {
                'summary': str,  # Brief summary
                'explanation': str,  # Detailed explanation
                'factors': List[str],  # Contributing factors
                'strength': str,  # 'strong', 'moderate', 'weak'
                'direction': str,  # 'positive', 'negative', 'neutral'
            }
        """
        try:
            # Extract features for explanation
            if entity1_metadata and entity2_metadata:
                features = self.feature_extractor.extract_pair_features(
                    entity1_metadata, entity2_metadata
                )
            else:
                features = {}
            
            # Determine correlation strength and direction
            strength = self._classify_correlation_strength(correlation_score)
            direction = self._classify_correlation_direction(correlation_score)
            
            # Identify contributing factors
            factors = self._identify_contributing_factors(
                entity1_id, entity2_id, correlation_score, features
            )
            
            # Generate summary
            summary = self._generate_correlation_summary(
                entity1_id, entity2_id, strength, direction, correlation_score
            )
            
            # Generate detailed explanation
            explanation = self._generate_detailed_explanation(
                entity1_id, entity2_id, correlation_score, strength, direction, factors, features
            )
            
            return {
                'summary': summary,
                'explanation': explanation,
                'factors': factors,
                'strength': strength,
                'direction': direction,
                'correlation_score': correlation_score
            }
        
        except Exception as e:
            logger.error("Failed to explain correlation: %s", e)
            return {
                'summary': f'Correlation between {entity1_id} and {entity2_id}',
                'explanation': 'Explanation generation failed',
                'factors': [],
                'strength': 'unknown',
                'direction': 'unknown',
                'error': str(e)
            }
    
    def _detect_pattern_type(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation_score: float,
        features: Dict
    ) -> Tuple[str, float, List[str]]:
        """
        Detect pattern type from correlation and features.
        
        Returns:
            Tuple of (pattern_type, strength, indicators)
        """
        indicators = []
        strength = abs(correlation_score)
        
        # Check for complementary pattern (motion sensor -> light)
        if features.get('domain_complementary', False):
            return ('complementary', strength, ['complementary_domains'])
        
        # Check for same area pattern
        if features.get('same_area', False):
            indicators.append('same_area')
            if strength > 0.5:
                return ('spatial', strength, indicators)
        
        # Check for temporal pattern (time overlap)
        time_overlap = features.get('time_overlap', 0.0)
        if time_overlap > 0.7:
            indicators.append('high_time_overlap')
            return ('temporal', strength, indicators)
        
        # Check for sequential pattern (one triggers the other)
        # This would require usage history analysis
        if strength > 0.6:
            indicators.append('high_correlation')
            return ('sequential', strength, indicators)
        
        # Default: general correlation
        if strength > 0.3:
            return ('general', strength, ['moderate_correlation'])
        
        return ('none', 0.0, [])
    
    def _calculate_pattern_confidence(
        self,
        correlation_score: float,
        strength: float,
        indicators: List[str]
    ) -> float:
        """Calculate confidence in pattern detection"""
        # Base confidence on correlation strength
        base_confidence = strength
        
        # Boost confidence with more indicators
        indicator_boost = min(0.2, len(indicators) * 0.05)
        
        # Boost confidence for strong correlations
        if abs(correlation_score) > 0.7:
            correlation_boost = 0.1
        elif abs(correlation_score) > 0.5:
            correlation_boost = 0.05
        else:
            correlation_boost = 0.0
        
        confidence = min(1.0, base_confidence + indicator_boost + correlation_boost)
        return confidence
    
    def _generate_pattern_description(
        self,
        pattern_type: str,
        entity1_id: str,
        entity2_id: str,
        strength: float,
        indicators: List[str]
    ) -> str:
        """Generate human-readable pattern description"""
        strength_desc = 'strong' if strength > 0.7 else 'moderate' if strength > 0.4 else 'weak'
        
        descriptions = {
            'complementary': f"{entity1_id} and {entity2_id} are complementary devices that work together ({strength_desc} correlation)",
            'spatial': f"{entity1_id} and {entity2_id} are in the same area and show {strength_desc} correlation",
            'temporal': f"{entity1_id} and {entity2_id} are used at similar times ({strength_desc} correlation)",
            'sequential': f"{entity1_id} and {entity2_id} show sequential usage patterns ({strength_desc} correlation)",
            'general': f"{entity1_id} and {entity2_id} show {strength_desc} correlation",
            'none': f"{entity1_id} and {entity2_id} show minimal correlation"
        }
        
        return descriptions.get(pattern_type, f"{entity1_id} and {entity2_id} correlation pattern")
    
    def _classify_correlation_strength(self, correlation_score: float) -> str:
        """Classify correlation strength"""
        abs_score = abs(correlation_score)
        if abs_score >= 0.7:
            return 'strong'
        elif abs_score >= 0.4:
            return 'moderate'
        elif abs_score >= 0.2:
            return 'weak'
        else:
            return 'negligible'
    
    def _classify_correlation_direction(self, correlation_score: float) -> str:
        """Classify correlation direction"""
        if correlation_score > 0.2:
            return 'positive'
        elif correlation_score < -0.2:
            return 'negative'
        else:
            return 'neutral'
    
    def _identify_contributing_factors(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation_score: float,
        features: Dict
    ) -> List[str]:
        """Identify factors contributing to correlation"""
        factors = []
        
        # Spatial factors
        if features.get('same_area', False):
            factors.append('Same area/room')
        
        if features.get('same_device', False):
            factors.append('Same device')
        
        # Temporal factors
        time_overlap = features.get('time_overlap', 0.0)
        if time_overlap > 0.5:
            factors.append(f'High time overlap ({time_overlap:.0%})')
        
        # Usage factors
        usage_freq_1 = features.get('usage_frequency_1', 0.0)
        usage_freq_2 = features.get('usage_frequency_2', 0.0)
        if usage_freq_1 > 0.7 or usage_freq_2 > 0.7:
            factors.append('High usage frequency')
        
        # Domain factors
        if features.get('domain_complementary', False):
            factors.append('Complementary device types')
        
        # Correlation strength
        if abs(correlation_score) > 0.7:
            factors.append('Strong correlation score')
        elif abs(correlation_score) > 0.5:
            factors.append('Moderate correlation score')
        
        return factors
    
    def _generate_correlation_summary(
        self,
        entity1_id: str,
        entity2_id: str,
        strength: str,
        direction: str,
        correlation_score: float
    ) -> str:
        """Generate brief correlation summary"""
        direction_desc = {
            'positive': 'positively correlated',
            'negative': 'negatively correlated',
            'neutral': 'weakly correlated'
        }.get(direction, 'correlated')
        
        return f"{entity1_id} and {entity2_id} are {strength}ly {direction_desc} (score: {correlation_score:.2f})"
    
    def _generate_detailed_explanation(
        self,
        entity1_id: str,
        entity2_id: str,
        correlation_score: float,
        strength: str,
        direction: str,
        factors: List[str],
        features: Dict
    ) -> str:
        """Generate detailed correlation explanation"""
        explanation_parts = []
        
        # Introduction
        explanation_parts.append(
            f"The correlation between {entity1_id} and {entity2_id} is {strength} ({correlation_score:.2f})."
        )
        
        # Direction explanation
        if direction == 'positive':
            explanation_parts.append(
                "When one device is active, the other is likely to be active as well."
            )
        elif direction == 'negative':
            explanation_parts.append(
                "When one device is active, the other is likely to be inactive."
            )
        else:
            explanation_parts.append(
                "The devices show minimal correlation in their usage patterns."
            )
        
        # Contributing factors
        if factors:
            explanation_parts.append(
                f"Contributing factors: {', '.join(factors)}."
            )
        
        # Feature-based insights
        if features.get('same_area', False):
            explanation_parts.append(
                "Both devices are in the same area, which may contribute to their correlation."
            )
        
        if features.get('time_overlap', 0.0) > 0.5:
            explanation_parts.append(
                f"The devices are used at overlapping times ({features['time_overlap']:.0%} overlap)."
            )
        
        return " ".join(explanation_parts)

