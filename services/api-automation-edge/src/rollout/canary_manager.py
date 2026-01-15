"""
Canary Rollout Manager

Epic G1: Staged deploys by home cohort with health gates
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class CanaryManager:
    """
    Manages canary rollouts for automation specs.
    
    Features:
    - Staged deploys by home cohort
    - Health gate checks (error rate, latency)
    - Gradual rollout percentage
    """
    
    def __init__(self):
        """Initialize canary manager"""
        # Track rollouts: spec_id -> rollout_state
        self.rollouts: Dict[str, Dict[str, Any]] = {}
    
    def start_canary(
        self,
        spec_id: str,
        spec_version: str,
        home_cohorts: List[str],
        rollout_percentage: float = 10.0
    ) -> Dict[str, Any]:
        """
        Start canary rollout.
        
        Args:
            spec_id: Spec ID
            spec_version: Spec version
            home_cohorts: List of home IDs in canary cohort
            rollout_percentage: Initial rollout percentage (0-100)
        
        Returns:
            Rollout state dictionary
        """
        rollout_state = {
            "spec_id": spec_id,
            "spec_version": spec_version,
            "home_cohorts": home_cohorts,
            "rollout_percentage": rollout_percentage,
            "status": "canary",
            "health_metrics": {
                "error_rate": 0.0,
                "avg_latency": 0.0,
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0
            }
        }
        
        self.rollouts[spec_id] = rollout_state
        
        logger.info(
            f"Started canary rollout for {spec_id} v{spec_version} "
            f"to {len(home_cohorts)} homes ({rollout_percentage}%)"
        )
        
        return rollout_state
    
    def update_health_metrics(
        self,
        spec_id: str,
        success: bool,
        latency: float
    ):
        """
        Update health metrics for canary.
        
        Args:
            spec_id: Spec ID
            success: Whether execution succeeded
            latency: Execution latency
        """
        if spec_id not in self.rollouts:
            return
        
        rollout = self.rollouts[spec_id]
        metrics = rollout["health_metrics"]
        
        metrics["total_executions"] += 1
        if success:
            metrics["successful_executions"] += 1
        else:
            metrics["failed_executions"] += 1
        
        # Update error rate
        if metrics["total_executions"] > 0:
            metrics["error_rate"] = (
                metrics["failed_executions"] / metrics["total_executions"]
            )
        
        # Update average latency (simple moving average)
        if metrics["total_executions"] == 1:
            metrics["avg_latency"] = latency
        else:
            metrics["avg_latency"] = (
                (metrics["avg_latency"] * (metrics["total_executions"] - 1) + latency) /
                metrics["total_executions"]
            )
    
    def check_health_gates(
        self,
        spec_id: str,
        max_error_rate: float = 0.05,
        max_latency: float = 5.0,
        min_executions: int = 10
    ) -> tuple[bool, Optional[str]]:
        """
        Check health gates for canary.
        
        Args:
            spec_id: Spec ID
            max_error_rate: Maximum allowed error rate (0-1)
            max_latency: Maximum allowed latency in seconds
            min_executions: Minimum executions before checking gates
        
        Returns:
            Tuple of (passes_gates, reason)
        """
        if spec_id not in self.rollouts:
            return True, None
        
        rollout = self.rollouts[spec_id]
        metrics = rollout["health_metrics"]
        
        # Need minimum executions
        if metrics["total_executions"] < min_executions:
            return True, None  # Not enough data yet
        
        # Check error rate
        if metrics["error_rate"] > max_error_rate:
            return False, f"Error rate {metrics['error_rate']:.2%} exceeds threshold {max_error_rate:.2%}"
        
        # Check latency
        if metrics["avg_latency"] > max_latency:
            return False, f"Average latency {metrics['avg_latency']:.2f}s exceeds threshold {max_latency:.2f}s"
        
        return True, None
    
    def promote_canary(
        self,
        spec_id: str,
        new_rollout_percentage: float = 100.0
    ) -> bool:
        """
        Promote canary to next stage.
        
        Args:
            spec_id: Spec ID
            new_rollout_percentage: New rollout percentage
        
        Returns:
            True if promotion successful
        """
        if spec_id not in self.rollouts:
            return False
        
        rollout = self.rollouts[spec_id]
        
        # Check health gates
        passes, reason = self.check_health_gates(spec_id)
        if not passes:
            logger.warning(f"Cannot promote canary for {spec_id}: {reason}")
            return False
        
        # Update rollout percentage
        rollout["rollout_percentage"] = new_rollout_percentage
        
        if new_rollout_percentage >= 100.0:
            rollout["status"] = "complete"
            logger.info(f"Canary rollout complete for {spec_id}")
        else:
            logger.info(
                f"Promoted canary for {spec_id} to {new_rollout_percentage}%"
            )
        
        return True
    
    def get_rollout_state(self, spec_id: str) -> Optional[Dict[str, Any]]:
        """Get rollout state for spec"""
        return self.rollouts.get(spec_id)
