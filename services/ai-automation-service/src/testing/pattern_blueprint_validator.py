"""
Pattern-Blueprint Validation

Enhances pattern detection with blueprint validation to boost confidence
and add blueprint references to patterns.

Phase 2: Enhanced Pattern Detection
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class PatternBlueprintValidator:
    """
    Validate detected patterns against blueprints.
    
    Patterns that match blueprints get:
    - Confidence boost (+0.1)
    - Blueprint reference added
    - Validation flag set
    """
    
    def __init__(self, correlator=None):
        """
        Initialize pattern-blueprint validator.
        
        Args:
            correlator: BlueprintDatasetCorrelator instance (optional)
        """
        self.correlator = correlator
        logger.info("PatternBlueprintValidator initialized")
    
    def set_correlator(self, correlator):
        """Set the correlator instance"""
        self.correlator = correlator
    
    async def validate_patterns_with_blueprints(
        self,
        patterns: list[dict[str, Any]],
        miner=None
    ) -> list[dict[str, Any]]:
        """
        Validate patterns against blueprints and boost confidence.
        
        Args:
            patterns: List of detected patterns
            miner: MinerIntegration instance (optional)
        
        Returns:
            List of patterns with blueprint validation added
        """
        if not self.correlator:
            logger.warning("No correlator available, skipping blueprint validation")
            return patterns
        
        validated_patterns = []
        
        for pattern in patterns:
            validated_pattern = pattern.copy()
            
            try:
                # Find matching blueprint
                blueprint_match = await self.correlator.find_blueprint_for_pattern(
                    pattern, miner
                )
                
                if blueprint_match and blueprint_match.get('fit_score', 0) > 0.5:
                    # Boost confidence
                    original_confidence = validated_pattern.get('confidence', 0.0)
                    validated_pattern['confidence'] = min(1.0, original_confidence + 0.1)
                    
                    # Add blueprint reference
                    validated_pattern['blueprint_validated'] = True
                    validated_pattern['blueprint_reference'] = blueprint_match['blueprint'].get('id')
                    validated_pattern['blueprint_name'] = blueprint_match['blueprint'].get('title', 'Unknown')
                    validated_pattern['blueprint_fit_score'] = blueprint_match['fit_score']
                    
                    logger.debug(
                        f"Pattern validated by blueprint: {validated_pattern.get('blueprint_name')} "
                        f"(confidence: {original_confidence:.3f} → {validated_pattern['confidence']:.3f})"
                    )
                else:
                    validated_pattern['blueprint_validated'] = False
                    
            except Exception as e:
                logger.warning(f"Error validating pattern with blueprint: {e}")
                validated_pattern['blueprint_validated'] = False
            
            validated_patterns.append(validated_pattern)
        
        validated_count = sum(1 for p in validated_patterns if p.get('blueprint_validated', False))
        logger.info(f"Validated {validated_count}/{len(patterns)} patterns with blueprints")
        
        return validated_patterns

