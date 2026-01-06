"""
Automation Execution Tracker

Tracks automation execution and learns from success/failure.
Integrates with Home Assistant to monitor automation runs
and update pattern/synergy confidence based on outcomes.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md - Recommendation 2.2
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AutomationTracker:
    """
    Track automation execution and learn from success/failure.
    
    Integrates with Home Assistant to monitor automation runs
    and update pattern/synergy confidence based on outcomes.
    """
    
    def __init__(self, db: Optional[AsyncSession] = None):
        """
        Initialize automation tracker.
        
        Args:
            db: Optional database session for storing execution data
        """
        self.db = db
    
    async def track_automation_execution(
        self,
        automation_id: str,
        synergy_id: str,
        execution_result: dict[str, Any],
        db: Optional[AsyncSession] = None
    ) -> None:
        """
        Track automation execution and update synergy confidence.
        
        Args:
            automation_id: Home Assistant automation entity ID
            synergy_id: Synergy ID that generated this automation
            execution_result: {
                'success': bool,
                'error': str | None,
                'execution_time_ms': int,
                'triggered_count': int
            }
            db: Optional database session (uses self.db if not provided)
        """
        session = db or self.db
        if not session:
            logger.warning("No database session available for tracking automation execution")
            return
        
        try:
            success = execution_result.get('success', False)
            error = execution_result.get('error')
            execution_time_ms = execution_result.get('execution_time_ms', 0)
            triggered_count = execution_result.get('triggered_count', 0)
            
            # Store execution record
            await self._store_execution_record(
                session,
                automation_id,
                synergy_id,
                success,
                error,
                execution_time_ms,
                triggered_count
            )
            
            # Update synergy confidence based on execution
            await self._update_synergy_confidence(
                session,
                synergy_id,
                success,
                triggered_count
            )
            
            logger.info(
                f"✅ Tracked automation execution: automation_id={automation_id}, "
                f"synergy_id={synergy_id}, success={success}, triggered={triggered_count}"
            )
        except Exception as e:
            logger.error(f"Failed to track automation execution: {e}", exc_info=True)
    
    async def _store_execution_record(
        self,
        db: AsyncSession,
        automation_id: str,
        synergy_id: str,
        success: bool,
        error: Optional[str],
        execution_time_ms: int,
        triggered_count: int
    ) -> None:
        """Store automation execution record in database."""
        try:
            # Create execution record table if it doesn't exist
            create_table_query = text("""
                CREATE TABLE IF NOT EXISTS automation_executions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    automation_id TEXT NOT NULL,
                    synergy_id TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    error TEXT,
                    execution_time_ms INTEGER,
                    triggered_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (synergy_id) REFERENCES synergy_opportunities(synergy_id)
                )
            """)
            await db.execute(create_table_query)
            await db.commit()
            
            # Insert execution record
            insert_query = text("""
                INSERT INTO automation_executions 
                (automation_id, synergy_id, success, error, execution_time_ms, triggered_count, created_at)
                VALUES (:automation_id, :synergy_id, :success, :error, :execution_time_ms, :triggered_count, datetime('now'))
            """)
            await db.execute(
                insert_query,
                {
                    "automation_id": automation_id,
                    "synergy_id": synergy_id,
                    "success": success,
                    "error": error,
                    "execution_time_ms": execution_time_ms,
                    "triggered_count": triggered_count
                }
            )
            await db.commit()
        except Exception as e:
            logger.warning(f"Failed to store execution record: {e}")
            await db.rollback()
    
    async def _update_synergy_confidence(
        self,
        db: AsyncSession,
        synergy_id: str,
        success: bool,
        triggered_count: int
    ) -> None:
        """
        Update synergy confidence based on execution outcomes.
        
        Positive outcomes → increase confidence
        Negative outcomes → decrease confidence
        """
        try:
            # Get current synergy
            get_synergy_query = text("""
                SELECT confidence, impact_score
                FROM synergy_opportunities
                WHERE synergy_id = :synergy_id
            """)
            result = await db.execute(get_synergy_query, {"synergy_id": synergy_id})
            row = result.fetchone()
            
            if not row:
                logger.warning(f"Synergy {synergy_id} not found for confidence update")
                return
            
            current_confidence = row[0] or 0.5
            current_impact = row[1] or 0.5
            
            # Calculate confidence adjustment
            # Success with triggers → +0.05 confidence, +0.03 impact
            # Failure → -0.1 confidence, -0.05 impact
            # Success but no triggers → +0.02 confidence (automation works but not used)
            if success:
                if triggered_count > 0:
                    # Successful execution with triggers → strong positive signal
                    confidence_adjustment = min(0.05, 1.0 - current_confidence)
                    impact_adjustment = min(0.03, 1.0 - current_impact)
                else:
                    # Successful but not triggered → weak positive signal
                    confidence_adjustment = min(0.02, 1.0 - current_confidence)
                    impact_adjustment = 0.0
            else:
                # Failure → negative signal
                confidence_adjustment = max(-0.1, -current_confidence)
                impact_adjustment = max(-0.05, -current_impact)
            
            new_confidence = max(0.0, min(1.0, current_confidence + confidence_adjustment))
            new_impact = max(0.0, min(1.0, current_impact + impact_adjustment))
            
            # Update synergy confidence
            update_query = text("""
                UPDATE synergy_opportunities
                SET confidence = :confidence,
                    impact_score = :impact_score,
                    updated_at = datetime('now')
                WHERE synergy_id = :synergy_id
            """)
            await db.execute(
                update_query,
                {
                    "synergy_id": synergy_id,
                    "confidence": new_confidence,
                    "impact_score": new_impact
                }
            )
            await db.commit()
            
            logger.info(
                f"Updated synergy {synergy_id} confidence: {current_confidence:.2f} → {new_confidence:.2f} "
                f"(adjustment: {confidence_adjustment:+.2f})"
            )
        except Exception as e:
            logger.warning(f"Failed to update synergy confidence: {e}")
            await db.rollback()
    
    async def get_execution_stats(
        self,
        synergy_id: str,
        db: Optional[AsyncSession] = None
    ) -> dict[str, Any]:
        """
        Get execution statistics for a synergy.
        
        Args:
            synergy_id: Synergy ID to get stats for
            db: Optional database session
        
        Returns:
            {
                'total_executions': int,
                'successful_executions': int,
                'failed_executions': int,
                'total_triggered': int,
                'avg_execution_time_ms': float,
                'success_rate': float
            }
        """
        session = db or self.db
        if not session:
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_triggered': 0,
                'avg_execution_time_ms': 0.0,
                'success_rate': 0.0
            }
        
        try:
            stats_query = text("""
                SELECT 
                    COUNT(*) as total_executions,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful_executions,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed_executions,
                    SUM(triggered_count) as total_triggered,
                    AVG(execution_time_ms) as avg_execution_time_ms
                FROM automation_executions
                WHERE synergy_id = :synergy_id
            """)
            result = await session.execute(stats_query, {"synergy_id": synergy_id})
            row = result.fetchone()
            
            if row and row[0]:
                total = row[0] or 0
                successful = row[1] or 0
                failed = row[2] or 0
                total_triggered = row[3] or 0
                avg_time = row[4] or 0.0
                
                return {
                    'total_executions': total,
                    'successful_executions': successful,
                    'failed_executions': failed,
                    'total_triggered': total_triggered,
                    'avg_execution_time_ms': avg_time,
                    'success_rate': (successful / total) if total > 0 else 0.0
                }
            else:
                return {
                    'total_executions': 0,
                    'successful_executions': 0,
                    'failed_executions': 0,
                    'total_triggered': 0,
                    'avg_execution_time_ms': 0.0,
                    'success_rate': 0.0
                }
        except Exception as e:
            logger.warning(f"Failed to get execution stats: {e}")
            return {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_triggered': 0,
                'avg_execution_time_ms': 0.0,
                'success_rate': 0.0
            }
