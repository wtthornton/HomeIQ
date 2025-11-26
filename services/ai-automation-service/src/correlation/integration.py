"""
Correlation Integration Helpers

Epic 36, Story 36.7-36.8: Pattern & Synergy Detection Integration
Integrates correlation service with existing pattern and synergy detection.

Single-home NUC optimized:
- Lightweight integration (no heavy computation)
- Optional correlation enhancement (can be disabled)
- Caches correlation lookups
"""

import logging
from typing import Optional

from .correlation_service import CorrelationService

from shared.logging_config import get_logger

logger = get_logger(__name__)


class CorrelationPatternEnhancer:
    """
    Enhances pattern detection with correlation insights.
    
    Adds correlation scores to detected patterns to improve
    confidence and provide additional validation.
    """
    
    def __init__(self, correlation_service: CorrelationService):
        """
        Initialize pattern enhancer.
        
        Args:
            correlation_service: Correlation service instance
        """
        self.correlation_service = correlation_service
        logger.info("CorrelationPatternEnhancer initialized")
    
    def enhance_pattern(
        self,
        pattern: dict,
        entity_metadata: Optional[dict] = None
    ) -> dict:
        """
        Enhance a pattern with correlation insights.
        
        Args:
            pattern: Pattern dict with entity_id or entity_ids
            entity_metadata: Optional dict mapping entity_id -> metadata
        
        Returns:
            Enhanced pattern dict with correlation_score
        """
        if not pattern:
            return pattern
        
        # Extract entity IDs from pattern
        entity_ids = self._extract_entity_ids(pattern)
        
        if not entity_ids or len(entity_ids) < 2:
            # Single entity pattern, no correlation to compute
            pattern['correlation_score'] = None
            pattern['correlation_insights'] = []
            return pattern
        
        # Compute average correlation for all pairs
        correlations = []
        insights = []
        
        for i, entity1_id in enumerate(entity_ids):
            for entity2_id in entity_ids[i+1:]:
                entity1_meta = entity_metadata.get(entity1_id, {}) if entity_metadata else {}
                entity2_meta = entity_metadata.get(entity2_id, {}) if entity_metadata else {}
                
                corr = self.correlation_service.get_correlation(
                    entity1_id,
                    entity2_id,
                    entity1_meta,
                    entity2_meta
                )
                
                if corr is not None:
                    correlations.append(corr)
                    insights.append({
                        'entity1_id': entity1_id,
                        'entity2_id': entity2_id,
                        'correlation': corr
                    })
        
        # Average correlation score
        if correlations:
            avg_correlation = sum(correlations) / len(correlations)
            pattern['correlation_score'] = float(avg_correlation)
            pattern['correlation_insights'] = insights
            
            # Boost confidence if correlation is high
            if avg_correlation > 0.7 and 'confidence' in pattern:
                pattern['confidence'] = min(1.0, pattern['confidence'] * 1.1)
        else:
            pattern['correlation_score'] = None
            pattern['correlation_insights'] = []
        
        return pattern
    
    def _extract_entity_ids(self, pattern: dict) -> list[str]:
        """Extract entity IDs from pattern dict"""
        entity_ids = []
        
        # Try different pattern formats
        if 'entity_id' in pattern:
            entity_ids.append(pattern['entity_id'])
        
        if 'entity_ids' in pattern:
            entity_ids.extend(pattern['entity_ids'])
        
        if 'entities' in pattern:
            for entity in pattern['entities']:
                if isinstance(entity, dict):
                    entity_ids.append(entity.get('entity_id', ''))
                elif isinstance(entity, str):
                    entity_ids.append(entity)
        
        return [eid for eid in entity_ids if eid]


class CorrelationSynergyEnhancer:
    """
    Enhances synergy detection with correlation insights.
    
    Uses TabPFN to predict likely synergies and validates
    detected synergies with correlation scores.
    """
    
    def __init__(self, correlation_service: CorrelationService):
        """
        Initialize synergy enhancer.
        
        Args:
            correlation_service: Correlation service instance
        """
        self.correlation_service = correlation_service
        logger.info("CorrelationSynergyEnhancer initialized")
    
    def enhance_synergy(
        self,
        synergy: dict,
        entity_metadata: Optional[dict] = None
    ) -> dict:
        """
        Enhance a synergy with correlation insights.
        
        Args:
            synergy: Synergy dict with entity1_id and entity2_id
            entity_metadata: Optional dict mapping entity_id -> metadata
        
        Returns:
            Enhanced synergy dict with correlation_score
        """
        if not synergy:
            return synergy
        
        entity1_id = synergy.get('entity1_id') or synergy.get('trigger_entity_id')
        entity2_id = synergy.get('entity2_id') or synergy.get('action_entity_id')
        
        if not entity1_id or not entity2_id:
            synergy['correlation_score'] = None
            return synergy
        
        entity1_meta = entity_metadata.get(entity1_id, {}) if entity_metadata else {}
        entity2_meta = entity_metadata.get(entity2_id, {}) if entity_metadata else {}
        
        # Get correlation
        corr = self.correlation_service.get_correlation(
            entity1_id,
            entity2_id,
            entity1_meta,
            entity2_meta
        )
        
        if corr is not None:
            synergy['correlation_score'] = float(corr)
            
            # Boost impact score if correlation is high
            if corr > 0.7 and 'impact_score' in synergy:
                synergy['impact_score'] = min(1.0, synergy['impact_score'] * 1.1)
        else:
            synergy['correlation_score'] = None
        
        return synergy
    
    def predict_likely_synergies(
        self,
        entities: list[dict],
        usage_stats: Optional[dict] = None,
        threshold: float = 0.5
    ) -> list[dict]:
        """
        Predict likely synergies using TabPFN.
        
        Args:
            entities: List of entity metadata dicts
            usage_stats: Optional usage statistics
            threshold: Minimum prediction probability
        
        Returns:
            List of predicted synergy dicts
        """
        if not self.correlation_service.enable_tabpfn:
            return []
        
        # Predict likely correlated pairs
        likely_pairs = self.correlation_service.predict_likely_correlated_pairs(
            entities,
            usage_stats,
            threshold
        )
        
        # Convert to synergy format
        synergies = []
        for entity1, entity2, probability in likely_pairs:
            synergy = {
                'entity1_id': entity1.get('entity_id', ''),
                'entity2_id': entity2.get('entity_id', ''),
                'entity1_domain': entity1.get('domain', ''),
                'entity2_domain': entity2.get('domain', ''),
                'prediction_probability': float(probability),
                'correlation_score': None,  # Will be computed when enhanced
                'source': 'tabpfn_prediction'
            }
            synergies.append(synergy)
        
        logger.debug("Predicted %d likely synergies using TabPFN", len(synergies))
        
        return synergies

