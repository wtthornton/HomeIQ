"""
Pattern Quality Filter

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.7: Pattern Quality Filtering in 3 AM Workflow

Filter patterns by quality score before suggestion generation.
"""

import logging
import time
from typing import Any

from .quality_service import PatternQualityService
from .feature_extractor import PatternFeatureExtractor

logger = logging.getLogger(__name__)


class PatternQualityFilter:
    """
    Filter patterns by quality score.
    
    Filters patterns based on ML-predicted quality scores,
    ensuring only high-quality patterns are used for suggestions.
    """
    
    def __init__(
        self,
        quality_service: PatternQualityService | None = None,
        feature_extractor: PatternFeatureExtractor | None = None,
        quality_threshold: float = 0.7,
        enable_filtering: bool = True
    ):
        """
        Initialize quality filter.
        
        Args:
            quality_service: Pattern quality scoring service (default: create new)
            feature_extractor: Feature extractor (default: create new)
            quality_threshold: Minimum quality score (0.0-1.0)
            enable_filtering: Enable/disable filtering
        """
        self.quality_service = quality_service or PatternQualityService()
        self.feature_extractor = feature_extractor or PatternFeatureExtractor()
        self.quality_threshold = quality_threshold
        self.enable_filtering = enable_filtering
    
    async def filter_patterns(
        self,
        patterns: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Filter patterns by quality score.
        
        Args:
            patterns: List of pattern dictionaries
        
        Returns:
            Tuple of (filtered_patterns, stats)
            - filtered_patterns: Patterns that meet quality threshold
            - stats: Filtering statistics (total, filtered, avg_quality, etc.)
        """
        if not self.enable_filtering or not patterns:
            return patterns, {
                'total': len(patterns),
                'filtered': len(patterns),
                'removed': 0,
                'avg_quality': 0.0,
                'filtering_enabled': False
            }
        
        start_time = time.time()
        
        try:
            # Score all patterns
            scored_patterns = []
            for pattern in patterns:
                try:
                    # Extract features
                    features = self.feature_extractor.extract_features(pattern)
                    
                    # Score pattern
                    quality_score = await self.quality_service.score_pattern(features)
                    
                    # Add quality score to pattern
                    pattern_with_score = pattern.copy()
                    pattern_with_score['quality_score'] = quality_score
                    pattern_with_score['_quality_scored'] = True
                    
                    scored_patterns.append(pattern_with_score)
                    
                except Exception as e:
                    logger.warning(f"Error scoring pattern: {e}")
                    # Include pattern without score if scoring fails (backward compatibility)
                    pattern_with_score = pattern.copy()
                    pattern_with_score['quality_score'] = 0.5  # Default score
                    pattern_with_score['_quality_scored'] = False
                    scored_patterns.append(pattern_with_score)
            
            # Filter by threshold
            filtered_patterns = [
                p for p in scored_patterns
                if p.get('quality_score', 0.0) >= self.quality_threshold
            ]
            
            # Calculate statistics
            total = len(patterns)
            filtered = len(filtered_patterns)
            removed = total - filtered
            
            quality_scores = [p.get('quality_score', 0.0) for p in scored_patterns]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            
            processing_time = time.time() - start_time
            
            stats = {
                'total': total,
                'filtered': filtered,
                'removed': removed,
                'avg_quality': avg_quality,
                'min_quality': min(quality_scores) if quality_scores else 0.0,
                'max_quality': max(quality_scores) if quality_scores else 0.0,
                'threshold': self.quality_threshold,
                'filtering_enabled': True,
                'processing_time': processing_time
            }
            
            logger.info(
                f"Quality filtering: {total} patterns → {filtered} filtered "
                f"(removed {removed}, avg quality: {avg_quality:.3f}, "
                f"time: {processing_time*1000:.1f}ms)"
            )
            
            return filtered_patterns, stats
            
        except Exception as e:
            logger.error(f"Error filtering patterns: {e}", exc_info=True)
            # Return all patterns on error (backward compatibility)
            return patterns, {
                'total': len(patterns),
                'filtered': len(patterns),
                'removed': 0,
                'avg_quality': 0.0,
                'filtering_enabled': False,
                'error': str(e)
            }
    
    def rank_by_quality(
        self,
        patterns: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Rank patterns by quality score.
        
        Args:
            patterns: List of pattern dictionaries with quality scores
        
        Returns:
            Sorted list (highest quality first)
        """
        # Sort by quality score (descending), then by confidence (descending)
        ranked = sorted(
            patterns,
            key=lambda p: (
                p.get('quality_score', 0.0),
                p.get('confidence', 0.0)
            ),
            reverse=True
        )
        
        return ranked
    
    async def filter_and_rank(
        self,
        patterns: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """
        Filter patterns by quality and rank by quality score.
        
        Args:
            patterns: List of pattern dictionaries
        
        Returns:
            Tuple of (filtered_and_ranked_patterns, stats)
        """
        filtered_patterns, stats = await self.filter_patterns(patterns)
        ranked_patterns = self.rank_by_quality(filtered_patterns)
        
        return ranked_patterns, stats

