"""
Storage Analytics
Track storage usage, retention operations, and cost savings
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any
from influxdb_client_3 import InfluxDBClient3, Point

logger = logging.getLogger(__name__)


class StorageAnalytics:
    """Monitor and analyze storage usage"""
    
    def __init__(self):
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://influxdb:8086')
        self.influxdb_token = os.getenv('INFLUXDB_TOKEN')
        self.influxdb_org = os.getenv('INFLUXDB_ORG', 'home_assistant')
        self.influxdb_bucket = os.getenv('INFLUXDB_BUCKET', 'events')
        
        self.client: InfluxDBClient3 = None
    
    def initialize(self):
        """Initialize InfluxDB client"""
        self.client = InfluxDBClient3(
            host=self.influxdb_url,
            token=self.influxdb_token,
            database=self.influxdb_bucket,
            org=self.influxdb_org
        )
    
    async def calculate_storage_metrics(self) -> Dict[str, Any]:
        """Calculate current storage metrics"""
        
        logger.info("Calculating storage metrics...")
        
        try:
            # Count records in each tier
            raw_count_query = '''
            SELECT COUNT(*) as count
            FROM home_assistant_events
            WHERE time >= NOW() - INTERVAL '7 days'
            '''
            
            hourly_count_query = '''
            SELECT COUNT(*) as count
            FROM hourly_aggregates
            '''
            
            daily_count_query = '''
            SELECT COUNT(*) as count
            FROM daily_aggregates
            '''
            
            raw_result = self.client.query(raw_count_query, language='sql', mode='pandas')
            hourly_result = self.client.query(hourly_count_query, language='sql', mode='pandas')
            daily_result = self.client.query(daily_count_query, language='sql', mode='pandas')
            
            raw_count = int(raw_result['count'].iloc[0]) if not raw_result.empty else 0
            hourly_count = int(hourly_result['count'].iloc[0]) if not hourly_result.empty else 0
            daily_count = int(daily_result['count'].iloc[0]) if not daily_result.empty else 0
            
            # Estimate storage sizes (rough)
            avg_event_size = 200  # bytes
            current_db_size_mb = (
                (raw_count * avg_event_size) +
                (hourly_count * 150) +
                (daily_count * 100)
            ) / (1024 * 1024)
            
            # Calculate what size would be without optimization
            events_per_day = 10000  # Typical
            days_retained = 365
            unoptimized_size_mb = (
                events_per_day * days_retained * avg_event_size
            ) / (1024 * 1024)
            
            storage_saved_mb = unoptimized_size_mb - current_db_size_mb
            reduction_percentage = (storage_saved_mb / unoptimized_size_mb) * 100 if unoptimized_size_mb > 0 else 0
            
            # Calculate cost savings
            cost_per_gb_month = 0.10  # Rough estimate
            annual_cost_savings = (storage_saved_mb / 1024) * cost_per_gb_month * 12
            
            metrics = {
                'current_db_size_mb': current_db_size_mb,
                'storage_saved_mb': storage_saved_mb,
                'reduction_percentage': reduction_percentage,
                'annual_cost_savings': annual_cost_savings,
                'raw_records': raw_count,
                'hourly_records': hourly_count,
                'daily_records': daily_count,
                'timestamp': datetime.now()
            }
            
            logger.info(f"Storage metrics: {current_db_size_mb:.0f}MB current, {reduction_percentage:.1f}% reduction")
            
            # Store metrics in InfluxDB
            point = Point("retention_metrics") \
                .field("current_db_size_mb", current_db_size_mb) \
                .field("storage_saved_mb", storage_saved_mb) \
                .field("reduction_percentage", reduction_percentage) \
                .field("annual_cost_savings", annual_cost_savings) \
                .field("raw_records", raw_count) \
                .field("hourly_records", hourly_count) \
                .field("daily_records", daily_count) \
                .time(datetime.now())
            
            self.client.write(point)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating storage metrics: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def log_retention_operation(
        self,
        operation_type: str,
        records_processed: int,
        storage_freed_mb: float,
        duration_seconds: float,
        errors: int = 0
    ):
        """Log retention operation for tracking"""
        
        try:
            point = Point("retention_operations") \
                .tag("operation_type", operation_type) \
                .field("records_processed", records_processed) \
                .field("storage_freed_mb", storage_freed_mb) \
                .field("duration_seconds", duration_seconds) \
                .field("errors", errors) \
                .field("success", errors == 0) \
                .time(datetime.now())
            
            self.client.write(point)
            
            logger.info(f"Logged {operation_type} operation: {records_processed} records, {storage_freed_mb:.1f}MB freed")
            
        except Exception as e:
            logger.error(f"Error logging operation: {e}")

