"""
Execution Tracker

Tracks automation execution results to measure success rate.
Target: 85% automation success rate (from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Status of an automation execution."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    PARTIAL = "partial"  # Some actions succeeded, some failed
    SKIPPED = "skipped"  # Conditions not met


@dataclass
class ExecutionRecord:
    """Record of a single automation execution."""
    
    automation_id: str
    execution_id: str
    triggered_at: datetime
    completed_at: datetime | None = None
    
    # Status
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    error_message: str | None = None
    error_type: str | None = None
    
    # Performance
    execution_time_ms: int | None = None
    actions_total: int = 0
    actions_succeeded: int = 0
    actions_failed: int = 0
    
    # Context
    trigger_type: str | None = None  # state, time, event, etc.
    trigger_entity: str | None = None
    synergy_id: str | None = None
    blueprint_id: str | None = None
    
    # Computed
    @property
    def success_rate(self) -> float:
        """Calculate action success rate."""
        if self.actions_total == 0:
            return 1.0 if self.status == ExecutionStatus.SUCCESS else 0.0
        return self.actions_succeeded / self.actions_total


@dataclass
class AutomationStats:
    """Statistics for a single automation."""
    
    automation_id: str
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    
    # Performance
    avg_execution_time_ms: float = 0.0
    min_execution_time_ms: int | None = None
    max_execution_time_ms: int | None = None
    
    # Error tracking
    error_counts: dict[str, int] = field(default_factory=dict)
    last_error: str | None = None
    last_error_at: datetime | None = None
    
    # Computed
    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        if self.total_executions == 0:
            return 0.0
        return self.successful_executions / self.total_executions * 100


class ExecutionTracker:
    """
    Tracks automation execution results.
    
    Monitors:
    - Execution success/failure
    - Execution time
    - Error patterns
    - Per-automation statistics
    
    Target: 85% success rate (from RECOMMENDATIONS_FEASIBILITY_ANALYSIS.md)
    """
    
    def __init__(self, retention_days: int = 90):
        """
        Initialize execution tracker.
        
        Args:
            retention_days: Days to retain execution records
        """
        self.retention_days = retention_days
        self._executions: list[ExecutionRecord] = []
        self._automation_stats: dict[str, AutomationStats] = {}
        self._synergy_executions: dict[str, list[ExecutionRecord]] = defaultdict(list)
        
        logger.info(f"ExecutionTracker initialized (retention={retention_days} days)")
    
    def record_execution(
        self,
        automation_id: str,
        execution_id: str,
        status: ExecutionStatus,
        triggered_at: datetime | None = None,
        completed_at: datetime | None = None,
        execution_time_ms: int | None = None,
        error_message: str | None = None,
        error_type: str | None = None,
        trigger_type: str | None = None,
        trigger_entity: str | None = None,
        actions_total: int = 0,
        actions_succeeded: int = 0,
        actions_failed: int = 0,
        synergy_id: str | None = None,
        blueprint_id: str | None = None,
    ) -> ExecutionRecord:
        """
        Record an automation execution.
        
        Args:
            automation_id: Home Assistant automation entity ID
            execution_id: Unique execution identifier
            status: Execution status
            triggered_at: When automation was triggered
            completed_at: When execution completed
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if failed
            error_type: Error type classification
            trigger_type: Type of trigger (state, time, event)
            trigger_entity: Entity that triggered automation
            actions_total: Total actions in automation
            actions_succeeded: Number of successful actions
            actions_failed: Number of failed actions
            synergy_id: Synergy that created this automation
            blueprint_id: Blueprint used
            
        Returns:
            ExecutionRecord
        """
        record = ExecutionRecord(
            automation_id=automation_id,
            execution_id=execution_id,
            triggered_at=triggered_at or datetime.utcnow(),
            completed_at=completed_at,
            status=status,
            error_message=error_message,
            error_type=error_type,
            execution_time_ms=execution_time_ms,
            trigger_type=trigger_type,
            trigger_entity=trigger_entity,
            actions_total=actions_total,
            actions_succeeded=actions_succeeded,
            actions_failed=actions_failed,
            synergy_id=synergy_id,
            blueprint_id=blueprint_id,
        )
        
        # Store execution
        self._executions.append(record)
        
        # Update automation stats
        self._update_automation_stats(record)
        
        # Track synergy executions
        if synergy_id:
            self._synergy_executions[synergy_id].append(record)
        
        logger.debug(
            f"Recorded execution: automation={automation_id}, "
            f"status={status.value}, time={execution_time_ms}ms"
        )
        
        return record
    
    def get_automation_stats(self, automation_id: str) -> AutomationStats | None:
        """Get statistics for an automation."""
        return self._automation_stats.get(automation_id)
    
    def get_automation_success_rate(self, automation_id: str) -> float | None:
        """Get success rate for an automation."""
        stats = self._automation_stats.get(automation_id)
        return stats.success_rate if stats else None
    
    def get_synergy_success_rate(self, synergy_id: str) -> float | None:
        """Get success rate for automations from a synergy."""
        executions = self._synergy_executions.get(synergy_id, [])
        if not executions:
            return None
        
        successful = sum(1 for e in executions if e.status == ExecutionStatus.SUCCESS)
        return successful / len(executions) * 100
    
    def get_overall_success_rate(self, days: int = 30) -> dict[str, Any]:
        """
        Get overall success rate for the period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with success metrics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        period_executions = [e for e in self._executions if e.triggered_at >= cutoff]
        
        if not period_executions:
            return {
                "period_days": days,
                "total_executions": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "target": 85.0,
                "achieved": False,
            }
        
        successful = sum(1 for e in period_executions if e.status == ExecutionStatus.SUCCESS)
        failed = sum(1 for e in period_executions if e.status == ExecutionStatus.FAILURE)
        success_rate = successful / len(period_executions) * 100
        
        return {
            "period_days": days,
            "total_executions": len(period_executions),
            "successful": successful,
            "failed": failed,
            "partial": sum(1 for e in period_executions if e.status == ExecutionStatus.PARTIAL),
            "skipped": sum(1 for e in period_executions if e.status == ExecutionStatus.SKIPPED),
            "timeout": sum(1 for e in period_executions if e.status == ExecutionStatus.TIMEOUT),
            "success_rate": success_rate,
            "target": 85.0,
            "achieved": success_rate >= 85.0,
            "progress_pct": min(100, success_rate / 85.0 * 100),
        }
    
    def get_error_summary(self, days: int = 30) -> dict[str, Any]:
        """
        Get summary of errors for the period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with error breakdown
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        failed_executions = [
            e for e in self._executions
            if e.triggered_at >= cutoff and e.status == ExecutionStatus.FAILURE
        ]
        
        # Count errors by type
        error_counts: dict[str, int] = defaultdict(int)
        for execution in failed_executions:
            error_type = execution.error_type or "unknown"
            error_counts[error_type] += 1
        
        # Sort by count
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "period_days": days,
            "total_failures": len(failed_executions),
            "error_types": dict(sorted_errors),
            "top_errors": sorted_errors[:5],
        }
    
    def get_performance_summary(self, days: int = 30) -> dict[str, Any]:
        """
        Get performance summary for the period.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Dictionary with performance metrics
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        period_executions = [
            e for e in self._executions
            if e.triggered_at >= cutoff and e.execution_time_ms is not None
        ]
        
        if not period_executions:
            return {
                "period_days": days,
                "total_executions": 0,
                "avg_execution_time_ms": 0,
                "min_execution_time_ms": 0,
                "max_execution_time_ms": 0,
                "p95_execution_time_ms": 0,
            }
        
        execution_times = [e.execution_time_ms for e in period_executions]
        execution_times.sort()
        
        p95_index = int(len(execution_times) * 0.95)
        
        return {
            "period_days": days,
            "total_executions": len(period_executions),
            "avg_execution_time_ms": sum(execution_times) / len(execution_times),
            "min_execution_time_ms": min(execution_times),
            "max_execution_time_ms": max(execution_times),
            "p95_execution_time_ms": execution_times[p95_index] if p95_index < len(execution_times) else execution_times[-1],
        }
    
    def get_problematic_automations(
        self,
        min_executions: int = 5,
        max_success_rate: float = 80.0,
    ) -> list[dict[str, Any]]:
        """
        Get automations with low success rates.
        
        Args:
            min_executions: Minimum executions to consider
            max_success_rate: Maximum success rate to include
            
        Returns:
            List of problematic automations with stats
        """
        problematic = []
        
        for automation_id, stats in self._automation_stats.items():
            if stats.total_executions >= min_executions and stats.success_rate <= max_success_rate:
                problematic.append({
                    "automation_id": automation_id,
                    "total_executions": stats.total_executions,
                    "success_rate": stats.success_rate,
                    "last_error": stats.last_error,
                    "last_error_at": stats.last_error_at.isoformat() if stats.last_error_at else None,
                    "top_errors": sorted(
                        stats.error_counts.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )[:3],
                })
        
        # Sort by success rate (lowest first)
        problematic.sort(key=lambda x: x["success_rate"])
        
        return problematic
    
    def cleanup_old_records(self) -> int:
        """
        Remove records older than retention period.
        
        Returns:
            Number of records removed
        """
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        original_count = len(self._executions)
        
        self._executions = [e for e in self._executions if e.triggered_at >= cutoff]
        
        removed = original_count - len(self._executions)
        if removed > 0:
            logger.info(f"Cleaned up {removed} old execution records")
        
        return removed
    
    def _update_automation_stats(self, record: ExecutionRecord) -> None:
        """Update automation statistics with new execution."""
        automation_id = record.automation_id
        
        if automation_id not in self._automation_stats:
            self._automation_stats[automation_id] = AutomationStats(
                automation_id=automation_id
            )
        
        stats = self._automation_stats[automation_id]
        stats.total_executions += 1
        
        if record.status == ExecutionStatus.SUCCESS:
            stats.successful_executions += 1
        elif record.status == ExecutionStatus.FAILURE:
            stats.failed_executions += 1
            if record.error_type:
                stats.error_counts[record.error_type] = stats.error_counts.get(record.error_type, 0) + 1
            stats.last_error = record.error_message
            stats.last_error_at = record.triggered_at
        
        # Update execution time stats
        if record.execution_time_ms is not None:
            # Running average
            prev_avg = stats.avg_execution_time_ms
            prev_count = stats.total_executions - 1
            stats.avg_execution_time_ms = (
                (prev_avg * prev_count + record.execution_time_ms) / stats.total_executions
            )
            
            if stats.min_execution_time_ms is None or record.execution_time_ms < stats.min_execution_time_ms:
                stats.min_execution_time_ms = record.execution_time_ms
            if stats.max_execution_time_ms is None or record.execution_time_ms > stats.max_execution_time_ms:
                stats.max_execution_time_ms = record.execution_time_ms
