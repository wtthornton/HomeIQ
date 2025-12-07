"""
Performance Tracking Utility

Tracks performance metrics for the chat endpoint and other operations.
Provides detailed timing information for optimization analysis.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single performance metric"""
    name: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """Performance report for an operation"""
    operation: str
    total_duration: float
    metrics: List[PerformanceMetric]
    timestamp: float


class PerformanceTracker:
    """Tracks performance metrics for operations"""
    
    def __init__(self, max_reports: int = 100):
        """
        Initialize performance tracker.
        
        Args:
            max_reports: Maximum number of reports to keep in memory
        """
        self.metrics: Dict[str, PerformanceMetric] = {}
        self.reports: deque = deque(maxlen=max_reports)
        self.max_reports = max_reports
    
    def start(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Start tracking a metric.
        
        Args:
            name: Metric name
            metadata: Optional metadata
            
        Returns:
            Metric ID for ending the metric
        """
        metric_id = f"{name}_{int(time.time() * 1000)}_{id(self)}"
        self.metrics[metric_id] = PerformanceMetric(
            name=name,
            start_time=time.perf_counter(),
            metadata=metadata or {}
        )
        return metric_id
    
    def end(self, metric_id: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[PerformanceMetric]:
        """
        End tracking a metric.
        
        Args:
            metric_id: Metric ID from start()
            metadata: Optional additional metadata
            
        Returns:
            Completed metric or None if not found
        """
        metric = self.metrics.get(metric_id)
        if not metric:
            logger.warning(f"Performance metric {metric_id} not found")
            return None
        
        end_time = time.perf_counter()
        duration = end_time - metric.start_time
        
        metric.end_time = end_time
        metric.duration = duration
        if metadata:
            metric.metadata.update(metadata)
        
        return metric
    
    def create_report(
        self, 
        operation: str, 
        metric_ids: List[str],
        additional_metadata: Optional[Dict[str, Any]] = None
    ) -> PerformanceReport:
        """
        Create a performance report for an operation.
        
        Args:
            operation: Operation name
            metric_ids: List of metric IDs to include
            additional_metadata: Optional additional metadata for the report
            
        Returns:
            Performance report
        """
        metrics = []
        for metric_id in metric_ids:
            metric = self.metrics.get(metric_id)
            if metric and metric.duration is not None:
                metrics.append(metric)
        
        total_duration = sum(m.duration for m in metrics if m.duration)
        
        report = PerformanceReport(
            operation=operation,
            total_duration=total_duration,
            metrics=metrics,
            timestamp=time.time()
        )
        
        # Add to reports
        self.reports.append(report)
        
        # Log report (convert seconds to milliseconds for display)
        total_duration_ms = total_duration * 1000
        logger.info(
            f"[Performance] {operation}: "
            f"Total: {total_duration_ms:.2f}ms ({total_duration:.3f}s), "
            f"Metrics: {len(metrics)}, "
            f"Details: {', '.join(f'{m.name}={m.duration*1000:.2f}ms' for m in metrics)}"
        )
        
        if additional_metadata:
            logger.debug(f"[Performance] {operation} metadata: {additional_metadata}")
        
        return report
    
    def get_reports(self) -> List[PerformanceReport]:
        """Get all reports"""
        return list(self.reports)
    
    def get_reports_for_operation(self, operation: str) -> List[PerformanceReport]:
        """Get reports for a specific operation"""
        return [r for r in self.reports if r.operation == operation]
    
    def get_average_duration(self, operation: str) -> float:
        """Get average duration for an operation"""
        reports = self.get_reports_for_operation(operation)
        if not reports:
            return 0.0
        total = sum(r.total_duration for r in reports)
        return total / len(reports)
    
    def clear(self) -> None:
        """Clear all metrics and reports"""
        self.metrics.clear()
        self.reports.clear()
    
    def export_reports(self) -> List[Dict[str, Any]]:
        """Export reports as dictionaries"""
        return [
            {
                "operation": r.operation,
                "total_duration": r.total_duration,
                "timestamp": r.timestamp,
                "metrics": [
                    {
                        "name": m.name,
                        "duration": m.duration,
                        "metadata": m.metadata
                    }
                    for m in r.metrics
                ]
            }
            for r in self.reports
        ]


# Global instance
_performance_tracker = PerformanceTracker()


def get_tracker() -> PerformanceTracker:
    """Get the global performance tracker instance"""
    return _performance_tracker


def start_tracking(name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    """Start tracking a metric (convenience function)"""
    return _performance_tracker.start(name, metadata)


def end_tracking(metric_id: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[PerformanceMetric]:
    """End tracking a metric (convenience function)"""
    return _performance_tracker.end(metric_id, metadata)


def create_report(
    operation: str,
    metric_ids: List[str],
    additional_metadata: Optional[Dict[str, Any]] = None
) -> PerformanceReport:
    """Create a performance report (convenience function)"""
    return _performance_tracker.create_report(operation, metric_ids, additional_metadata)

