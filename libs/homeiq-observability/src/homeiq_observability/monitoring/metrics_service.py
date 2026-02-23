"""Performance metrics collection and monitoring service."""

import asyncio
import time
import psutil
import threading
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import json
import os
from enum import Enum


class MetricType(Enum):
    """Metric type enumeration."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


@dataclass
class MetricValue:
    """Metric value with timestamp."""
    timestamp: str
    value: float
    labels: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric value to dictionary."""
        return asdict(self)


@dataclass
class Metric:
    """Metric definition."""
    name: str
    type: MetricType
    description: str
    unit: str
    values: List[MetricValue]
    labels: Optional[Dict[str, str]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "unit": self.unit,
            "values": [value.to_dict() for value in self.values],
            "labels": self.labels
        }


class MetricsCollector:
    """Metrics collection and aggregation."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.metrics: Dict[str, Metric] = {}
        self.metrics_lock = threading.Lock()
        self.max_values_per_metric = int(os.getenv('METRICS_MAX_VALUES', '1000'))
        
        # System metrics collection
        self.system_metrics_enabled = os.getenv('SYSTEM_METRICS_ENABLED', 'true').lower() == 'true'
        self.metrics_interval = float(os.getenv('METRICS_INTERVAL_SECONDS', '60'))
        
        # Background collection
        self.is_collecting = False
        self.collection_task = None
        
        # Initialize system metrics
        if self.system_metrics_enabled:
            self._initialize_system_metrics()
    
    def _initialize_system_metrics(self):
        """Initialize system metrics."""
        # CPU metrics
        self.register_metric("system_cpu_usage_percent", MetricType.GAUGE, 
                           "System CPU usage percentage", "percent")
        self.register_metric("system_cpu_count", MetricType.GAUGE, 
                           "Number of CPU cores", "count")
        
        # Memory metrics
        self.register_metric("system_memory_usage_bytes", MetricType.GAUGE, 
                           "System memory usage in bytes", "bytes")
        self.register_metric("system_memory_usage_percent", MetricType.GAUGE, 
                           "System memory usage percentage", "percent")
        self.register_metric("system_memory_available_bytes", MetricType.GAUGE, 
                           "System available memory in bytes", "bytes")
        
        # Disk metrics
        self.register_metric("system_disk_usage_bytes", MetricType.GAUGE, 
                           "System disk usage in bytes", "bytes")
        self.register_metric("system_disk_usage_percent", MetricType.GAUGE, 
                           "System disk usage percentage", "percent")
        self.register_metric("system_disk_free_bytes", MetricType.GAUGE, 
                           "System free disk space in bytes", "bytes")
        
        # Network metrics
        self.register_metric("system_network_bytes_sent", MetricType.COUNTER, 
                           "System network bytes sent", "bytes")
        self.register_metric("system_network_bytes_recv", MetricType.COUNTER, 
                           "System network bytes received", "bytes")
        
        # Process metrics
        self.register_metric("system_process_count", MetricType.GAUGE, 
                           "Number of running processes", "count")
    
    def register_metric(self, name: str, metric_type: MetricType, 
                       description: str, unit: str, 
                       labels: Optional[Dict[str, str]] = None):
        """Register a new metric."""
        with self.metrics_lock:
            if name not in self.metrics:
                self.metrics[name] = Metric(
                    name=name,
                    type=metric_type,
                    description=description,
                    unit=unit,
                    values=[],
                    labels=labels
                )
    
    def record_value(self, name: str, value: float, 
                    labels: Optional[Dict[str, str]] = None):
        """Record a metric value."""
        with self.metrics_lock:
            if name not in self.metrics:
                return
            
            metric = self.metrics[name]
            metric_value = MetricValue(
                timestamp=datetime.now(timezone.utc).isoformat(),
                value=value,
                labels=labels
            )
            
            metric.values.append(metric_value)
            
            # Limit number of values per metric
            if len(metric.values) > self.max_values_per_metric:
                metric.values = metric.values[-self.max_values_per_metric:]
    
    def increment_counter(self, name: str, increment: float = 1.0,
                         labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric."""
        current_value = self.get_latest_value(name, labels)
        new_value = current_value + increment
        self.record_value(name, new_value, labels)
    
    def set_gauge(self, name: str, value: float,
                  labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value."""
        self.record_value(name, value, labels)
    
    def record_timer(self, name: str, duration_seconds: float,
                    labels: Optional[Dict[str, str]] = None):
        """Record a timer metric."""
        self.record_value(name, duration_seconds, labels)
    
    def get_latest_value(self, name: str, 
                        labels: Optional[Dict[str, str]] = None) -> float:
        """Get the latest value for a metric."""
        with self.metrics_lock:
            if name not in self.metrics:
                return 0.0
            
            metric = self.metrics[name]
            if not metric.values:
                return 0.0
            
            # Filter by labels if provided
            if labels:
                for value in reversed(metric.values):
                    if value.labels == labels:
                        return value.value
            else:
                return metric.values[-1].value
            
            return 0.0
    
    def get_metric(self, name: str) -> Optional[Metric]:
        """Get a metric by name."""
        with self.metrics_lock:
            return self.metrics.get(name)
    
    def get_all_metrics(self) -> List[Metric]:
        """Get all metrics."""
        with self.metrics_lock:
            return list(self.metrics.values())
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        with self.metrics_lock:
            metrics = list(self.metrics.values())
        
        summary = {
            "total_metrics": len(metrics),
            "metric_types": defaultdict(int),
            "total_values": 0,
            "oldest_timestamp": None,
            "newest_timestamp": None
        }
        
        all_timestamps = []
        
        for metric in metrics:
            summary["metric_types"][metric.type.value] += 1
            summary["total_values"] += len(metric.values)
            
            for value in metric.values:
                all_timestamps.append(value.timestamp)
        
        if all_timestamps:
            summary["oldest_timestamp"] = min(all_timestamps)
            summary["newest_timestamp"] = max(all_timestamps)
        
        return dict(summary)
    
    async def start_collection(self):
        """Start system metrics collection."""
        if self.is_collecting:
            return
        
        self.is_collecting = True
        self.collection_task = asyncio.create_task(self._collect_system_metrics())
    
    async def stop_collection(self):
        """Stop system metrics collection."""
        if not self.is_collecting:
            return
        
        self.is_collecting = False
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
    
    async def _collect_system_metrics(self):
        """Collect system metrics periodically."""
        while self.is_collecting:
            try:
                await self._collect_cpu_metrics()
                await self._collect_memory_metrics()
                await self._collect_disk_metrics()
                await self._collect_network_metrics()
                await self._collect_process_metrics()
                
                # Wait for next collection interval
                await asyncio.sleep(self.metrics_interval)
                
            except Exception as e:
                print(f"Error collecting system metrics: {e}")
                await asyncio.sleep(5)
    
    async def _collect_cpu_metrics(self):
        """Collect CPU metrics."""
        try:
            # CPU usage percentage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.set_gauge("system_cpu_usage_percent", cpu_percent)
            
            # CPU count
            cpu_count = psutil.cpu_count()
            self.set_gauge("system_cpu_count", cpu_count)
            
        except Exception as e:
            print(f"Error collecting CPU metrics: {e}")
    
    async def _collect_memory_metrics(self):
        """Collect memory metrics."""
        try:
            memory = psutil.virtual_memory()
            
            self.set_gauge("system_memory_usage_bytes", memory.used)
            self.set_gauge("system_memory_usage_percent", memory.percent)
            self.set_gauge("system_memory_available_bytes", memory.available)
            
        except Exception as e:
            print(f"Error collecting memory metrics: {e}")
    
    async def _collect_disk_metrics(self):
        """Collect disk metrics."""
        try:
            disk = psutil.disk_usage('/')
            
            self.set_gauge("system_disk_usage_bytes", disk.used)
            self.set_gauge("system_disk_usage_percent", (disk.used / disk.total) * 100)
            self.set_gauge("system_disk_free_bytes", disk.free)
            
        except Exception as e:
            print(f"Error collecting disk metrics: {e}")
    
    async def _collect_network_metrics(self):
        """Collect network metrics."""
        try:
            network = psutil.net_io_counters()
            
            self.record_value("system_network_bytes_sent", network.bytes_sent)
            self.record_value("system_network_bytes_recv", network.bytes_recv)
            
        except Exception as e:
            print(f"Error collecting network metrics: {e}")
    
    async def _collect_process_metrics(self):
        """Collect process metrics."""
        try:
            process_count = len(psutil.pids())
            self.set_gauge("system_process_count", process_count)
            
        except Exception as e:
            print(f"Error collecting process metrics: {e}")


class PerformanceTracker:
    """Performance tracking for application operations."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize performance tracker."""
        self.metrics_collector = metrics_collector
        self.operation_timers: Dict[str, float] = {}
    
    def start_operation(self, operation_name: str) -> str:
        """Start timing an operation."""
        timer_id = f"{operation_name}_{int(time.time() * 1000000)}"
        self.operation_timers[timer_id] = time.time()
        return timer_id
    
    def end_operation(self, timer_id: str, labels: Optional[Dict[str, str]] = None):
        """End timing an operation and record the duration."""
        if timer_id in self.operation_timers:
            start_time = self.operation_timers.pop(timer_id)
            duration = time.time() - start_time
            
            # Extract operation name from timer_id
            operation_name = timer_id.split('_')[0]
            metric_name = f"operation_duration_seconds"
            
            self.metrics_collector.record_timer(metric_name, duration, {
                "operation": operation_name,
                **(labels or {})
            })
    
    def record_event_processed(self, event_type: str, processing_time_ms: float,
                             entity_id: Optional[str] = None):
        """Record event processing metrics."""
        labels = {"event_type": event_type}
        if entity_id:
            labels["entity_id"] = entity_id
        
        self.metrics_collector.record_timer("event_processing_duration_seconds", 
                                          processing_time_ms / 1000, labels)
        self.metrics_collector.increment_counter("events_processed_total", 1, labels)
    
    def record_error(self, error_type: str, service: str):
        """Record error metrics."""
        self.metrics_collector.increment_counter("errors_total", 1, {
            "error_type": error_type,
            "service": service
        })
    
    def record_api_request(self, endpoint: str, method: str, status_code: int,
                          response_time_ms: float):
        """Record API request metrics."""
        self.metrics_collector.record_timer("api_request_duration_seconds", 
                                          response_time_ms / 1000, {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        })
        self.metrics_collector.increment_counter("api_requests_total", 1, {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        })


class MetricsService:
    """Main metrics service for the application."""
    
    def __init__(self):
        """Initialize metrics service."""
        self.collector = MetricsCollector()
        self.performance_tracker = PerformanceTracker(self.collector)
        self.is_running = False
        
        # Initialize application metrics
        self._initialize_application_metrics()
    
    def _initialize_application_metrics(self):
        """Initialize application-specific metrics."""
        # Event processing metrics
        self.collector.register_metric("events_processed_total", MetricType.COUNTER,
                                     "Total number of events processed", "count")
        self.collector.register_metric("event_processing_duration_seconds", MetricType.HISTOGRAM,
                                     "Time taken to process events", "seconds")
        
        # API metrics
        self.collector.register_metric("api_requests_total", MetricType.COUNTER,
                                     "Total number of API requests", "count")
        self.collector.register_metric("api_request_duration_seconds", MetricType.HISTOGRAM,
                                     "API request duration", "seconds")
        
        # Error metrics
        self.collector.register_metric("errors_total", MetricType.COUNTER,
                                     "Total number of errors", "count")
        
        # Service health metrics
        self.collector.register_metric("service_health_status", MetricType.GAUGE,
                                     "Service health status (1=healthy, 0=unhealthy)", "status")
        
        # Database metrics
        self.collector.register_metric("database_connections_active", MetricType.GAUGE,
                                     "Number of active database connections", "count")
        self.collector.register_metric("database_query_duration_seconds", MetricType.HISTOGRAM,
                                     "Database query duration", "seconds")
    
    async def start(self):
        """Start the metrics service."""
        if self.is_running:
            return
        
        await self.collector.start_collection()
        self.is_running = True
    
    async def stop(self):
        """Stop the metrics service."""
        if not self.is_running:
            return
        
        await self.collector.stop_collection()
        self.is_running = False
    
    def get_collector(self) -> MetricsCollector:
        """Get metrics collector."""
        return self.collector
    
    def get_performance_tracker(self) -> PerformanceTracker:
        """Get performance tracker."""
        return self.performance_tracker
    
    def get_metrics(self, metric_names: Optional[List[str]] = None) -> List[Metric]:
        """Get metrics."""
        if metric_names:
            return [self.collector.get_metric(name) for name in metric_names 
                   if self.collector.get_metric(name)]
        return self.collector.get_all_metrics()
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        return self.collector.get_metrics_summary()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current metric values."""
        metrics = self.collector.get_all_metrics()
        current_values = {}
        
        for metric in metrics:
            if metric.values:
                latest_value = metric.values[-1]
                current_values[metric.name] = {
                    "value": latest_value.value,
                    "timestamp": latest_value.timestamp,
                    "unit": metric.unit,
                    "type": metric.type.value
                }
        
        return current_values


# Global metrics service instance
metrics_service = MetricsService()
