"""
Pattern Drift Detection

Detects when pattern quality degrades over time (model drift).
"""

import logging
from typing import Any
from datetime import datetime, timezone
import statistics

logger = logging.getLogger(__name__)


class PatternDriftDetector:
    """Detect pattern quality drift"""
    
    def __init__(self, drift_threshold: float = 0.1):
        """
        Initialize drift detector.
        
        Args:
            drift_threshold: Quality degradation threshold (0.1 = 10%)
        """
        self.drift_threshold = drift_threshold
        self.baseline_quality: dict[str, Any] | None = None
        self.quality_history: list[dict[str, Any]] = []
        self.drift_detections: list[dict[str, Any]] = []
    
    def check_drift(
        self,
        current_patterns: list[dict[str, Any]],
        quality_scores: list[float] | None = None
    ) -> dict[str, Any]:
        """
        Check for quality drift.
        
        Args:
            current_patterns: List of current patterns
            quality_scores: Optional pre-calculated quality scores
        
        Returns:
            Dictionary with drift detection results
        """
        # Calculate current quality distribution
        if quality_scores is None:
            # Calculate quality scores if not provided
            from ..testing.pattern_quality_scorer import PatternQualityScorer
            scorer = PatternQualityScorer()
            quality_scores = [
                scorer.calculate_quality_score(p)['quality_score']
                for p in current_patterns
            ]
        
        current_quality = self._calculate_quality_distribution(quality_scores)
        
        # Store in history
        self.quality_history.append({
            'quality_distribution': current_quality,
            'timestamp': datetime.now(timezone.utc),
            'pattern_count': len(current_patterns)
        })
        
        if self.baseline_quality is None:
            # Set baseline
            self.baseline_quality = current_quality
            return {
                'drift_detected': False,
                'baseline_set': True,
                'baseline_quality': current_quality
            }
        
        # Compare with baseline
        quality_degradation = self.baseline_quality['mean'] - current_quality['mean']
        
        if quality_degradation > self.drift_threshold:
            drift_info = {
                'drift_detected': True,
                'degradation': quality_degradation,
                'baseline_mean': self.baseline_quality['mean'],
                'current_mean': current_quality['mean'],
                'recommendation': 'retrain_quality_model',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            self.drift_detections.append(drift_info)
            logger.warning(
                f"Pattern quality drift detected: {quality_degradation:.2f} degradation "
                f"(baseline: {self.baseline_quality['mean']:.2f}, current: {current_quality['mean']:.2f})"
            )
            
            return drift_info
        
        return {
            'drift_detected': False,
            'degradation': quality_degradation,
            'baseline_mean': self.baseline_quality['mean'],
            'current_mean': current_quality['mean']
        }
    
    def _calculate_quality_distribution(
        self,
        quality_scores: list[float]
    ) -> dict[str, Any]:
        """
        Calculate quality distribution statistics.
        
        Args:
            quality_scores: List of quality scores
        
        Returns:
            Dictionary with distribution statistics
        """
        if not quality_scores:
            return {
                'mean': 0.0,
                'median': 0.0,
                'std': 0.0,
                'min': 0.0,
                'max': 0.0,
                'count': 0
            }
        
        sorted_scores = sorted(quality_scores)
        n = len(sorted_scores)
        
        return {
            'mean': statistics.mean(quality_scores),
            'median': statistics.median(quality_scores),
            'std': statistics.stdev(quality_scores) if n > 1 else 0.0,
            'min': sorted_scores[0],
            'max': sorted_scores[-1],
            'count': n
        }
    
    def reset_baseline(self, patterns: list[dict[str, Any]] | None = None, quality_scores: list[float] | None = None):
        """
        Reset baseline quality.
        
        Args:
            patterns: Optional list of patterns to use for baseline
            quality_scores: Optional pre-calculated quality scores
        """
        if quality_scores is None and patterns:
            from ..testing.pattern_quality_scorer import PatternQualityScorer
            scorer = PatternQualityScorer()
            quality_scores = [
                scorer.calculate_quality_score(p)['quality_score']
                for p in patterns
            ]
        
        if quality_scores:
            self.baseline_quality = self._calculate_quality_distribution(quality_scores)
            logger.info(f"Baseline quality reset: mean={self.baseline_quality['mean']:.2f}")
    
    def get_drift_statistics(self) -> dict[str, Any]:
        """Get drift detection statistics"""
        return {
            'baseline_set': self.baseline_quality is not None,
            'baseline_quality': self.baseline_quality,
            'drift_detections': len(self.drift_detections),
            'quality_history_size': len(self.quality_history),
            'last_drift': self.drift_detections[-1] if self.drift_detections else None
        }

