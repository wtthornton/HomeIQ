"""
Weight Optimization Loop

Optimizes quality score component weights using gradient descent.
"""

import logging
from typing import Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class WeightOptimizationLoop:
    """Optimize quality score component weights"""
    
    def __init__(self, learning_rate: float = 0.01):
        """
        Initialize weight optimization loop.
        
        Args:
            learning_rate: Learning rate for gradient descent
        """
        self.learning_rate = learning_rate
        self.weights = {
            'confidence': 0.40,
            'frequency': 0.30,
            'temporal': 0.20,
            'relationship': 0.10
        }
        self.training_history: list[dict[str, Any]] = []
        self.stats = {
            'updates_performed': 0,
            'total_samples': 0
        }
    
    def update_weights(
        self,
        pattern: dict[str, Any],
        actual_acceptance: bool
    ) -> dict[str, Any]:
        """
        Update weights using gradient descent.
        
        Args:
            pattern: Pattern dictionary
            actual_acceptance: True if user accepted, False if rejected
        
        Returns:
            Dictionary with update results
        """
        # Calculate predicted quality
        predicted_quality = self._calculate_quality(pattern)
        
        # Actual quality (1.0 if accepted, 0.0 if rejected)
        actual_quality = 1.0 if actual_acceptance else 0.0
        
        # Calculate error
        error = predicted_quality - actual_quality
        
        # Calculate gradients for each component
        gradients = {}
        component_values = self._extract_component_values(pattern)
        
        for component, weight in self.weights.items():
            component_value = component_values.get(component, 0.0)
            # Gradient = error * component_value
            gradient = error * component_value
            gradients[component] = gradient
        
        # Update weights (gradient descent)
        old_weights = self.weights.copy()
        for component in self.weights:
            self.weights[component] -= self.learning_rate * gradients[component]
        
        # Normalize weights (ensure they sum to 1.0)
        total = sum(self.weights.values())
        if total > 0:
            for component in self.weights:
                self.weights[component] /= total
        
        # Store in history
        self.training_history.append({
            'pattern': pattern,
            'predicted_quality': predicted_quality,
            'actual_quality': actual_quality,
            'error': error,
            'old_weights': old_weights,
            'new_weights': self.weights.copy(),
            'gradients': gradients,
            'timestamp': datetime.now(timezone.utc)
        })
        
        self.stats['updates_performed'] += 1
        self.stats['total_samples'] += 1
        
        return {
            'error': error,
            'old_weights': old_weights,
            'new_weights': self.weights.copy(),
            'gradients': gradients
        }
    
    def _calculate_quality(self, pattern: dict[str, Any]) -> float:
        """Calculate quality score with current weights"""
        component_values = self._extract_component_values(pattern)
        
        quality = sum(
            component_values.get(component, 0.0) * weight
            for component, weight in self.weights.items()
        )
        
        return max(0.0, min(1.0, quality))
    
    def _extract_component_values(self, pattern: dict[str, Any]) -> dict[str, float]:
        """Extract component values from pattern"""
        return {
            'confidence': pattern.get('confidence', 0.0),
            'frequency': self._extract_frequency(pattern),
            'temporal': self._extract_temporal(pattern),
            'relationship': self._extract_relationship(pattern)
        }
    
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
    
    def get_weights(self) -> dict[str, float]:
        """Get current weights"""
        return self.weights.copy()
    
    def get_average_error(self, window: int = 10) -> float:
        """Get average error over last N samples"""
        if not self.training_history:
            return 0.0
        
        recent_errors = [
            abs(h['error']) for h in self.training_history[-window:]
        ]
        return sum(recent_errors) / len(recent_errors) if recent_errors else 0.0
    
    def get_optimization_stats(self) -> dict[str, Any]:
        """Get optimization statistics"""
        return {
            **self.stats,
            'current_weights': self.weights.copy(),
            'average_error': self.get_average_error(),
            'total_samples': len(self.training_history)
        }

