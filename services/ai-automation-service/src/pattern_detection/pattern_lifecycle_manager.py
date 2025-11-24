"""
Pattern Lifecycle Management

Manages pattern lifecycle: creation, validation, deprecation, and deletion.
Automatically handles stale patterns and maintains database health.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import Pattern, PatternHistory

logger = logging.getLogger(__name__)


class PatternLifecycleManager:
    """
    Manage pattern lifecycle: creation, validation, deprecation, deletion.
    
    Handles:
    - Deprecating stale patterns (not seen recently)
    - Deleting very old deprecated patterns
    - Validating active patterns (check if still occurring)
    - Database size management
    """
    
    def __init__(
        self,
        stale_threshold_days: int = 60,
        deletion_threshold_days: int = 90,
        validation_window_days: int = 30
    ):
        """
        Initialize pattern lifecycle manager.
        
        Args:
            stale_threshold_days: Days without activity to mark as stale (default: 60)
            deletion_threshold_days: Days deprecated before deletion (default: 90)
            validation_window_days: Days to check for recent occurrences (default: 30)
        """
        self.stale_threshold_days = stale_threshold_days
        self.deletion_threshold_days = deletion_threshold_days
        self.validation_window_days = validation_window_days
        logger.info(
            f"PatternLifecycleManager initialized: "
            f"stale={stale_threshold_days}d, deletion={deletion_threshold_days}d, "
            f"validation={validation_window_days}d"
        )
    
    async def manage_pattern_lifecycle(self, db: AsyncSession) -> dict[str, Any]:
        """
        Run lifecycle management tasks.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with lifecycle management results:
            {
                'deprecated_count': int,
                'deleted_count': int,
                'needs_review_count': int,
                'active_patterns': int
            }
        """
        now = datetime.now(timezone.utc)
        results = {
            'deprecated_count': 0,
            'deleted_count': 0,
            'needs_review_count': 0,
            'active_patterns': 0
        }
        
        try:
            # 1. Deprecate stale patterns (not seen in stale_threshold_days)
            stale_cutoff = now - timedelta(days=self.stale_threshold_days)
            stale_patterns_query = select(Pattern).where(
                and_(
                    Pattern.last_seen < stale_cutoff,
                    Pattern.deprecated == False  # type: ignore
                )
            )
            stale_result = await db.execute(stale_patterns_query)
            stale_patterns = stale_result.scalars().all()
            
            for pattern in stale_patterns:
                pattern.deprecated = True  # type: ignore
                pattern.deprecated_at = now  # type: ignore
                results['deprecated_count'] += 1
                logger.info(
                    f"Deprecated stale pattern {pattern.id} "
                    f"(type: {pattern.pattern_type}, device: {pattern.device_id}, "
                    f"last seen: {pattern.last_seen})"
                )
            
            # 2. Delete very old deprecated patterns (90+ days deprecated)
            old_deprecated_cutoff = now - timedelta(days=self.deletion_threshold_days)
            delete_query = delete(Pattern).where(
                and_(
                    Pattern.deprecated == True,  # type: ignore
                    Pattern.deprecated_at < old_deprecated_cutoff  # type: ignore
                )
            )
            delete_result = await db.execute(delete_query)
            results['deleted_count'] = delete_result.rowcount or 0
            
            if results['deleted_count'] > 0:
                logger.info(f"Deleted {results['deleted_count']} very old deprecated patterns")
            
            # 3. Validate active patterns (check if still occurring)
            validation_cutoff = now - timedelta(days=self.validation_window_days)
            active_patterns_query = select(Pattern).where(
                Pattern.deprecated == False  # type: ignore
            )
            active_result = await db.execute(active_patterns_query)
            active_patterns = active_result.scalars().all()
            results['active_patterns'] = len(active_patterns)
            
            for pattern in active_patterns:
                # Check if pattern has recent occurrences in history
                recent_history_query = select(PatternHistory).where(
                    and_(
                        PatternHistory.pattern_id == pattern.id,
                        PatternHistory.recorded_at >= validation_cutoff
                    )
                ).limit(1)
                recent_history_result = await db.execute(recent_history_query)
                recent_history = recent_history_result.scalar_one_or_none()
                
                if not recent_history:
                    # Pattern has no recent occurrences - mark for review
                    pattern.needs_review = True  # type: ignore
                    results['needs_review_count'] += 1
                    logger.debug(
                        f"Pattern {pattern.id} marked for review "
                        f"(no occurrences in last {self.validation_window_days} days)"
                    )
                else:
                    # Pattern is still active - clear review flag
                    pattern.needs_review = False  # type: ignore
            
            await db.commit()
            
            logger.info(
                f"Pattern lifecycle management complete: "
                f"{results['deprecated_count']} deprecated, "
                f"{results['deleted_count']} deleted, "
                f"{results['needs_review_count']} need review, "
                f"{results['active_patterns']} active"
            )
            
            return results
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Pattern lifecycle management failed: {e}", exc_info=True)
            raise
    
    async def get_lifecycle_stats(self, db: AsyncSession) -> dict[str, Any]:
        """
        Get lifecycle statistics.
        
        Args:
            db: Database session
            
        Returns:
            Dictionary with lifecycle statistics
        """
        now = datetime.now(timezone.utc)
        stale_cutoff = now - timedelta(days=self.stale_threshold_days)
        old_deprecated_cutoff = now - timedelta(days=self.deletion_threshold_days)
        
        # Count patterns by status
        total_query = select(Pattern)
        total_result = await db.execute(total_query)
        total_patterns = len(total_result.scalars().all())
        
        active_query = select(Pattern).where(
            Pattern.deprecated == False  # type: ignore
        )
        active_result = await db.execute(active_query)
        active_patterns = len(active_result.scalars().all())
        
        deprecated_query = select(Pattern).where(
            Pattern.deprecated == True  # type: ignore
        )
        deprecated_result = await db.execute(deprecated_query)
        deprecated_patterns = len(deprecated_result.scalars().all())
        
        stale_query = select(Pattern).where(
            and_(
                Pattern.last_seen < stale_cutoff,
                Pattern.deprecated == False  # type: ignore
            )
        )
        stale_result = await db.execute(stale_query)
        stale_patterns = len(stale_result.scalars().all())
        
        needs_review_query = select(Pattern).where(
            Pattern.needs_review == True  # type: ignore
        )
        needs_review_result = await db.execute(needs_review_query)
        needs_review_patterns = len(needs_review_result.scalars().all())
        
        return {
            'total_patterns': total_patterns,
            'active_patterns': active_patterns,
            'deprecated_patterns': deprecated_patterns,
            'stale_patterns': stale_patterns,
            'needs_review_patterns': needs_review_patterns,
            'stale_threshold_days': self.stale_threshold_days,
            'deletion_threshold_days': self.deletion_threshold_days,
            'validation_window_days': self.validation_window_days
        }

