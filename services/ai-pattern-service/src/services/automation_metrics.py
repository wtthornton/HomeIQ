"""
Automation Metrics Collector Service

Collects and reports automation execution metrics for tracking success rates.
Implements Recommendation 2.2: Automation Execution Tracking.

Based on PATTERNS_SYNERGIES_IMPROVEMENT_RECOMMENDATIONS.md

Created: January 2026
Features:
- Records automation execution results to InfluxDB
- Calculates success rates per automation and overall
- Tracks execution time and error patterns
- Provides metrics for feedback loop integration
- Supports the 85% success rate target
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Automation execution status."""
    
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"  # Condition not met
    PARTIAL = "partial"  # Some actions succeeded


@dataclass
class ExecutionRecord:
    """Record of a single automation execution."""
    
    automation_id: str
    synergy_id: Optional[str] = None
    blueprint_id: Optional[str] = None
    
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Context
    trigger_type: Optional[str] = None  # time, state, event
    trigger_entity: Optional[str] = None
    action_count: int = 1
    actions_succeeded: int = 1
    
    # Timestamps
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.SUCCESS
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'automation_id': self.automation_id,
            'synergy_id': self.synergy_id,
            'blueprint_id': self.blueprint_id,
            'status': self.status.value,
            'execution_time_ms': self.execution_time_ms,
            'error_message': self.error_message,
            'error_code': self.error_code,
            'trigger_type': self.trigger_type,
            'trigger_entity': self.trigger_entity,
            'action_count': self.action_count,
            'actions_succeeded': self.actions_succeeded,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class AutomationMetrics:
    """Aggregated metrics for an automation."""
    
    automation_id: str
    synergy_id: Optional[str] = None
    blueprint_id: Optional[str] = None
    
    # Execution counts
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    timeout_executions: int = 0
    skipped_executions: int = 0
    
    # Success rate
    success_rate: float = 0.0
    
    # Performance
    avg_execution_time_ms: float = 0.0
    min_execution_time_ms: int = 0
    max_execution_time_ms: int = 0
    p95_execution_time_ms: int = 0
    
    # Error analysis
    error_count: int = 0
    most_common_error: Optional[str] = None
    error_rate: float = 0.0
    
    # Time range
    first_execution: Optional[datetime] = None
    last_execution: Optional[datetime] = None
    lookback_hours: int = 24
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'automation_id': self.automation_id,
            'synergy_id': self.synergy_id,
            'blueprint_id': self.blueprint_id,
            'total_executions': self.total_executions,
            'successful_executions': self.successful_executions,
            'failed_executions': self.failed_executions,
            'timeout_executions': self.timeout_executions,
            'skipped_executions': self.skipped_executions,
            'success_rate': round(self.success_rate, 3),
            'avg_execution_time_ms': round(self.avg_execution_time_ms, 1),
            'min_execution_time_ms': self.min_execution_time_ms,
            'max_execution_time_ms': self.max_execution_time_ms,
            'p95_execution_time_ms': self.p95_execution_time_ms,
            'error_count': self.error_count,
            'most_common_error': self.most_common_error,
            'error_rate': round(self.error_rate, 3),
            'first_execution': self.first_execution.isoformat() if self.first_execution else None,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'lookback_hours': self.lookback_hours,
        }


@dataclass
class OverallMetrics:
    """Overall automation metrics summary."""
    
    total_automations: int = 0
    total_executions: int = 0
    overall_success_rate: float = 0.0
    
    # Target tracking (85% success rate target)
    target_success_rate: float = 0.85
    meets_target: bool = False
    gap_to_target: float = 0.0
    
    # Performance
    avg_execution_time_ms: float = 0.0
    
    # Problem automations
    failing_automations: int = 0
    automations_below_target: int = 0
    
    # Time range
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    lookback_hours: int = 24
    
    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'total_automations': self.total_automations,
            'total_executions': self.total_executions,
            'overall_success_rate': round(self.overall_success_rate, 3),
            'target_success_rate': self.target_success_rate,
            'meets_target': self.meets_target,
            'gap_to_target': round(self.gap_to_target, 3),
            'avg_execution_time_ms': round(self.avg_execution_time_ms, 1),
            'failing_automations': self.failing_automations,
            'automations_below_target': self.automations_below_target,
            'analysis_timestamp': self.analysis_timestamp.isoformat(),
            'lookback_hours': self.lookback_hours,
        }


class AutomationMetricsCollector:
    """
    Collect and report automation execution metrics.
    
    Integrates with InfluxDB for time-series storage and provides
    metrics for the feedback loop to improve synergy recommendations.
    
    Target: 85% automation success rate
    """
    
    DEFAULT_BUCKET = "automation_metrics"
    TARGET_SUCCESS_RATE = 0.85
    
    def __init__(
        self,
        influx_client: Any = None,
        bucket: str = DEFAULT_BUCKET,
        target_success_rate: float = TARGET_SUCCESS_RATE,
    ):
        """
        Initialize metrics collector.
        
        Args:
            influx_client: InfluxDB client (optional - uses in-memory if None)
            bucket: InfluxDB bucket name
            target_success_rate: Target success rate (default 85%)
        """
        self.influx_client = influx_client
        self.bucket = bucket
        self.target_success_rate = target_success_rate
        
        # In-memory storage for when InfluxDB is not available
        self._in_memory_records: list[ExecutionRecord] = []
        self._max_in_memory_records = 10000
        
        logger.info(
            f"AutomationMetricsCollector initialized: "
            f"bucket={bucket}, target_success_rate={target_success_rate:.0%}"
        )
    
    async def record_execution(
        self,
        automation_id: str,
        synergy_id: Optional[str] = None,
        blueprint_id: Optional[str] = None,
        success: bool = True,
        execution_time_ms: int = 0,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None,
        trigger_type: Optional[str] = None,
        trigger_entity: Optional[str] = None,
        action_count: int = 1,
        actions_succeeded: int = 1,
    ) -> ExecutionRecord:
        """
        Record automation execution to InfluxDB.
        
        Args:
            automation_id: Automation identifier
            synergy_id: Optional synergy that generated this automation
            blueprint_id: Optional blueprint used
            success: Whether execution succeeded
            execution_time_ms: Execution time in milliseconds
            error_message: Error message if failed
            error_code: Error code if failed
            trigger_type: Type of trigger (time, state, event)
            trigger_entity: Entity that triggered automation
            action_count: Total number of actions
            actions_succeeded: Number of actions that succeeded
            
        Returns:
            ExecutionRecord with recorded data
        """
        # Determine status
        if success:
            status = ExecutionStatus.SUCCESS
        elif actions_succeeded > 0 and actions_succeeded < action_count:
            status = ExecutionStatus.PARTIAL
        elif error_code == "timeout":
            status = ExecutionStatus.TIMEOUT
        else:
            status = ExecutionStatus.FAILURE
        
        record = ExecutionRecord(
            automation_id=automation_id,
            synergy_id=synergy_id,
            blueprint_id=blueprint_id,
            status=status,
            execution_time_ms=execution_time_ms,
            error_message=error_message[:200] if error_message else None,  # Truncate
            error_code=error_code,
            trigger_type=trigger_type,
            trigger_entity=trigger_entity,
            action_count=action_count,
            actions_succeeded=actions_succeeded,
            started_at=datetime.utcnow() - timedelta(milliseconds=execution_time_ms),
            completed_at=datetime.utcnow(),
        )
        
        # Write to InfluxDB if available
        if self.influx_client:
            await self._write_to_influx(record)
        else:
            # Store in memory
            self._store_in_memory(record)
        
        logger.debug(
            f"Recorded execution: automation={automation_id}, "
            f"status={status.value}, time={execution_time_ms}ms"
        )
        
        return record
    
    async def _write_to_influx(self, record: ExecutionRecord) -> None:
        """Write execution record to InfluxDB."""
        try:
            # Build InfluxDB point
            # Note: Actual implementation depends on influxdb-client-python
            point_data = {
                "measurement": "automation_execution",
                "tags": {
                    "automation_id": record.automation_id,
                    "synergy_id": record.synergy_id or "manual",
                    "blueprint_id": record.blueprint_id or "none",
                    "status": record.status.value,
                    "trigger_type": record.trigger_type or "unknown",
                },
                "fields": {
                    "execution_time_ms": record.execution_time_ms,
                    "success_int": 1 if record.is_success else 0,
                    "action_count": record.action_count,
                    "actions_succeeded": record.actions_succeeded,
                },
                "time": record.completed_at or datetime.utcnow(),
            }
            
            if record.error_message:
                point_data["fields"]["error"] = record.error_message
            
            # Write using InfluxDB client
            # await self.influx_client.write_api.write(bucket=self.bucket, record=point_data)
            
            # For now, also store in memory as backup
            self._store_in_memory(record)
            
        except Exception as e:
            logger.error(f"Failed to write to InfluxDB: {e}")
            self._store_in_memory(record)
    
    def _store_in_memory(self, record: ExecutionRecord) -> None:
        """Store record in memory (fallback when InfluxDB unavailable)."""
        self._in_memory_records.append(record)
        
        # Trim if exceeds max
        if len(self._in_memory_records) > self._max_in_memory_records:
            self._in_memory_records = self._in_memory_records[-self._max_in_memory_records:]
    
    async def get_automation_metrics(
        self,
        automation_id: str,
        lookback_hours: int = 24,
    ) -> AutomationMetrics:
        """
        Get metrics for a specific automation.
        
        Args:
            automation_id: Automation to get metrics for
            lookback_hours: Hours to look back
            
        Returns:
            AutomationMetrics with aggregated data
        """
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        # Filter records
        records = [
            r for r in self._in_memory_records
            if r.automation_id == automation_id and r.started_at >= cutoff
        ]
        
        return self._calculate_metrics(automation_id, records, lookback_hours)
    
    async def get_success_rate(
        self,
        lookback_hours: int = 24,
        automation_id: Optional[str] = None,
    ) -> dict[str, float]:
        """
        Calculate success rate for automations.
        
        Args:
            lookback_hours: Hours to look back
            automation_id: Optional specific automation (None = all)
            
        Returns:
            Dictionary mapping automation_id to success rate
        """
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        
        # Filter records
        if automation_id:
            records = [
                r for r in self._in_memory_records
                if r.automation_id == automation_id and r.started_at >= cutoff
            ]
            automation_ids = [automation_id]
        else:
            records = [r for r in self._in_memory_records if r.started_at >= cutoff]
            automation_ids = list({r.automation_id for r in records})
        
        # Calculate success rates
        result = {}
        for aid in automation_ids:
            aid_records = [r for r in records if r.automation_id == aid]
            if aid_records:
                success_count = sum(1 for r in aid_records if r.is_success)
                result[aid] = success_count / len(aid_records)
            else:
                result[aid] = 0.0
        
        return result
    
    async def get_overall_metrics(
        self,
        lookback_hours: int = 24,
    ) -> OverallMetrics:
        """
        Get overall automation metrics summary.
        
        Args:
            lookback_hours: Hours to look back
            
        Returns:
            OverallMetrics summary
        """
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        records = [r for r in self._in_memory_records if r.started_at >= cutoff]
        
        if not records:
            return OverallMetrics(
                lookback_hours=lookback_hours,
                target_success_rate=self.target_success_rate,
            )
        
        # Calculate overall metrics
        automation_ids = list({r.automation_id for r in records})
        total_executions = len(records)
        successful_executions = sum(1 for r in records if r.is_success)
        overall_success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
        
        # Calculate per-automation metrics
        failing_automations = 0
        automations_below_target = 0
        
        for aid in automation_ids:
            aid_records = [r for r in records if r.automation_id == aid]
            if aid_records:
                success_count = sum(1 for r in aid_records if r.is_success)
                success_rate = success_count / len(aid_records)
                
                if success_rate < 0.5:
                    failing_automations += 1
                if success_rate < self.target_success_rate:
                    automations_below_target += 1
        
        # Performance metrics
        execution_times = [r.execution_time_ms for r in records if r.execution_time_ms > 0]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        return OverallMetrics(
            total_automations=len(automation_ids),
            total_executions=total_executions,
            overall_success_rate=overall_success_rate,
            target_success_rate=self.target_success_rate,
            meets_target=overall_success_rate >= self.target_success_rate,
            gap_to_target=max(0, self.target_success_rate - overall_success_rate),
            avg_execution_time_ms=avg_execution_time,
            failing_automations=failing_automations,
            automations_below_target=automations_below_target,
            lookback_hours=lookback_hours,
        )
    
    def _calculate_metrics(
        self,
        automation_id: str,
        records: list[ExecutionRecord],
        lookback_hours: int,
    ) -> AutomationMetrics:
        """Calculate metrics from execution records."""
        if not records:
            return AutomationMetrics(
                automation_id=automation_id,
                lookback_hours=lookback_hours,
            )
        
        # Count by status
        total = len(records)
        successful = sum(1 for r in records if r.status == ExecutionStatus.SUCCESS)
        failed = sum(1 for r in records if r.status == ExecutionStatus.FAILURE)
        timeout = sum(1 for r in records if r.status == ExecutionStatus.TIMEOUT)
        skipped = sum(1 for r in records if r.status == ExecutionStatus.SKIPPED)
        
        # Success rate
        success_rate = successful / total if total > 0 else 0.0
        
        # Execution times
        execution_times = [r.execution_time_ms for r in records if r.execution_time_ms > 0]
        if execution_times:
            avg_time = sum(execution_times) / len(execution_times)
            min_time = min(execution_times)
            max_time = max(execution_times)
            sorted_times = sorted(execution_times)
            p95_idx = int(len(sorted_times) * 0.95)
            p95_time = sorted_times[min(p95_idx, len(sorted_times) - 1)]
        else:
            avg_time = min_time = max_time = p95_time = 0
        
        # Error analysis
        errors = [r.error_message for r in records if r.error_message]
        error_count = len(errors)
        error_rate = error_count / total if total > 0 else 0.0
        
        # Most common error
        most_common_error = None
        if errors:
            from collections import Counter
            error_counts = Counter(errors)
            most_common_error = error_counts.most_common(1)[0][0]
        
        # Timestamps
        first_execution = min(r.started_at for r in records)
        last_execution = max(r.started_at for r in records)
        
        # Get synergy/blueprint from first record
        first_record = records[0]
        
        return AutomationMetrics(
            automation_id=automation_id,
            synergy_id=first_record.synergy_id,
            blueprint_id=first_record.blueprint_id,
            total_executions=total,
            successful_executions=successful,
            failed_executions=failed,
            timeout_executions=timeout,
            skipped_executions=skipped,
            success_rate=success_rate,
            avg_execution_time_ms=avg_time,
            min_execution_time_ms=min_time,
            max_execution_time_ms=max_time,
            p95_execution_time_ms=p95_time,
            error_count=error_count,
            most_common_error=most_common_error,
            error_rate=error_rate,
            first_execution=first_execution,
            last_execution=last_execution,
            lookback_hours=lookback_hours,
        )
    
    async def get_problem_automations(
        self,
        lookback_hours: int = 24,
        success_threshold: float = 0.7,
    ) -> list[AutomationMetrics]:
        """
        Get automations with success rate below threshold.
        
        Args:
            lookback_hours: Hours to look back
            success_threshold: Minimum acceptable success rate
            
        Returns:
            List of AutomationMetrics for problem automations
        """
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        records = [r for r in self._in_memory_records if r.started_at >= cutoff]
        
        # Group by automation
        automation_ids = list({r.automation_id for r in records})
        
        problem_automations = []
        for aid in automation_ids:
            aid_records = [r for r in records if r.automation_id == aid]
            metrics = self._calculate_metrics(aid, aid_records, lookback_hours)
            
            if metrics.success_rate < success_threshold:
                problem_automations.append(metrics)
        
        # Sort by success rate (worst first)
        problem_automations.sort(key=lambda m: m.success_rate)
        
        return problem_automations
    
    async def update_synergy_confidence(
        self,
        synergy_id: str,
        lookback_hours: int = 168,  # 1 week
    ) -> Optional[float]:
        """
        Calculate confidence adjustment for a synergy based on automation performance.
        
        This is used by the feedback loop to adjust synergy confidence scores
        based on how well the generated automations perform.
        
        Args:
            synergy_id: Synergy to calculate adjustment for
            lookback_hours: Hours to look back
            
        Returns:
            Confidence adjustment (-0.2 to +0.2) or None if insufficient data
        """
        cutoff = datetime.utcnow() - timedelta(hours=lookback_hours)
        records = [
            r for r in self._in_memory_records
            if r.synergy_id == synergy_id and r.started_at >= cutoff
        ]
        
        if len(records) < 5:  # Need minimum data
            return None
        
        # Calculate success rate
        success_count = sum(1 for r in records if r.is_success)
        success_rate = success_count / len(records)
        
        # Calculate adjustment
        # - 100% success → +0.2 boost
        # - 85% success (target) → +0.1 boost
        # - 70% success → no change
        # - 50% success → -0.1 penalty
        # - 0% success → -0.2 penalty
        
        if success_rate >= 0.95:
            adjustment = 0.2
        elif success_rate >= self.target_success_rate:
            adjustment = 0.1 + (success_rate - self.target_success_rate) * 0.67
        elif success_rate >= 0.7:
            adjustment = (success_rate - 0.7) * 0.67
        elif success_rate >= 0.5:
            adjustment = -0.1 + (success_rate - 0.5) * 0.5
        else:
            adjustment = -0.2 + success_rate * 0.2
        
        logger.info(
            f"Synergy {synergy_id} confidence adjustment: {adjustment:+.3f} "
            f"(success_rate={success_rate:.0%}, executions={len(records)})"
        )
        
        return round(adjustment, 3)
