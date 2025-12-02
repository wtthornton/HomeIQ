"""
Pattern Quality Service

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.3: Pattern Quality Scoring Service

Service for pattern quality scoring and filtering.
"""

import logging
from pathlib import Path
from typing import Any

from .scorer import PatternQualityScorer

logger = logging.getLogger(__name__)


class PatternQualityService:
    """
    Service for pattern quality scoring and filtering.
    
    Provides lifecycle management and quality scoring functionality.
    """
    
    def __init__(self, model_path: Path | str | None = None):
        """
        Initialize quality service.
        
        Args:
            model_path: Path to trained model file (optional)
        """
        self.scorer = PatternQualityScorer(model_path)
        self._started = False
    
    async def startup(self) -> None:
        """
        Start service (load model).
        
        Model is already loaded in scorer.__init__, but this method
        can be used for additional initialization or model reloading.
        """
        if not self._started:
            # Model is loaded in scorer.__init__, but we can reload here if needed
            self._started = True
            logger.info("Pattern quality service started")
    
    async def shutdown(self) -> None:
        """Shutdown service."""
        self._started = False
        logger.info("Pattern quality service stopped")
    
    def score_pattern(self, pattern: Any) -> float:
        """
        Score a single pattern.
        
        Args:
            pattern: Pattern model or dict
        
        Returns:
            Quality score (0.0-1.0)
        """
        return self.scorer.score_pattern(pattern)
    
    def score_patterns(self, patterns: list[Any]) -> list[float]:
        """
        Score multiple patterns.
        
        Args:
            patterns: List of Pattern models or dicts
        
        Returns:
            List of quality scores (0.0-1.0)
        """
        return self.scorer.score_patterns(patterns)
    
    def filter_by_quality(
        self,
        patterns: list[Any],
        threshold: float = 0.7
    ) -> list[tuple[Any, float]]:
        """
        Filter patterns by quality threshold.
        
        Args:
            patterns: List of patterns
            threshold: Minimum quality score (0.0-1.0)
        
        Returns:
            List of (pattern, score) tuples for patterns above threshold
        """
        return self.scorer.filter_by_quality(patterns, threshold)
    
    def rank_by_quality(self, patterns: list[Any]) -> list[tuple[Any, float]]:
        """
        Rank patterns by quality score (highest first).
        
        Args:
            patterns: List of patterns
        
        Returns:
            List of (pattern, score) tuples sorted by score (descending)
        """
        return self.scorer.rank_by_quality(patterns)
    
    def is_model_loaded(self) -> bool:
        """
        Check if model is loaded.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.scorer.is_model_loaded()

