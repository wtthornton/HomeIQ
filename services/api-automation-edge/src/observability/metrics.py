"""
Metrics Collection

Epic F2: Collect and emit metrics to InfluxDB
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from ..config import settings

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Collects and emits metrics to InfluxDB.
    
    Features:
    - Action success/failure by home, domain, automation ID, version
    - Decision latency (trigger → execute)
    - WebSocket disconnect rates, reconnect success, retries, breaker trips
    - Write to InfluxDB (match existing pattern from websocket-ingestion)
    """
    
    def __init__(
        self,
        influxdb_url: Optional[str] = None,
        influxdb_token: Optional[str] = None,
        influxdb_org: Optional[str] = None,
        influxdb_bucket: Optional[str] = None
    ):
        """
        Initialize metrics collector.
        
        Args:
            influxdb_url: InfluxDB URL (defaults to settings)
            influxdb_token: InfluxDB token (defaults to settings)
            influxdb_org: InfluxDB org (defaults to settings)
            influxdb_bucket: InfluxDB bucket (defaults to settings)
        """
        self.influxdb_url = influxdb_url or settings.influxdb_url
        self.influxdb_token = influxdb_token or settings.influxdb_token
        self.influxdb_org = influxdb_org or settings.influxdb_org
        self.influxdb_bucket = influxdb_bucket or settings.influxdb_bucket
        
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        
        if self.influxdb_url and self.influxdb_token:
            try:
                self.client = InfluxDBClient(
                    url=self.influxdb_url,
                    token=self.influxdb_token,
                    org=self.influxdb_org
                )
                self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
                logger.info("Metrics collector initialized with InfluxDB")
            except Exception as e:
                logger.warning(f"Failed to initialize InfluxDB client: {e}")
        else:
            logger.warning("InfluxDB not configured - metrics will not be collected")
    
    def record_action_metric(
        self,
        home_id: str,
        spec_id: str,
        spec_version: str,
        domain: str,
        success: bool,
        execution_time: float,
        correlation_id: Optional[str] = None
    ):
        """
        Record action execution metric.
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
            spec_version: Spec version
            domain: Service domain
            success: Whether action succeeded
            execution_time: Execution time in seconds
            correlation_id: Optional correlation ID
        """
        if not self.write_api:
            return
        
        try:
            point = Point("automation_action") \
                .tag("home_id", home_id) \
                .tag("spec_id", spec_id) \
                .tag("spec_version", spec_version) \
                .tag("domain", domain) \
                .tag("success", str(success).lower()) \
                .field("execution_time", execution_time) \
                .field("success", 1 if success else 0) \
                .time(datetime.now(timezone.utc))
            
            if correlation_id:
                point = point.tag("correlation_id", correlation_id)
            
            self.write_api.write(bucket=self.influxdb_bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to record action metric: {e}")
    
    def record_decision_latency(
        self,
        home_id: str,
        spec_id: str,
        latency: float,
        correlation_id: Optional[str] = None
    ):
        """
        Record decision latency (trigger → execute).
        
        Args:
            home_id: Home ID
            spec_id: Spec ID
            latency: Latency in seconds
            correlation_id: Optional correlation ID
        """
        if not self.write_api:
            return
        
        try:
            point = Point("automation_decision_latency") \
                .tag("home_id", home_id) \
                .tag("spec_id", spec_id) \
                .field("latency", latency) \
                .time(datetime.now(timezone.utc))
            
            if correlation_id:
                point = point.tag("correlation_id", correlation_id)
            
            self.write_api.write(bucket=self.influxdb_bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to record decision latency: {e}")
    
    def record_websocket_metric(
        self,
        home_id: str,
        metric_type: str,
        value: float,
        **tags
    ):
        """
        Record WebSocket metric.
        
        Args:
            home_id: Home ID
            metric_type: Metric type (disconnect_count, reconnect_latency, etc.)
            value: Metric value
            **tags: Additional tags
        """
        if not self.write_api:
            return
        
        try:
            point = Point("websocket_metrics") \
                .tag("home_id", home_id) \
                .tag("metric_type", metric_type) \
                .field("value", value) \
                .time(datetime.now(timezone.utc))
            
            for key, val in tags.items():
                point = point.tag(key, str(val))
            
            self.write_api.write(bucket=self.influxdb_bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to record WebSocket metric: {e}")
    
    def record_circuit_breaker_trip(
        self,
        home_id: str,
        breaker_id: str
    ):
        """Record circuit breaker trip"""
        if not self.write_api:
            return
        
        try:
            point = Point("circuit_breaker") \
                .tag("home_id", home_id) \
                .tag("breaker_id", breaker_id) \
                .field("tripped", 1) \
                .time(datetime.now(timezone.utc))
            
            self.write_api.write(bucket=self.influxdb_bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to record circuit breaker trip: {e}")
    
    def record_queue_metric(
        self,
        home_id: str,
        metric_type: str,
        value: float,
        **tags
    ):
        """
        Record task queue metric.
        
        Args:
            home_id: Home ID
            metric_type: Metric type (queue_depth, execution_time, success_rate, retry_count)
            value: Metric value
            **tags: Additional tags (spec_id, task_id, etc.)
        """
        if not self.write_api:
            return
        
        try:
            point = Point("automation_queue_metrics") \
                .tag("home_id", home_id) \
                .tag("metric_type", metric_type) \
                .field("value", value) \
                .time(datetime.now(timezone.utc))
            
            for key, val in tags.items():
                point = point.tag(key, str(val))
            
            self.write_api.write(bucket=self.influxdb_bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to record queue metric: {e}")
    
    def record_task_execution_metric(
        self,
        home_id: str,
        spec_id: str,
        task_id: str,
        success: bool,
        execution_time: float,
        retry_count: int = 0,
        correlation_id: Optional[str] = None
    ):
        """
        Record task execution metric.
        
        Args:
            home_id: Home ID
            spec_id: Automation spec ID
            task_id: Task ID
            success: Whether task succeeded
            execution_time: Execution time in seconds
            retry_count: Number of retries
            correlation_id: Optional correlation ID
        """
        if not self.write_api:
            return
        
        try:
            point = Point("automation_task_execution") \
                .tag("home_id", home_id) \
                .tag("spec_id", spec_id) \
                .tag("task_id", task_id) \
                .tag("success", str(success).lower()) \
                .field("execution_time", execution_time) \
                .field("success", 1 if success else 0) \
                .field("retry_count", retry_count) \
                .time(datetime.now(timezone.utc))
            
            if correlation_id:
                point = point.tag("correlation_id", correlation_id)
            
            self.write_api.write(bucket=self.influxdb_bucket, record=point)
            
        except Exception as e:
            logger.error(f"Failed to record task execution metric: {e}")
    
    def close(self):
        """Close InfluxDB client"""
        if self.client:
            self.client.close()
            logger.info("Metrics collector closed")
