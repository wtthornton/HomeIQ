"""
Kill Switch

Epic G3: Global pause for non-safety automations
"""

import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger(__name__)

# Huey task queue (optional, imported if available)
try:
    from ..queue.huey_config import huey
    from ..queue.scheduler import get_scheduler
    HUEY_AVAILABLE = True
except ImportError:
    HUEY_AVAILABLE = False
    huey = None
    get_scheduler = None


class KillSwitch:
    """
    Kill switch for pausing automations.
    
    Features:
    - Global pause for non-safety automations
    - Per-home pause
    - Emergency stop mechanism
    - Task queue integration (revoke queued tasks)
    """
    
    def __init__(self):
        """Initialize kill switch"""
        self.global_paused: bool = False
        self.paused_homes: Set[str] = set()
        self.paused_specs: Set[str] = set()
    
    def pause_global(self):
        """Pause all non-safety automations globally"""
        self.global_paused = True
        logger.warning("Global kill switch activated - all non-safety automations paused")
        
        # Revoke queued tasks if Huey is available
        if HUEY_AVAILABLE and huey:
            try:
                # Revoke all pending tasks (except high-risk ones)
                pending_tasks = huey.pending()
                revoked_count = 0
                
                for task_id in pending_tasks:
                    try:
                        # Note: We can't check spec from task_id directly
                        # For now, revoke all pending tasks
                        # In production, we'd need to store task metadata
                        huey.revoke(task_id, revoke_once=False)
                        revoked_count += 1
                    except Exception as e:
                        logger.warning(f"Failed to revoke task {task_id}: {e}")
                
                if revoked_count > 0:
                    logger.info(f"Revoked {revoked_count} queued tasks due to kill switch")
                    
            except Exception as e:
                logger.error(f"Error revoking tasks on kill switch activation: {e}", exc_info=True)
    
    def resume_global(self):
        """Resume all automations globally"""
        self.global_paused = False
        logger.info("Global kill switch deactivated - automations resumed")
    
    def pause_home(self, home_id: str):
        """Pause automations for a specific home"""
        self.paused_homes.add(home_id)
        logger.warning(f"Kill switch activated for home {home_id}")
    
    def resume_home(self, home_id: str):
        """Resume automations for a specific home"""
        self.paused_homes.discard(home_id)
        logger.info(f"Kill switch deactivated for home {home_id}")
    
    def pause_spec(self, spec_id: str):
        """Pause a specific spec"""
        self.paused_specs.add(spec_id)
        logger.warning(f"Kill switch activated for spec {spec_id}")
        
        # Revoke scheduled tasks for this spec if Huey is available
        if HUEY_AVAILABLE:
            try:
                scheduler = get_scheduler()
                if scheduler:
                    scheduler.unregister_scheduled_automation(spec_id)
                    logger.info(f"Unregistered scheduled automation for spec {spec_id}")
            except Exception as e:
                logger.warning(f"Failed to unregister schedule for {spec_id}: {e}")
    
    def resume_spec(self, spec_id: str):
        """Resume a specific spec"""
        self.paused_specs.discard(spec_id)
        logger.info(f"Kill switch deactivated for spec {spec_id}")
    
    def is_allowed(
        self,
        spec: Dict,
        home_id: str
    ) -> tuple[bool, Optional[str]]:
        """
        Check if automation is allowed to execute.
        
        Args:
            spec: Automation spec dictionary
            home_id: Home ID
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        spec_id = spec.get("id", "unknown")
        policy = spec.get("policy", {})
        risk = policy.get("risk", "low")
        
        # Safety automations (high risk) are never paused
        if risk == "high":
            return True, None
        
        # Check global pause
        if self.global_paused:
            return False, "Global kill switch is active"
        
        # Check home pause
        if home_id in self.paused_homes:
            return False, f"Kill switch is active for home {home_id}"
        
        # Check spec pause
        if spec_id in self.paused_specs:
            return False, f"Kill switch is active for spec {spec_id}"
        
        return True, None
    
    def get_status(self) -> Dict[str, Any]:
        """Get kill switch status"""
        return {
            "global_paused": self.global_paused,
            "paused_homes": list(self.paused_homes),
            "paused_specs": list(self.paused_specs)
        }
