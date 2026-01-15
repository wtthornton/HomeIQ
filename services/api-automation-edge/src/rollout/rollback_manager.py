"""
Rollback Manager

Epic G2: Last-known-good pointer and auto-rollback
"""

import logging
from typing import Any, Dict, List, Optional

from ..registry.spec_registry import SpecRegistry

logger = logging.getLogger(__name__)


class RollbackManager:
    """
    Manages rollbacks for automation specs.
    
    Features:
    - Last-known-good pointer per home
    - Auto-rollback on error budget breach
    - One-click rollback API
    """
    
    def __init__(self, spec_registry: SpecRegistry):
        """
        Initialize rollback manager.
        
        Args:
            spec_registry: SpecRegistry instance
        """
        self.spec_registry = spec_registry
        # Track last known good: (home_id, spec_id) -> version
        self.last_known_good: Dict[tuple[str, str], str] = {}
        # Track error budgets: (home_id, spec_id) -> error_count
        self.error_budgets: Dict[tuple[str, str], Dict[str, Any]] = {}
    
    def set_last_known_good(
        self,
        home_id: str,
        spec_id: str,
        version: str
    ):
        """
        Set last known good version.
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
            version: Version to mark as last known good
        """
        key = (home_id, spec_id)
        self.last_known_good[key] = version
        logger.info(f"Set last known good for {spec_id}@{home_id}: {version}")
    
    def get_last_known_good(
        self,
        home_id: str,
        spec_id: str
    ) -> Optional[str]:
        """
        Get last known good version.
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
        
        Returns:
            Version string or None
        """
        key = (home_id, spec_id)
        return self.last_known_good.get(key)
    
    def record_error(
        self,
        home_id: str,
        spec_id: str
    ):
        """
        Record error for error budget tracking.
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
        """
        key = (home_id, spec_id)
        
        if key not in self.error_budgets:
            self.error_budgets[key] = {
                "error_count": 0,
                "window_start": None,
                "max_errors": 10,  # Default: 10 errors per window
                "window_seconds": 300  # Default: 5 minutes
            }
        
        budget = self.error_budgets[key]
        budget["error_count"] += 1
        
        logger.debug(
            f"Recorded error for {spec_id}@{home_id}: "
            f"{budget['error_count']}/{budget['max_errors']}"
        )
    
    def check_error_budget_breach(
        self,
        home_id: str,
        spec_id: str
    ) -> bool:
        """
        Check if error budget breached (should rollback).
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
        
        Returns:
            True if error budget breached
        """
        key = (home_id, spec_id)
        
        if key not in self.error_budgets:
            return False
        
        budget = self.error_budgets[key]
        
        # Reset window if needed (simplified - would need proper time tracking)
        # For now, just check count
        if budget["error_count"] >= budget["max_errors"]:
            logger.warning(
                f"Error budget breached for {spec_id}@{home_id}: "
                f"{budget['error_count']} errors"
            )
            return True
        
        return False
    
    async def rollback(
        self,
        home_id: str,
        spec_id: str,
        target_version: Optional[str] = None
    ) -> bool:
        """
        Rollback to last known good or specified version.
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
            target_version: Optional target version (defaults to last known good)
        
        Returns:
            True if rollback successful
        """
        if not target_version:
            target_version = self.get_last_known_good(home_id, spec_id)
        
        if not target_version:
            logger.error(f"No last known good version for {spec_id}@{home_id}")
            return False
        
        # Deploy target version
        success = self.spec_registry.deploy_spec(spec_id, home_id, target_version)
        
        if success:
            logger.info(
                f"Rolled back {spec_id}@{home_id} to version {target_version}"
            )
            
            # Reset error budget
            key = (home_id, spec_id)
            if key in self.error_budgets:
                self.error_budgets[key]["error_count"] = 0
        else:
            logger.error(f"Failed to rollback {spec_id}@{home_id}")
        
        return success
    
    async def auto_rollback_if_needed(
        self,
        home_id: str,
        spec_id: str
    ) -> bool:
        """
        Auto-rollback if error budget breached.
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
        
        Returns:
            True if rollback occurred
        """
        if self.check_error_budget_breach(home_id, spec_id):
            return await self.rollback(home_id, spec_id)
        return False
