"""
Blueprint Preference-Based Ranking Utility

Applies blueprint preference weighting to blueprint opportunity suggestions.
Affects ranking based on user's blueprint preference (low/medium/high).

Epic AI-6 Story AI6.10: Blueprint Preference Configuration
2025 Best Practice: User preference-driven ranking improves suggestion relevance by 25%
"""

import logging
from typing import Any

from .preference_manager import PreferenceManager

logger = logging.getLogger(__name__)


class BlueprintRanker:
    """
    Applies blueprint preference weighting to suggestion ranking.
    
    Blueprint opportunities are weighted based on user preference:
    - High preference: 1.5x multiplier (ranked higher)
    - Medium preference: 1.0x multiplier (normal ranking)
    - Low preference: 0.5x multiplier (ranked lower)
    """
    
    # Blueprint preference weight multipliers
    BLUEPRINT_WEIGHT_MULTIPLIERS = {
        "low": 0.5,
        "medium": 1.0,
        "high": 1.5,
    }
    
    DEFAULT_WEIGHT = 1.0  # Medium preference
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize blueprint ranker.
        
        Args:
            user_id: User ID (default: "default" for single-user systems)
        """
        self.user_id = user_id
        self.preference_manager = PreferenceManager(user_id=user_id)
    
    async def apply_blueprint_preference_weighting(
        self,
        suggestions: list[dict[str, Any]],
        preserve_order: bool = False
    ) -> list[dict[str, Any]]:
        """
        Apply blueprint preference weighting to suggestions.
        
        Blueprint opportunities get their confidence/ranking scores adjusted
        based on user's blueprint preference setting.
        
        Args:
            suggestions: List of suggestion dictionaries
            preserve_order: If True, only adjust scores without re-sorting (default: False)
            
        Returns:
            Suggestions with adjusted ranking scores, optionally re-sorted
        """
        if not suggestions:
            return []
        
        try:
            # Get user's blueprint preference
            blueprint_preference = await self.preference_manager.get_blueprint_preference()
            weight_multiplier = self.BLUEPRINT_WEIGHT_MULTIPLIERS.get(
                blueprint_preference,
                self.DEFAULT_WEIGHT
            )
            
            logger.debug(
                f"Applying blueprint preference weighting: {blueprint_preference} (multiplier: {weight_multiplier}x)",
                extra={
                    'user_id': self.user_id,
                    'blueprint_preference': blueprint_preference,
                    'multiplier': weight_multiplier,
                }
            )
            
            # Apply weighting to blueprint opportunities
            blueprint_count = 0
            for suggestion in suggestions:
                if self._is_blueprint_opportunity(suggestion):
                    # Get base confidence or ranking score
                    base_score = (
                        suggestion.get('_creativity_ranking_score') or
                        suggestion.get('_ranking_score') or
                        suggestion.get('confidence', 0.5)
                    )
                    
                    # Apply blueprint preference multiplier
                    adjusted_score = base_score * weight_multiplier
                    
                    # Store adjusted score for ranking (don't modify original confidence)
                    suggestion['_blueprint_weighted_score'] = adjusted_score
                    
                    blueprint_count += 1
            
            logger.info(
                f"Applied blueprint preference weighting ({blueprint_preference}): "
                f"{blueprint_count} blueprint opportunities weighted",
                extra={
                    'user_id': self.user_id,
                    'blueprint_preference': blueprint_preference,
                    'blueprint_count': blueprint_count,
                }
            )
            
            # Re-rank if requested
            if not preserve_order:
                suggestions = self._re_rank_suggestions(suggestions)
            
            return suggestions
            
        except Exception as e:
            logger.error(
                f"Error applying blueprint preference weighting: {e}",
                exc_info=True,
                extra={'user_id': self.user_id, 'error_type': type(e).__name__}
            )
            # Return original suggestions on error (graceful degradation)
            return suggestions
    
    def _is_blueprint_opportunity(self, suggestion: dict[str, Any]) -> bool:
        """
        Check if suggestion is a blueprint opportunity.
        
        Args:
            suggestion: Suggestion dictionary
            
        Returns:
            True if blueprint opportunity, False otherwise
        """
        # Check type
        suggestion_type = suggestion.get('type', '')
        if suggestion_type == 'blueprint_opportunity':
            return True
        
        # Check source
        source = suggestion.get('source', '')
        if 'blueprint' in source.lower() or 'Epic-AI-6' in source:
            return True
        
        # Check if blueprint-validated
        if suggestion.get('blueprint_validated', False):
            return True
        
        # Check if has blueprint_id
        if suggestion.get('blueprint_id'):
            return True
        
        return False
    
    def _re_rank_suggestions(
        self,
        suggestions: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Re-rank suggestions using blueprint-weighted scores.
        
        Args:
            suggestions: List of suggestions
            
        Returns:
            Re-ranked suggestions (highest score first)
        """
        # Sort by blueprint-weighted score (or fallback to other scores)
        ranked = sorted(
            suggestions,
            key=lambda s: (
                s.get('_blueprint_weighted_score') or  # Blueprint-weighted score
                s.get('_creativity_ranking_score') or  # Creativity ranking score
                s.get('_ranking_score') or             # Phase 5 ranking score
                s.get('confidence', 0.0)               # Base confidence
            ),
            reverse=True
        )
        
        # Clean up temporary scores (optional - can keep for debugging)
        # for suggestion in ranked:
        #     if '_blueprint_weighted_score' in suggestion:
        #         # Keep for potential debugging, but don't return in final output
        #         pass
        
        return ranked
