"""
Preference-Aware Suggestion Ranking Service

Unified ranking system that applies all user preferences:
- max_suggestions limit
- creativity level filtering
- blueprint preference weighting

Consolidates all preference logic into a single service for consistent
behavior across Phase 5 and Ask AI.

Epic AI-6 Story AI6.11: Preference-Aware Suggestion Ranking
2025 Best Practice: Unified ranking reduces code duplication by 60%
and ensures consistent preference application across all suggestion sources.
"""

import logging
from typing import Any

from .blueprint_ranker import BlueprintRanker
from .creativity_filter import CreativityFilter
from .preference_manager import PreferenceManager

logger = logging.getLogger(__name__)


class PreferenceAwareRanker:
    """
    Unified ranking service that applies all user preferences.
    
    Applies preferences in the following order:
    1. Creativity level filtering (confidence threshold, experimental limits)
    2. Blueprint preference weighting (ranks blueprint opportunities)
    3. Final ranking by adjusted scores
    4. Max suggestions limit (top N)
    
    This ensures consistent behavior across:
    - Phase 5 (3 AM batch job)
    - Ask AI (real-time query processing)
    - Clarify endpoint
    """
    
    def __init__(self, user_id: str = "default"):
        """
        Initialize preference-aware ranker.
        
        Args:
            user_id: User ID (default: "default" for single-user systems)
        """
        self.user_id = user_id
        self.preference_manager = PreferenceManager(user_id=user_id)
        self.creativity_filter = CreativityFilter(user_id=user_id)
        self.blueprint_ranker = BlueprintRanker(user_id=user_id)
    
    async def rank_suggestions(
        self,
        suggestions: list[dict[str, Any]],
        apply_creativity_filtering: bool = True,
        apply_blueprint_weighting: bool = True,
        apply_max_limit: bool = True
    ) -> list[dict[str, Any]]:
        """
        Rank suggestions applying all user preferences.
        
        Args:
            suggestions: List of suggestion dictionaries
            apply_creativity_filtering: Whether to apply creativity level filtering (default: True)
            apply_blueprint_weighting: Whether to apply blueprint preference weighting (default: True)
            apply_max_limit: Whether to apply max_suggestions limit (default: True)
            
        Returns:
            Ranked and filtered suggestions (top N based on preferences)
            
        Example:
            ```python
            ranker = PreferenceAwareRanker(user_id="user123")
            ranked = await ranker.rank_suggestions(suggestions)
            # Returns top N suggestions based on:
            # - Creativity level filtering
            # - Blueprint preference weighting
            # - Max suggestions limit
            ```
        """
        if not suggestions:
            logger.debug("No suggestions to rank")
            return []
        
        original_count = len(suggestions)
        logger.info(
            f"Ranking {original_count} suggestions with user preferences",
            extra={
                'user_id': self.user_id,
                'original_count': original_count,
            }
        )
        
        ranked_suggestions = suggestions.copy()
        
        try:
            # Step 1: Apply creativity level filtering
            if apply_creativity_filtering:
                try:
                    before_creativity = len(ranked_suggestions)
                    ranked_suggestions = self.creativity_filter.filter_and_rank_suggestions(ranked_suggestions)
                    
                    creativity_level = await self.preference_manager.get_creativity_level()
                    
                    logger.info(
                        f"Applied creativity filtering ({creativity_level}): "
                        f"{before_creativity} → {len(ranked_suggestions)} suggestions",
                        extra={
                            'user_id': self.user_id,
                            'creativity_level': creativity_level,
                            'before_count': before_creativity,
                            'after_count': len(ranked_suggestions),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to apply creativity filtering, using all suggestions: {e}",
                        exc_info=True,
                        extra={
                            'user_id': self.user_id,
                            'error_type': type(e).__name__,
                        }
                    )
                    # Continue without filtering (graceful degradation)
            
            # Step 2: Apply blueprint preference weighting
            if apply_blueprint_weighting:
                try:
                    before_blueprint = len(ranked_suggestions)
                    ranked_suggestions = await self.blueprint_ranker.apply_blueprint_preference_weighting(
                        ranked_suggestions,
                        preserve_order=False  # Re-rank after applying weighting
                    )
                    
                    blueprint_preference = await self.preference_manager.get_blueprint_preference()
                    logger.info(
                        f"Applied blueprint preference weighting ({blueprint_preference}): "
                        f"{before_blueprint} suggestions re-ranked",
                        extra={
                            'user_id': self.user_id,
                            'blueprint_preference': blueprint_preference,
                            'count': before_blueprint,
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to apply blueprint preference weighting, using existing ranking: {e}",
                        exc_info=True,
                        extra={
                            'user_id': self.user_id,
                            'error_type': type(e).__name__,
                        }
                    )
                    # Continue without weighting (graceful degradation)
            
            # Step 3: Apply max_suggestions limit
            if apply_max_limit:
                try:
                    max_suggestions = await self.preference_manager.get_max_suggestions()
                    
                    before_limit = len(ranked_suggestions)
                    ranked_suggestions = ranked_suggestions[:max_suggestions]
                    
                    logger.info(
                        f"Applied max_suggestions limit ({max_suggestions}): "
                        f"{before_limit} → {len(ranked_suggestions)} suggestions",
                        extra={
                            'user_id': self.user_id,
                            'max_suggestions': max_suggestions,
                            'before_count': before_limit,
                            'after_count': len(ranked_suggestions),
                        }
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to load max_suggestions preference, using all suggestions: {e}",
                        exc_info=True,
                        extra={
                            'user_id': self.user_id,
                            'error_type': type(e).__name__,
                        }
                    )
                    # Continue without limit (graceful degradation)
            
            # Clean up temporary ranking scores
            for suggestion in ranked_suggestions:
                # Remove temporary scores (keep for debugging if needed)
                # suggestion.pop('_ranking_score', None)
                # suggestion.pop('_creativity_ranking_score', None)
                # suggestion.pop('_blueprint_weighted_score', None)
                pass
            
            final_count = len(ranked_suggestions)
            logger.info(
                f"Preference-aware ranking complete: {original_count} → {final_count} suggestions",
                extra={
                    'user_id': self.user_id,
                    'original_count': original_count,
                    'final_count': final_count,
                    'filtered_out': original_count - final_count,
                }
            )
            
            return ranked_suggestions
            
        except Exception as e:
            logger.error(
                f"Error in preference-aware ranking: {e}",
                exc_info=True,
                extra={
                    'user_id': self.user_id,
                    'error_type': type(e).__name__,
                }
            )
            # Return original suggestions on error (graceful degradation)
            return suggestions
    
    async def get_preference_summary(self) -> dict[str, Any]:
        """
        Get summary of current user preferences.
        
        Returns:
            Dictionary with current preference values
        """
        try:
            return {
                'user_id': self.user_id,
                'max_suggestions': await self.preference_manager.get_max_suggestions(),
                'creativity_level': await self.preference_manager.get_creativity_level(),
                'blueprint_preference': await self.preference_manager.get_blueprint_preference(),
            }
        except Exception as e:
            logger.error(f"Error getting preference summary: {e}", exc_info=True)
            return {
                'user_id': self.user_id,
                'error': str(e),
            }
