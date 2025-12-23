"""
Pattern Quality Scorer

Epic AI-13: ML-Based Pattern Quality & Active Learning
Story AI13.3: Pattern Quality Scoring Service

Score patterns using trained quality model.
"""

import logging
from pathlib import Path
from typing import Any

from .quality_model import PatternQualityModel

logger = logging.getLogger(__name__)


class PatternQualityScorer:
    """
    Score patterns using trained quality model.
    """
    
    def __init__(self, model_path: Path | str | None = None):
        """
        Initialize quality scorer.
        
        Args:
            model_path: Path to trained model file (optional, uses default if None)
        """
        self.model: PatternQualityModel | None = None
        self.model_path = self._get_model_path(model_path)
        self._load_model()
    
    def _get_model_path(self, model_path: Path | str | None) -> Path:
        """
        Get model path (default or provided).
        
        Args:
            model_path: Provided model path or None
        
        Returns:
            Path to model file
        """
        if model_path:
            return Path(model_path)
        
        # Default model path
        default_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "models"
            / "pattern_quality_model.joblib"
        )
        return default_path
    
    def _load_model(self) -> None:
        """Load trained model from disk."""
        try:
            if self.model_path.exists():
                self.model = PatternQualityModel.load(self.model_path)
                logger.info(f"Quality model loaded from {self.model_path}")
            else:
                logger.warning(
                    f"Model file not found: {self.model_path}. "
                    "Using default scores. Train model first using train_pattern_quality_model.py"
                )
                self.model = None
        except Exception as e:
            logger.error(f"Error loading quality model: {e}", exc_info=True)
            self.model = None
    
    def score_pattern(self, pattern: Any) -> float:
        """
        Score a single pattern.
        
        Args:
            pattern: Pattern model or dict
        
        Returns:
            Quality score (0.0-1.0, probability of being good pattern)
        """
        if self.model is None:
            logger.debug("Model not available, returning default quality score")
            return 0.5  # Default score when model not available
        
        return self.model.predict_quality(pattern)
    
    def score_patterns(self, patterns: list[Any]) -> list[float]:
        """
        Score multiple patterns.
        
        Args:
            patterns: List of Pattern models or dicts
        
        Returns:
            List of quality scores (0.0-1.0)
        """
        if not patterns:
            return []
        
        if self.model is None:
            logger.debug("Model not available, returning default quality scores")
            return [0.5] * len(patterns)  # Default scores
        
        return self.model.predict_quality_batch(patterns)
    
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
        if not patterns:
            return []
        
        scores = self.score_patterns(patterns)
        
        filtered = [
            (pattern, score)
            for pattern, score in zip(patterns, scores)
            if score >= threshold
        ]
        
        logger.debug(f"Filtered {len(filtered)}/{len(patterns)} patterns above threshold {threshold}")
        
        return filtered
    
    def rank_by_quality(
        self,
        patterns: list[Any]
    ) -> list[tuple[Any, float]]:
        """
        Rank patterns by quality score (highest first).
        
        Args:
            patterns: List of patterns
        
        Returns:
            List of (pattern, score) tuples sorted by score (descending)
        """
        if not patterns:
            return []
        
        scores = self.score_patterns(patterns)
        
        ranked = sorted(
            zip(patterns, scores),
            key=lambda x: x[1],
            reverse=True
        )
        
        return ranked
    
    def is_model_loaded(self) -> bool:
        """
        Check if model is loaded.
        
        Returns:
            True if model is loaded, False otherwise
        """
        return self.model is not None

