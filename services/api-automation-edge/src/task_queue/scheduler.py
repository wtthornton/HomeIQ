"""
Cron-Based Scheduling

Register periodic tasks from automation specs with schedule triggers.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from huey import crontab
from huey.contrib.sqlitedb import SqliteHuey

from ..registry.spec_registry import SpecRegistry
from ..config import settings

logger = logging.getLogger(__name__)

# Huey instance
try:
    from .huey_config import huey
    HUEY_AVAILABLE = True
except ImportError:
    HUEY_AVAILABLE = False
    huey = None


def parse_cron_to_crontab(cron_expr: str) -> crontab:
    """
    Parse cron expression to Huey crontab.
    
    Supports standard cron format: "minute hour day month day_of_week"
    Example: "0 7 * * *" (7 AM daily)
    
    Args:
        cron_expr: Cron expression string
    
    Returns:
        Huey crontab object
    """
    # Split cron expression
    parts = cron_expr.strip().split()
    if len(parts) != 5:
        raise ValueError(f"Invalid cron expression: {cron_expr}. Expected 5 fields.")
    
    minute, hour, day, month, day_of_week = parts
    
    # Parse each field
    # Huey crontab accepts: minute, hour, day, month, day_of_week
    # All can be: *, */n, n, n-m, n,m, or specific values
    
    return crontab(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week
    )


class AutomationScheduler:
    """
    Scheduler for registering periodic automation tasks from specs.
    """
    
    def __init__(
        self,
        spec_registry: Optional[SpecRegistry] = None,
        huey_instance: Optional[SqliteHuey] = None
    ):
        """
        Initialize automation scheduler.
        
        Args:
            spec_registry: Spec registry instance
            huey_instance: Huey instance (defaults to global)
        """
        if not HUEY_AVAILABLE or not huey:
            raise RuntimeError("Huey not available - scheduler requires Huey")
        
        self.spec_registry = spec_registry or SpecRegistry(settings.database_url)
        self.huey = huey_instance or huey
        self.registered_schedules: Dict[str, str] = {}  # spec_id -> job_id
    
    def register_scheduled_automation(
        self,
        spec_id: str,
        home_id: str,
        cron_expr: str
    ) -> str:
        """
        Register a periodic automation task.
        
        Args:
            spec_id: Automation spec ID
            home_id: Home ID
            cron_expr: Cron expression (e.g., "0 7 * * *")
        
        Returns:
            Job ID for the periodic task
        """
        if not HUEY_AVAILABLE:
            raise RuntimeError("Huey not available")
        
        try:
            # Parse cron expression
            cron = parse_cron_to_crontab(cron_expr)
            
            # Get spec for task configuration
            spec = self.spec_registry.get_spec(spec_id, home_id)
            
            # Import task function (avoid circular import)
            from .tasks import execute_automation_task
            from functools import partial
            
            # Register periodic task
            job_id = f"schedule_{spec_id}_{home_id}"
            
            # Create periodic task wrapper function
            # Note: Huey periodic tasks need unique function names
            # We'll create a closure to capture the spec parameters
            def create_periodic_task_wrapper(spec_id_inner, home_id_inner, spec_inner):
                """Create a periodic task wrapper function"""
                @self.huey.periodic_task(cron, name=f"Automation: {spec_id_inner}")
                def scheduled_automation():
                    """Periodic task wrapper - executed on schedule"""
                    correlation_id = f"scheduled_{spec_id_inner}_{home_id_inner}_{int(time.time())}"
                    logger.info(f"Executing scheduled automation: spec_id={spec_id_inner}, correlation_id={correlation_id}")
                    
                    # Execute automation task
                    execute_automation_task(
                        spec_id=spec_id_inner,
                        trigger_data={"type": "schedule"},
                        home_id=home_id_inner,
                        correlation_id=correlation_id,
                        spec=spec_inner
                    )
                
                return scheduled_automation
            
            # Create and register periodic task
            periodic_task = create_periodic_task_wrapper(spec_id, home_id, spec)
            
            # Store job ID (mapping spec_id to job_id)
            self.registered_schedules[spec_id] = job_id
            
            logger.info(
                f"Registered scheduled automation: spec_id={spec_id}, "
                f"cron={cron_expr}, job_id={job_id}"
            )
            
            return job_id
            
        except Exception as e:
            logger.error(
                f"Failed to register scheduled automation {spec_id}: {e}",
                exc_info=True
            )
            raise
    
    def unregister_scheduled_automation(
        self,
        spec_id: str
    ) -> bool:
        """
        Unregister a periodic automation task.
        
        Args:
            spec_id: Automation spec ID
        
        Returns:
            True if unregistered, False if not found
        """
        if not HUEY_AVAILABLE:
            return False
        
        job_id = self.registered_schedules.get(spec_id)
        if not job_id:
            return False
        
        try:
            # Revoke periodic task
            self.huey.revoke(job_id, revoke_once=False)
            del self.registered_schedules[spec_id]
            
            logger.info(f"Unregistered scheduled automation: spec_id={spec_id}")
            return True
            
        except Exception as e:
            logger.error(
                f"Failed to unregister scheduled automation {spec_id}: {e}",
                exc_info=True
            )
            return False
    
    def load_scheduled_automations(self, home_id: str = None):
        """
        Load and register all scheduled automations from specs.
        
        Args:
            home_id: Optional home ID filter (defaults to settings.home_id)
        """
        if not HUEY_AVAILABLE:
            logger.warning("Huey not available - skipping schedule load")
            return
        
        home_id = home_id or settings.home_id
        
        try:
            # Get all active specs
            # Note: This would need a method to list all specs
            # For now, we'll register schedules on spec deployment
            
            logger.info(f"Loaded scheduled automations for home {home_id}")
            
        except Exception as e:
            logger.error(
                f"Failed to load scheduled automations: {e}",
                exc_info=True
            )
    
    def get_schedule_status(self, spec_id: str) -> Optional[Dict[str, Any]]:
        """
        Get schedule status for an automation.
        
        Args:
            spec_id: Automation spec ID
        
        Returns:
            Schedule status dictionary or None if not scheduled
        """
        job_id = self.registered_schedules.get(spec_id)
        if not job_id:
            return None
        
        try:
            # Get job from Huey (if available)
            # Note: Huey doesn't have direct job status query
            # We'll track this ourselves
            
            return {
                "spec_id": spec_id,
                "job_id": job_id,
                "enabled": True  # Would track enabled/disabled state
            }
            
        except Exception as e:
            logger.warning(f"Failed to get schedule status for {spec_id}: {e}")
            return None


# Global scheduler instance
_scheduler: Optional[AutomationScheduler] = None


def get_scheduler() -> Optional[AutomationScheduler]:
    """Get or create global scheduler instance"""
    global _scheduler
    
    if not HUEY_AVAILABLE:
        return None
    
    if _scheduler is None:
        try:
            _scheduler = AutomationScheduler()
        except Exception as e:
            logger.error(f"Failed to create scheduler: {e}", exc_info=True)
            return None
    
    return _scheduler
