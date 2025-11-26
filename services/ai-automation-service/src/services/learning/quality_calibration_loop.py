"""
Quality Calibration Loop

Continuously calibrates quality scores based on user acceptance.
Implements feedback loops for continuous improvement.
"""

import logging
from typing import Any
from datetime import datetime, timezone
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)


class QualityCalibrationLoop:
    """Continuous quality score calibration based on user feedback"""
    
    def __init__(self, min_samples: int = 20):
        """
        Initialize quality calibration loop.
        
        Args:
            min_samples: Minimum number of samples before calibration
        """
        self.min_samples = min_samples
        self.acceptance_history: list[dict[str, Any]] = []
        self.quality_weights = {
            'confidence': 0.40,
            'frequency': 0.30,
            'temporal': 0.20,
            'relationship': 0.10
        }
        self.calibration_stats = {
            'total_samples': 0,
            'calibrations_performed': 0,
            'last_calibration': None
        }
    
    async def process_pattern_feedback(
        self,
        pattern: dict[str, Any],
        quality_score: float,
        user_action: str
    ) -> dict[str, Any]:
        """
        Process pattern feedback and update calibration.
        
        Args:
            pattern: Pattern dictionary
            quality_score: Predicted quality score
            user_action: User action ('accept', 'reject', 'modify', 'deploy', 'disable')
        
        Returns:
            Dictionary with calibration status
        """
        # Determine if accepted
        accepted = user_action in ['accept', 'deploy']
        
        # Store in history
        self.acceptance_history.append({
            'pattern': pattern,
            'quality_score': quality_score,
            'accepted': accepted,
            'user_action': user_action,
            'timestamp': datetime.now(timezone.utc)
        })
        
        self.calibration_stats['total_samples'] += 1
        
        # Calibrate if enough samples
        calibration_result = None
        if len(self.acceptance_history) >= self.min_samples:
            calibration_result = self._calibrate_weights()
        
        return {
            'samples_collected': len(self.acceptance_history),
            'calibration_performed': calibration_result is not None,
            'calibration_result': calibration_result,
            'stats': self.calibration_stats.copy()
        }
    
    def _calibrate_weights(self) -> dict[str, Any]:
        """
        Calibrate weights to maximize acceptance rate.
        
        Returns:
            Dictionary with calibration results
        """
        # Group by quality ranges
        quality_ranges = {
            'high': [p for p in self.acceptance_history if p['quality_score'] >= 0.75],
            'medium': [p for p in self.acceptance_history if 0.5 <= p['quality_score'] < 0.75],
            'low': [p for p in self.acceptance_history if p['quality_score'] < 0.5]
        }
        
        # Calculate acceptance rates
        acceptance_rates = {}
        for tier, patterns in quality_ranges.items():
            if patterns:
                acceptance_rate = sum(p['accepted'] for p in patterns) / len(patterns)
                acceptance_rates[tier] = acceptance_rate
            else:
                acceptance_rates[tier] = 0.0
        
        # Adjust weights if acceptance rate doesn't match expected
        adjustments = {}
        if acceptance_rates.get('high', 0.0) < 0.8:
            # High quality patterns should have >80% acceptance
            # Increase weight on components that correlate with acceptance
            adjustments['confidence'] = 0.01  # Small increase
            adjustments['frequency'] = 0.01
        
        if acceptance_rates.get('low', 0.0) > 0.3:
            # Low quality patterns should have <30% acceptance
            # Decrease weight on components that don't predict rejection
            adjustments['temporal'] = -0.01
            adjustments['relationship'] = -0.01
        
        # Apply adjustments (with normalization)
        if adjustments:
            for component, adjustment in adjustments.items():
                if component in self.quality_weights:
                    self.quality_weights[component] += adjustment
            
            # Normalize weights to sum to 1.0
            total = sum(self.quality_weights.values())
            if total > 0:
                for component in self.quality_weights:
                    self.quality_weights[component] /= total
        
        self.calibration_stats['calibrations_performed'] += 1
        self.calibration_stats['last_calibration'] = datetime.now(timezone.utc).isoformat()
        
        return {
            'acceptance_rates': acceptance_rates,
            'weight_adjustments': adjustments,
            'new_weights': self.quality_weights.copy()
        }
    
    def get_acceptance_rate_by_quality(self) -> dict[str, float]:
        """Get acceptance rate grouped by quality tier"""
        quality_ranges = {
            'high': [p for p in self.acceptance_history if p['quality_score'] >= 0.75],
            'medium': [p for p in self.acceptance_history if 0.5 <= p['quality_score'] < 0.75],
            'low': [p for p in self.acceptance_history if p['quality_score'] < 0.5]
        }
        
        rates = {}
        for tier, patterns in quality_ranges.items():
            if patterns:
                rates[tier] = sum(p['accepted'] for p in patterns) / len(patterns)
            else:
                rates[tier] = 0.0
        
        return rates
    
    def get_calibration_stats(self) -> dict[str, Any]:
        """Get calibration statistics"""
        return {
            **self.calibration_stats,
            'current_weights': self.quality_weights.copy(),
            'acceptance_rates': self.get_acceptance_rate_by_quality(),
            'total_samples': len(self.acceptance_history)
        }


class ErrorDrivenQualityCalibrator:
    """
    Error-driven learning for quality score calibration.
    
    Adjusts quality score components based on prediction errors.
    """
    
    def __init__(self, learning_rate: float = 0.01):
        """
        Initialize error-driven calibrator.
        
        Args:
            learning_rate: Learning rate for weight adjustments
        """
        self.learning_rate = learning_rate
        self.error_history: list[dict[str, Any]] = []
        self.weight_adjustments = {
            'confidence': 0.0,
            'frequency': 0.0,
            'temporal': 0.0,
            'relationship': 0.0
        }
    
    def calculate_error(
        self,
        predicted_quality: float,
        actual_acceptance: bool
    ) -> float:
        """
        Calculate prediction error.
        
        Args:
            predicted_quality: Predicted quality score (0.0-1.0)
            actual_acceptance: True if user accepted, False if rejected
        
        Returns:
            Error value (predicted - actual)
        """
        # Actual quality = 1.0 if accepted, 0.0 if rejected
        actual_quality = 1.0 if actual_acceptance else 0.0
        error = predicted_quality - actual_quality
        
        return error
    
    def update_weights(
        self,
        pattern: dict[str, Any],
        error: float,
        component_values: dict[str, float] | None = None
    ) -> dict[str, float]:
        """
        Update component weights based on error.
        
        Args:
            pattern: Pattern dictionary
            error: Prediction error
            component_values: Optional component values (if not provided, extracted from pattern)
        
        Returns:
            Updated weight adjustments
        """
        # Extract component values if not provided
        if component_values is None:
            component_values = {
                'confidence': pattern.get('confidence', 0.0),
                'frequency': self._extract_frequency_score(pattern),
                'temporal': self._extract_temporal_score(pattern),
                'relationship': self._extract_relationship_score(pattern)
            }
        
        # Gradient descent: adjust weights to reduce error
        for component in ['confidence', 'frequency', 'temporal', 'relationship']:
            component_value = component_values.get(component, 0.0)
            # Gradient = error * component_value
            gradient = error * component_value
            adjustment = -self.learning_rate * gradient
            self.weight_adjustments[component] += adjustment
        
        # Store error in history
        self.error_history.append({
            'error': error,
            'component_values': component_values.copy(),
            'timestamp': datetime.now(timezone.utc)
        })
        
        return self.weight_adjustments.copy()
    
    def _extract_frequency_score(self, pattern: dict[str, Any]) -> float:
        """Extract frequency score from pattern"""
        occurrences = pattern.get('occurrences', pattern.get('count', 0))
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
    
    def _extract_temporal_score(self, pattern: dict[str, Any]) -> float:
        """Extract temporal score from pattern"""
        pattern_type = pattern.get('pattern_type', '')
        if pattern_type == 'time_of_day':
            return 0.9
        elif pattern_type == 'co_occurrence':
            return 0.8
        return 0.5
    
    def _extract_relationship_score(self, pattern: dict[str, Any]) -> float:
        """Extract relationship score from pattern"""
        area1 = pattern.get('area1', pattern.get('area', ''))
        area2 = pattern.get('area2', '')
        if area1 and area2 and area1 == area2:
            return 0.5
        return 0.3
    
    def get_average_error(self, window: int = 10) -> float:
        """Get average error over last N samples"""
        if not self.error_history:
            return 0.0
        
        recent_errors = [e['error'] for e in self.error_history[-window:]]
        return statistics.mean(recent_errors) if recent_errors else 0.0
    
    def get_weight_adjustments(self) -> dict[str, float]:
        """Get current weight adjustments"""
        return self.weight_adjustments.copy()

