"""
Reinforcement Learning from Human Feedback (RLHF) for Pattern Quality

Epic 39, Story 39.7: Pattern Learning & RLHF Migration
Trains reward model based on user feedback to improve pattern/synergy detection.
"""

import logging
from typing import Any
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class PatternRLHF:
    """
    RLHF for pattern quality improvement.
    
    Reward Model:
    - User accepts suggestion: +1.0
    - User rejects suggestion: -0.5
    - User modifies suggestion: +0.3
    - Suggestion deployed successfully: +0.8
    - Suggestion disabled: -0.7
    
    Epic 39, Story 39.7: Extracted to pattern service.
    """
    
    def __init__(self):
        self.reward_model: dict[str, Any] | None = None
        self.policy_model: dict[str, Any] | None = None
        self.feedback_history: list[dict[str, Any]] = []
        self.reward_statistics = {
            'total_feedback': 0,
            'accept_count': 0,
            'reject_count': 0,
            'modify_count': 0,
            'deploy_count': 0,
            'disable_count': 0
        }
    
    def calculate_reward(self, pattern: dict[str, Any], user_action: str) -> float:
        """
        Calculate reward based on user action.
        
        Args:
            pattern: Pattern dictionary
            user_action: User action ('accept', 'reject', 'modify', 'deploy', 'disable')
        
        Returns:
            Reward value
        """
        rewards = {
            'accept': 1.0,
            'reject': -0.5,
            'modify': 0.3,
            'deploy': 0.8,
            'disable': -0.7
        }
        
        reward = rewards.get(user_action, 0.0)
        
        # Store feedback
        self.feedback_history.append({
            'pattern': pattern,
            'user_action': user_action,
            'reward': reward,
            'timestamp': datetime.now(timezone.utc)
        })
        
        # Update statistics
        self.reward_statistics['total_feedback'] += 1
        if user_action == 'accept':
            self.reward_statistics['accept_count'] += 1
        elif user_action == 'reject':
            self.reward_statistics['reject_count'] += 1
        elif user_action == 'modify':
            self.reward_statistics['modify_count'] += 1
        elif user_action == 'deploy':
            self.reward_statistics['deploy_count'] += 1
        elif user_action == 'disable':
            self.reward_statistics['disable_count'] += 1
        
        return reward
    
    def update_quality_weights(
        self,
        pattern: dict[str, Any],
        reward: float,
        current_weights: dict[str, float]
    ) -> dict[str, float]:
        """
        Update quality score weights based on reward.
        
        Args:
            pattern: Pattern dictionary
            reward: Reward value
            current_weights: Current quality weights
        
        Returns:
            Updated weights
        """
        # Simple policy gradient: adjust weights to maximize reward
        # Positive reward: increase weights for components with high values
        # Negative reward: decrease weights for components with high values
        
        updated_weights = current_weights.copy()
        
        # Extract component values
        component_values = {
            'confidence': pattern.get('confidence', 0.0),
            'frequency': self._extract_frequency(pattern),
            'temporal': self._extract_temporal(pattern),
            'relationship': self._extract_relationship(pattern)
        }
        
        # Adjust weights based on reward and component values
        learning_rate = 0.01
        for component, weight in updated_weights.items():
            component_value = component_values.get(component, 0.0)
            # Positive reward: increase weight if component is strong
            # Negative reward: decrease weight if component is strong
            adjustment = learning_rate * reward * component_value
            updated_weights[component] = max(0.0, min(1.0, weight + adjustment))
        
        # Normalize weights to sum to 1.0
        total = sum(updated_weights.values())
        if total > 0:
            for component in updated_weights:
                updated_weights[component] /= total
        
        return updated_weights
    
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
    
    def get_average_reward(self, window: int = 10) -> float:
        """Get average reward over last N samples"""
        if not self.feedback_history:
            return 0.0
        
        recent_rewards = [f['reward'] for f in self.feedback_history[-window:]]
        return sum(recent_rewards) / len(recent_rewards) if recent_rewards else 0.0
    
    def get_reward_statistics(self) -> dict[str, Any]:
        """Get reward statistics"""
        return {
            **self.reward_statistics,
            'average_reward': self.get_average_reward(),
            'total_samples': len(self.feedback_history)
        }

