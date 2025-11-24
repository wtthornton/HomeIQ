"""
Reinforcement Learning Optimizer for Synergy Recommendations

Uses Multi-Armed Bandit (Thompson Sampling) to learn from user feedback and
optimize synergy recommendations. Adapts to user preferences over time.

2025 Best Practice: RL-based recommendation systems show 20-30% improvement
in user satisfaction through personalization.
"""

import asyncio
import logging
from collections import defaultdict
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


class RLSynergyOptimizer:
    """
    Reinforcement Learning optimizer for synergy recommendations.
    
    Approach: Multi-Armed Bandit (Thompson Sampling)
    - State: User context, device state, time
    - Action: Recommend synergy
    - Reward: User acceptance, automation success, energy savings
    """
    
    def __init__(self):
        """
        Initialize RL optimizer.
        
        2025 Improvement: Thread-safe for async/concurrent access.
        """
        # Track success/failure for each synergy type and specific synergies
        self.synergy_stats = defaultdict(lambda: {
            'successes': 1,  # Prior: start with 1 success (optimistic)
            'failures': 1,   # Prior: start with 1 failure (realistic)
            'total_reward': 0.0,
            'recommendation_count': 0
        })
        # Thread-safety for concurrent updates (2025 improvement)
        self._lock = asyncio.Lock()
        
        logger.info("RLSynergyOptimizer initialized (Thompson Sampling, thread-safe)")
    
    async def update_from_feedback(
        self,
        synergy_id: str,
        feedback: dict[str, Any]
    ) -> None:
        """
        Update model from user feedback (thread-safe).
        
        Args:
            synergy_id: Synergy that was recommended
            feedback: {
                'accepted': bool,
                'deployed': bool,
                'usage_count': int,
                'user_rating': float (0-5),
                'energy_saved': float (kWh),
                'user_id': str (optional, for personalization)
            }
        """
        # Input validation (2025 improvement)
        if not isinstance(synergy_id, str) or not synergy_id:
            raise ValueError("synergy_id must be a non-empty string")
        if not isinstance(feedback, dict):
            raise ValueError("feedback must be a dictionary")
        
        async with self._lock:
            stats = self.synergy_stats[synergy_id]
            stats['recommendation_count'] += 1
            
            if feedback.get('accepted', False):
                stats['successes'] += 1
                
                # Calculate reward (0.0-1.0) with validation
                user_rating = feedback.get('user_rating', 3)
                if not 0.0 <= user_rating <= 5.0:
                    logger.warning(
                        f"Invalid user_rating {user_rating} for {synergy_id}, clamping to [0, 5]"
                    )
                    user_rating = max(0.0, min(5.0, user_rating))
                
                reward = (
                    user_rating / 5.0 * 0.5 +  # User satisfaction (50%)
                    (1.0 if feedback.get('deployed') else 0.0) * 0.3 +  # Deployment (30%)
                    min(feedback.get('usage_count', 0) / 100.0, 1.0) * 0.2  # Usage (20%)
                )
                
                stats['total_reward'] += reward
                
                logger.debug(
                    f"Synergy {synergy_id[:20]}...: SUCCESS "
                    f"(reward={reward:.3f}, total_reward={stats['total_reward']:.3f}, "
                    f"count={stats['recommendation_count']})"
                )
            else:
                stats['failures'] += 1
                logger.debug(
                    f"Synergy {synergy_id[:20]}...: FAILURE "
                    f"(successes={stats['successes']}, failures={stats['failures']}, "
                    f"count={stats['recommendation_count']})"
                )
    
    async def get_optimized_score(self, synergy: dict) -> float:
        """
        Get RL-optimized score for synergy (thread-safe).
        
        Uses Thompson Sampling to balance exploration vs exploitation.
        
        Args:
            synergy: Synergy opportunity dictionary
        
        Returns:
            Optimized score (0.0-1.0)
        """
        # Input validation (2025 improvement)
        if not isinstance(synergy, dict):
            raise ValueError("synergy must be a dictionary")
        
        synergy_id = synergy.get('synergy_id', 'unknown')
        
        # Thread-safe read
        async with self._lock:
            stats = self.synergy_stats[synergy_id]
        
        # Thompson Sampling: Sample from Beta distribution
        # Beta(alpha, beta) where alpha = successes, beta = failures
        alpha = stats['successes']
        beta = stats['failures']
        
        # Validate parameters
        if alpha <= 0 or beta <= 0:
            logger.warning(
                f"Invalid Beta parameters for {synergy_id}: alpha={alpha}, beta={beta}, "
                "using default score"
            )
            sampled_score = 0.5
        else:
            try:
                sampled_score = np.random.beta(alpha, beta)
            except (ValueError, RuntimeError) as e:
                logger.warning(
                    f"Beta sampling failed for {synergy_id} (alpha={alpha}, beta={beta}): {e}, "
                    "using default",
                    exc_info=True
                )
                sampled_score = 0.5
        
        # Combine with base score (weighted average)
        base_score = synergy.get('impact_score', 0.5)
        # Validate base score
        if not 0.0 <= base_score <= 1.0:
            logger.warning(
                f"Invalid base_score {base_score} for {synergy_id}, clamping to [0.0, 1.0]"
            )
            base_score = max(0.0, min(1.0, base_score))
        
        # Weight: More weight to RL score if we have more data
        recommendation_count = stats['recommendation_count']
        if recommendation_count > 10:
            # High confidence: 70% RL, 30% base
            rl_weight = 0.7
        elif recommendation_count > 5:
            # Medium confidence: 50% RL, 50% base
            rl_weight = 0.5
        else:
            # Low confidence: 30% RL, 70% base
            rl_weight = 0.3
        
        optimized_score = base_score * (1 - rl_weight) + sampled_score * rl_weight
        # Clamp to valid range
        optimized_score = max(0.0, min(1.0, optimized_score))
        
        # Store RL adjustment for explainability
        synergy['rl_adjustment'] = {
            'base_score': base_score,
            'rl_score': sampled_score,
            'optimized_score': optimized_score,
            'rl_weight': rl_weight,
            'recommendation_count': recommendation_count,
            'success_rate': alpha / (alpha + beta) if (alpha + beta) > 0 else 0.5
        }
        
        return optimized_score
    
    def get_statistics(self) -> dict[str, Any]:
        """
        Get RL optimizer statistics.
        
        Returns:
            Statistics dictionary
        """
        total_synergies = len(self.synergy_stats)
        total_recommendations = sum(s['recommendation_count'] for s in self.synergy_stats.values())
        total_successes = sum(s['successes'] - 1 for s in self.synergy_stats.values())  # Subtract prior
        total_failures = sum(s['failures'] - 1 for s in self.synergy_stats.values())  # Subtract prior
        
        overall_success_rate = (
            total_successes / (total_successes + total_failures)
            if (total_successes + total_failures) > 0 else 0.0
        )
        
        return {
            'total_synergies_tracked': total_synergies,
            'total_recommendations': total_recommendations,
            'total_successes': total_successes,
            'total_failures': total_failures,
            'overall_success_rate': overall_success_rate,
            'avg_recommendations_per_synergy': (
                total_recommendations / total_synergies if total_synergies > 0 else 0
            )
        }
    
    def get_top_performing_synergies(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        Get top performing synergies based on RL statistics.
        
        Args:
            limit: Number of top synergies to return
        
        Returns:
            List of synergy statistics
        """
        performance_scores = []
        
        for synergy_id, stats in self.synergy_stats.items():
            if stats['recommendation_count'] < 3:  # Need at least 3 recommendations
                continue
            
            alpha = stats['successes']
            beta = stats['failures']
            success_rate = alpha / (alpha + beta) if (alpha + beta) > 0 else 0.0
            
            # Performance score: success rate weighted by recommendation count
            performance_score = success_rate * min(stats['recommendation_count'] / 20.0, 1.0)
            
            performance_scores.append({
                'synergy_id': synergy_id,
                'success_rate': success_rate,
                'recommendation_count': stats['recommendation_count'],
                'total_reward': stats['total_reward'],
                'performance_score': performance_score
            })
        
        # Sort by performance score
        performance_scores.sort(key=lambda x: x['performance_score'], reverse=True)
        
        return performance_scores[:limit]

