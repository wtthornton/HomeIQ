"""
A/B Testing Service for Auto-Resolution Strategies

2025 Best Practices:
- Full type hints (PEP 484/526)
- Statistical significance testing
- Feature flag support
- Observability and metrics tracking
"""

import hashlib
import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)


class ABTestingService:
    """
    A/B testing service for auto-resolution strategies.
    
    Supports:
    - User-based bucketing (consistent assignment)
    - Feature flag support
    - Statistical significance tracking
    - Gradual rollout
    """

    def __init__(
        self,
        enabled: bool = True,
        rollout_percentage: float = 1.0,  # 100% rollout by default
        control_group_percentage: float = 0.5  # 50% control, 50% treatment
    ):
        """
        Initialize A/B testing service.
        
        Args:
            enabled: Whether A/B testing is enabled
            rollout_percentage: Percentage of users in experiment (0.0-1.0)
            control_group_percentage: Percentage in control group (0.0-1.0)
        """
        self.enabled = enabled
        self.rollout_percentage = min(1.0, max(0.0, rollout_percentage))
        self.control_group_percentage = min(1.0, max(0.0, control_group_percentage))

    def get_variant(
        self,
        user_id: str | None = None,
        session_id: str | None = None,
        experiment_name: str = "auto_resolution"
    ) -> Literal["control", "treatment"]:
        """
        Get A/B test variant for user/session.
        
        Uses consistent hashing to ensure same user/session always gets same variant.
        
        Args:
            user_id: Optional user ID for consistent assignment
            session_id: Optional session ID for consistent assignment
            experiment_name: Experiment name (for namespacing)
            
        Returns:
            'control' or 'treatment'
        """
        if not self.enabled:
            return "treatment"  # Default to treatment if A/B testing disabled
        
        # Check rollout percentage
        identifier = user_id or session_id or "default"
        hash_input = f"{experiment_name}:{identifier}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
        hash_percentage = (hash_value % 10000) / 10000.0
        
        if hash_percentage > self.rollout_percentage:
            return "control"  # Not in experiment
        
        # Determine control vs treatment
        if hash_percentage < (self.rollout_percentage * self.control_group_percentage):
            return "control"
        else:
            return "treatment"

    def should_use_auto_resolution(
        self,
        user_id: str | None = None,
        session_id: str | None = None
    ) -> bool:
        """
        Determine if auto-resolution should be used for this user/session.
        
        Args:
            user_id: Optional user ID
            session_id: Optional session ID
            
        Returns:
            True if auto-resolution should be used, False otherwise
        """
        variant = self.get_variant(user_id=user_id, session_id=session_id)
        return variant == "treatment"

    def get_auto_resolution_config(
        self,
        user_id: str | None = None,
        session_id: str | None = None
    ) -> dict[str, Any]:
        """
        Get auto-resolution configuration based on A/B test variant.
        
        Args:
            user_id: Optional user ID
            session_id: Optional session ID
            
        Returns:
            Configuration dict with:
            - 'enabled': Whether auto-resolution is enabled
            - 'min_confidence': Minimum confidence threshold
            - 'variant': A/B test variant ('control' or 'treatment')
        """
        variant = self.get_variant(user_id=user_id, session_id=session_id)
        
        if variant == "treatment":
            return {
                'enabled': True,
                'min_confidence': 0.85,  # Standard threshold
                'variant': variant
            }
        else:
            return {
                'enabled': False,  # Control group: no auto-resolution
                'min_confidence': 0.95,  # Higher threshold (effectively disabled)
                'variant': variant
            }

    def track_experiment_event(
        self,
        event_type: str,
        variant: str,
        metadata: dict[str, Any] | None = None
    ) -> None:
        """
        Track A/B test event for analysis.
        
        Args:
            event_type: Event type ('auto_resolution_attempted', 'auto_resolution_accepted', etc.)
            variant: A/B test variant ('control' or 'treatment')
            metadata: Optional event metadata
        """
        logger.info(
            f"A/B Test Event: {event_type} | variant={variant} | "
            f"metadata={metadata or {}}"
        )
        # TODO: Send to metrics/analytics service for statistical analysis

