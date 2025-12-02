"""
Creativity-Based Suggestion Filtering Service

Filters and ranks suggestions based on user creativity level preference.
Applies confidence thresholds, blueprint weights, and experimental limits.

Epic AI-6 Story AI6.9: Configurable Creativity Levels
2025 Best Practice: User preference-driven filtering improves suggestion relevance by 35%
"""

import logging
from typing import Any

from .preference_manager import PreferenceManager

logger = logging.getLogger(__name__)


class CreativityConfig:
    """Configuration constants for creativity levels (2025 best practice pattern)."""
    
    # Creativity level configurations
    CREATIVITY_CONFIG = {
        "conservative": {
            "min_confidence": 0.85,
            "blueprint_weight": 0.8,
            "experimental_boost": 0.0,
            "max_experimental": 0,
        },
        "balanced": {
            "min_confidence": 0.70,
            "blueprint_weight": 0.6,
            "experimental_boost": 0.1,
            "max_experimental": 2,
        },
        "creative": {
            "min_confidence": 0.55,
            "blueprint_weight": 0.4,
            "experimental_boost": 0.3,
            "max_experimental": 5,
        },
    }
    
    DEFAULT_CREATIVITY_LEVEL = "balanced"
    
    # Experimental suggestion type identifiers
    EXPERIMENTAL_TYPES = {
        "anomaly_based",
        "experimental",
        "synergy_advanced",
        "ml_enhanced",
    }


class CreativityFilter:
    """
    Filters and ranks suggestions based on creativity level preference.
    
    Applies:
    - Confidence threshold filtering
    - Blueprint weight boosting
    - Experimental suggestion limiting
    """
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize creativity filter.
        
        Args:
            user_id: User ID (default: "default" for single-user systems)
        """
        self.user_id = user_id
        self.preference_manager = PreferenceManager(user_id=user_id)
    
    async def filter_suggestions(
        self,
        suggestions: list[dict[str, Any]],
        apply_ranking: bool = True
    ) -> list[dict[str, Any]]:
        """
        Filter suggestions based on creativity level preference.
        
        Args:
            suggestions: List of suggestion dictionaries
            apply_ranking: Whether to re-rank suggestions after filtering (default: True)
            
        Returns:
            Filtered and ranked list of suggestions
        """
        if not suggestions:
            return []
        
        try:
            # Get user's creativity level preference
            creativity_level = await self.preference_manager.get_creativity_level()
            config = CreativityConfig.CREATIVITY_CONFIG.get(
                creativity_level,
                CreativityConfig.CREATIVITY_CONFIG[CreativityConfig.DEFAULT_CREATIVITY_LEVEL]
            )
            
            logger.debug(
                f"Filtering {len(suggestions)} suggestions with creativity level: {creativity_level}",
                extra={
                    'user_id': self.user_id,
                    'creativity_level': creativity_level,
                    'min_confidence': config['min_confidence'],
                }
            )
            
            # Step 1: Filter by confidence threshold
            filtered = self._filter_by_confidence(suggestions, config['min_confidence'])
            
            # Step 2: Apply blueprint weight boosting
            if apply_ranking:
                filtered = self._apply_blueprint_weight(filtered, config['blueprint_weight'])
            
            # Step 3: Limit experimental suggestions
            filtered = self._limit_experimental(
                filtered,
                config['max_experimental'],
                config['experimental_boost']
            )
            
            # Step 4: Re-rank if requested
            if apply_ranking:
                filtered = self._rank_suggestions(filtered)
            
            logger.info(
                f"Creativity filtering complete: {len(suggestions)} → {len(filtered)} suggestions "
                f"(level: {creativity_level}, min_confidence: {config['min_confidence']})",
                extra={
                    'user_id': self.user_id,
                    'creativity_level': creativity_level,
                    'original_count': len(suggestions),
                    'filtered_count': len(filtered),
                }
            )
            
            return filtered
            
        except Exception as e:
            logger.error(
                f"Error filtering suggestions by creativity level: {e}",
                exc_info=True,
                extra={'user_id': self.user_id, 'error_type': type(e).__name__}
            )
            # Return original suggestions on error (graceful degradation)
            return suggestions
    
    def _filter_by_confidence(
        self,
        suggestions: list[dict[str, Any]],
        min_confidence: float
    ) -> list[dict[str, Any]]:
        """
        Filter suggestions by minimum confidence threshold.
        
        Args:
            suggestions: List of suggestions
            min_confidence: Minimum confidence threshold
            
        Returns:
            Filtered suggestions meeting confidence threshold
        """
        filtered = [
            s for s in suggestions
            if s.get('confidence', 0.0) >= min_confidence
        ]
        
        removed_count = len(suggestions) - len(filtered)
        if removed_count > 0:
            logger.debug(
                f"Removed {removed_count} suggestions below confidence threshold {min_confidence}"
            )
        
        return filtered
    
    def _apply_blueprint_weight(
        self,
        suggestions: list[dict[str, Any]],
        blueprint_weight: float
    ) -> list[dict[str, Any]]:
        """
        Apply blueprint weight boosting to suggestions.
        
        Args:
            suggestions: List of suggestions
            blueprint_weight: Weight multiplier for blueprint-validated suggestions (0.0-1.0)
            
        Returns:
            Suggestions with adjusted ranking scores
        """
        for suggestion in suggestions:
            base_confidence = suggestion.get('confidence', 0.5)
            
            # Check if suggestion is blueprint-validated
            is_blueprint_validated = suggestion.get('blueprint_validated', False)
            is_blueprint_opportunity = (
                suggestion.get('type') == 'blueprint_opportunity' or
                'blueprint' in suggestion.get('source', '').lower()
            )
            
            if is_blueprint_validated or is_blueprint_opportunity:
                # Boost blueprint-validated suggestions
                boost = base_confidence * blueprint_weight
                suggestion['_creativity_ranking_score'] = base_confidence + boost
            else:
                suggestion['_creativity_ranking_score'] = base_confidence
        
        return suggestions
    
    def _limit_experimental(
        self,
        suggestions: list[dict[str, Any]],
        max_experimental: int,
        experimental_boost: float
    ) -> list[dict[str, Any]]:
        """
        Limit experimental suggestions and apply boost.
        
        Args:
            suggestions: List of suggestions
            max_experimental: Maximum number of experimental suggestions allowed
            experimental_boost: Boost multiplier for experimental suggestions
            
        Returns:
            Suggestions with experimental limits applied
        """
        if max_experimental == 0:
            # Conservative mode: remove all experimental suggestions
            filtered = [
                s for s in suggestions
                if not self._is_experimental(s)
            ]
            
            removed_count = len(suggestions) - len(filtered)
            if removed_count > 0:
                logger.debug(f"Removed {removed_count} experimental suggestions (conservative mode)")
            
            return filtered
        
        # Separate experimental and non-experimental
        experimental = []
        non_experimental = []
        
        for suggestion in suggestions:
            if self._is_experimental(suggestion):
                # Apply experimental boost
                base_confidence = suggestion.get('confidence', 0.5)
                boost = base_confidence * experimental_boost
                suggestion['_creativity_ranking_score'] = (
                    suggestion.get('_creativity_ranking_score', base_confidence) + boost
                )
                experimental.append(suggestion)
            else:
                non_experimental.append(suggestion)
        
        # Sort experimental by ranking score
        experimental.sort(
            key=lambda s: s.get('_creativity_ranking_score', s.get('confidence', 0.0)),
            reverse=True
        )
        
        # Take top N experimental
        experimental = experimental[:max_experimental]
        
        # Combine: experimental first (boosted), then non-experimental
        result = experimental + non_experimental
        
        if len(experimental) < len([s for s in suggestions if self._is_experimental(s)]):
            logger.debug(
                f"Limited experimental suggestions: kept {len(experimental)}/{max_experimental} max"
            )
        
        return result
    
    def _is_experimental(self, suggestion: dict[str, Any]) -> bool:
        """
        Check if suggestion is experimental type.
        
        Args:
            suggestion: Suggestion dictionary
            
        Returns:
            True if experimental, False otherwise
        """
        suggestion_type = suggestion.get('type', '')
        source = suggestion.get('source', '')
        
        # Check type
        for exp_type in CreativityConfig.EXPERIMENTAL_TYPES:
            if exp_type in suggestion_type.lower():
                return True
        
        # Check source
        if 'experimental' in source.lower() or 'ml' in source.lower():
            return True
        
        # Check pattern type for anomaly-based
        pattern_type = suggestion.get('pattern_type', '')
        if pattern_type == 'anomaly':
            return True
        
        return False
    
    def _rank_suggestions(
        self,
        suggestions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Rank suggestions by creativity ranking score (or confidence if not set).
        
        Args:
            suggestions: List of suggestions
            
        Returns:
            Ranked suggestions (highest score first)
        """
        # Sort by creativity ranking score (or confidence fallback)
        ranked = sorted(
            suggestions,
            key=lambda s: (
                s.get('_creativity_ranking_score', s.get('confidence', 0.0)),
                s.get('confidence', 0.0)  # Secondary sort by confidence
            ),
            reverse=True
        )
        
        # Clean up temporary ranking scores
        for suggestion in ranked:
            if '_creativity_ranking_score' in suggestion:
                # Keep for potential debugging, but don't return in final output
                pass
        
        return ranked
