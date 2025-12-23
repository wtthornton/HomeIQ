"""
Multi-Model Ensemble Quality Scorer

Combines multiple quality models and learns which performs best.
"""

import logging
from typing import Any
from datetime import datetime, timezone
import statistics

logger = logging.getLogger(__name__)


class EnsembleQualityScorer:
    """Ensemble of quality scoring models"""
    
    def __init__(self):
        """Initialize ensemble quality scorer"""
        # Initialize base models
        from ..testing.pattern_quality_scorer import PatternQualityScorer
        from .quality_calibration_loop import QualityCalibrationLoop
        from .weight_optimization_loop import WeightOptimizationLoop
        
        self.models = {
            'base': PatternQualityScorer(),
            'calibrated': None,  # Will be initialized with calibration loop
            'optimized': None  # Will be initialized with optimization loop
        }
        
        # Initialize calibration and optimization loops
        self.calibration_loop = QualityCalibrationLoop()
        self.optimization_loop = WeightOptimizationLoop()
        
        # Model weights (how much to trust each model)
        self.model_weights = {
            'base': 0.33,
            'calibrated': 0.33,
            'optimized': 0.34
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
        
        # Calibrated model (if available)
        if self.calibration_loop and len(self.calibration_loop.acceptance_history) >= 10:
            # Use calibrated weights
            calibrated_quality = self._calculate_with_weights(
                pattern,
                self.calibration_loop.quality_weights
            )
            scores['calibrated'] = calibrated_quality
        else:
            scores['calibrated'] = scores['base']  # Fallback to base
        
        # Optimized model (if available)
        if self.optimization_loop and len(self.optimization_loop.training_history) >= 10:
            optimized_quality = self.optimization_loop._calculate_quality(pattern)
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
        from .quality_calibration_loop import QualityCalibrationLoop
        temp_loop = QualityCalibrationLoop()
        temp_loop.quality_weights = weights
        
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
        
        # Calibrated model
        if self.calibration_loop and len(self.calibration_loop.acceptance_history) >= 10:
            scores['calibrated'] = self._calculate_with_weights(
                pattern,
                self.calibration_loop.quality_weights
            )
        else:
            scores['calibrated'] = scores['base']
        
        # Optimized model
        if self.optimization_loop and len(self.optimization_loop.training_history) >= 10:
            scores['optimized'] = self.optimization_loop._calculate_quality(pattern)
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
                inverse_error = 1.0 / (avg_error + 0.01)  # Add small epsilon to avoid division by zero
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

