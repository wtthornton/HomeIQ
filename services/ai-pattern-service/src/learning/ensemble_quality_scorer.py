"""
Multi-Model Ensemble Quality Scorer

Epic 39, Story 39.7: Pattern Learning & RLHF Migration
Combines multiple quality models and learns which performs best.

Note: Dependencies on quality_calibration_loop and weight_optimization_loop
will need to be addressed in future stories (simplified versions for now).
"""

import logging
from typing import Any
from datetime import datetime, timezone
import statistics

from .pattern_quality_scorer import PatternQualityScorer

logger = logging.getLogger(__name__)


class EnsembleQualityScorer:
    """
    Ensemble of quality scoring models.
    
    Epic 39, Story 39.7: Extracted to pattern service.
    Note: Calibration and optimization loops are simplified for Story 39.7.
    """
    
    def __init__(self):
        """Initialize ensemble quality scorer"""
        # Initialize base model
        self.models = {
            'base': PatternQualityScorer(),
            'calibrated': None,  # Will be initialized with calibration loop (future)
            'optimized': None  # Will be initialized with optimization loop (future)
        }
        
        # Simplified calibration/optimization (full versions in future stories)
        self.calibration_loop = None  # QualityCalibrationLoop() - future
        self.optimization_loop = None  # WeightOptimizationLoop() - future
        
        # Model weights (how much to trust each model)
        self.model_weights = {
            'base': 1.0,  # Start with 100% base model
            'calibrated': 0.0,  # Will increase as calibration data accumulates
            'optimized': 0.0  # Will increase as optimization data accumulates
        }
        
        self.performance_history: dict[str, list[float]] = {
            model: [] for model in self.models
        }
    
    def calculate_ensemble_quality(
        self,
        pattern: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Calculate ensemble quality score.
        
        Args:
            pattern: Pattern dictionary
        
        Returns:
            Dictionary with ensemble quality score and breakdown
        """
        scores = {}
        
        # Base model
        base_result = self.models['base'].calculate_quality_score(pattern)
        scores['base'] = base_result['quality_score']
        
        # Calibrated model (if available - future)
        if self.calibration_loop and len(getattr(self.calibration_loop, 'acceptance_history', [])) >= 10:
            calibrated_quality = self._calculate_with_weights(
                pattern,
                getattr(self.calibration_loop, 'quality_weights', {})
            )
            scores['calibrated'] = calibrated_quality
        else:
            scores['calibrated'] = scores['base']  # Fallback to base
        
        # Optimized model (if available - future)
        if self.optimization_loop and len(getattr(self.optimization_loop, 'training_history', [])) >= 10:
            optimized_quality = getattr(self.optimization_loop, '_calculate_quality', lambda p: scores['base'])(pattern)
            scores['optimized'] = optimized_quality
        else:
            scores['optimized'] = scores['base']  # Fallback to base
        
        # Weighted average
        ensemble_score = sum(
            scores[model] * self.model_weights[model]
            for model in self.models
        )
        
        return {
            'quality_score': ensemble_score,
            'base_score': scores['base'],
            'calibrated_score': scores['calibrated'],
            'optimized_score': scores['optimized'],
            'model_weights': self.model_weights.copy(),
            'breakdown': scores
        }
    
    def _calculate_with_weights(
        self,
        pattern: dict[str, Any],
        weights: dict[str, float]
    ) -> float:
        """Calculate quality with custom weights"""
        # Extract component values
        component_values = {
            'confidence': pattern.get('confidence', 0.0),
            'frequency': self._extract_frequency(pattern),
            'temporal': self._extract_temporal(pattern),
            'relationship': self._extract_relationship(pattern)
        }
        
        # Calculate weighted sum
        quality = sum(
            component_values.get(component, 0.0) * weight
            for component, weight in weights.items()
        )
        
        return max(0.0, min(1.0, quality))
    
    def _extract_frequency(self, pattern: dict[str, Any]) -> float:
        """Extract frequency component value"""
        occurrences = pattern.get('occurrences', 0)
        if occurrences == 0:
            return 0.0
        elif occurrences <= 2:
            return 0.3
        elif occurrences <= 5:
            return 0.6
        elif occurrences <= 10:
            return 0.8
        else:
            return 1.0
    
    def _extract_temporal(self, pattern: dict[str, Any]) -> float:
        """Extract temporal component value"""
        pattern_type = pattern.get('pattern_type', '')
        if pattern_type == 'time_of_day':
            return 0.9
        elif pattern_type == 'co_occurrence':
            return 0.8
        return 0.5
    
    def _extract_relationship(self, pattern: dict[str, Any]) -> float:
        """Extract relationship component value"""
        area1 = pattern.get('area1', pattern.get('area', ''))
        area2 = pattern.get('area2', '')
        if area1 and area2 and area1 == area2:
            return 0.5
        return 0.3
    
    def update_model_weights(
        self,
        pattern: dict[str, Any],
        actual_acceptance: bool
    ) -> dict[str, Any]:
        """
        Update model weights based on performance.
        
        Args:
            pattern: Pattern dictionary
            actual_acceptance: True if user accepted, False if rejected
        
        Returns:
            Dictionary with update results
        """
        # Calculate quality with each model
        scores = {}
        
        # Base model
        base_result = self.models['base'].calculate_quality_score(pattern)
        scores['base'] = base_result['quality_score']
        
        # Calibrated model (if available)
        if self.calibration_loop and len(getattr(self.calibration_loop, 'acceptance_history', [])) >= 10:
            scores['calibrated'] = self._calculate_with_weights(
                pattern,
                getattr(self.calibration_loop, 'quality_weights', {})
            )
        else:
            scores['calibrated'] = scores['base']
        
        # Optimized model (if available)
        if self.optimization_loop and len(getattr(self.optimization_loop, 'training_history', [])) >= 10:
            scores['optimized'] = getattr(self.optimization_loop, '_calculate_quality', lambda p: scores['base'])(pattern)
        else:
            scores['optimized'] = scores['base']
        
        # Evaluate performance (error)
        actual_quality = 1.0 if actual_acceptance else 0.0
        for model_name, score in scores.items():
            error = abs(score - actual_quality)
            self.performance_history[model_name].append(error)
        
        # Update weights (inverse of average error)
        total_inverse_error = 0.0
        inverse_errors = {}
        
        for model_name, errors in self.performance_history.items():
            if errors:
                # Use last 10 errors for stability
                recent_errors = errors[-10:]
                avg_error = sum(recent_errors) / len(recent_errors)
                inverse_error = 1.0 / (avg_error + 0.01)  # Add small epsilon
                inverse_errors[model_name] = inverse_error
                total_inverse_error += inverse_error
        
        # Normalize weights
        if total_inverse_error > 0:
            old_weights = self.model_weights.copy()
            for model_name in self.models:
                self.model_weights[model_name] = inverse_errors[model_name] / total_inverse_error
            
            return {
                'old_weights': old_weights,
                'new_weights': self.model_weights.copy(),
                'model_errors': {
                    model: statistics.mean(errors[-10:]) if errors else 0.0
                    for model, errors in self.performance_history.items()
                }
            }
        
        return {
            'old_weights': self.model_weights.copy(),
            'new_weights': self.model_weights.copy(),
            'model_errors': {}
        }
    
    def get_ensemble_stats(self) -> dict[str, Any]:
        """Get ensemble statistics"""
        return {
            'model_weights': self.model_weights.copy(),
            'performance_history_size': {
                model: len(errors)
                for model, errors in self.performance_history.items()
            },
            'average_errors': {
                model: statistics.mean(errors[-10:]) if errors else 0.0
                for model, errors in self.performance_history.items()
            }
        }

