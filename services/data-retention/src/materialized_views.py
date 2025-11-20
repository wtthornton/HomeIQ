"""
Materialized Views Manager
Creates and manages pre-computed aggregates for fast queries
"""

import logging
import os
from datetime import datetime
from typing import Any

from influxdb_client_3 import InfluxDBClient3

logger = logging.getLogger(__name__)


class MaterializedViewManager:
    """Manage materialized views for fast query performance"""

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

    async def create_daily_energy_view(self):
        """Create materialized view for daily energy by device"""

        logger.info("Creating daily energy by device view...")

        # In InfluxDB 3.0, we use continuous aggregates via tasks
        # This creates a new measurement with pre-computed data

        query = '''
        SELECT
            entity_id,
            DATE_TRUNC('day', time) as day,
            SUM(energy_consumption) as total_kwh,
            AVG(normalized_value) as avg_power,
            MAX(normalized_value) as peak_power,
            SUM(energy_consumption * 0.12) as cost_usd
        FROM home_assistant_events
        WHERE time >= NOW() - INTERVAL '30 days'
        AND energy_consumption > 0
        GROUP BY entity_id, DATE_TRUNC('day', time)
        '''

        # Execute and store in new measurement
        result = self.client.query(query, language='sql', mode='pandas')

        if not result.empty:
            # Write to materialized view measurement
            for _, row in result.iterrows():
                from influxdb_client_3 import Point

                point = Point("mv_daily_energy_by_device") \
                    .tag("entity_id", row['entity_id']) \
                    .field("total_kwh", float(row['total_kwh'])) \
                    .field("avg_power", float(row['avg_power'])) \
                    .field("peak_power", float(row['peak_power'])) \
                    .field("cost_usd", float(row['cost_usd'])) \
                    .time(row['day'])

                self.client.write(point)

            logger.info(f"Created/updated daily energy view with {len(result)} records")

    async def create_hourly_room_activity_view(self):
        """Create materialized view for hourly room activity"""

        logger.info("Creating hourly room activity view...")

        query = '''
        SELECT
            area,
            EXTRACT(HOUR FROM time) as hour,
            EXTRACT(DOW FROM time) as day_of_week,
            COUNT(*) as motion_count,
            AVG(CASE WHEN state_value = 'on' THEN 1.0 ELSE 0.0 END) as occupancy_rate
        FROM home_assistant_events
        WHERE time >= NOW() - INTERVAL '90 days'
        AND domain = 'binary_sensor'
        AND device_class = 'motion'
        GROUP BY area, EXTRACT(HOUR FROM time), EXTRACT(DOW FROM time)
        '''

        result = self.client.query(query, language='sql', mode='pandas')

        if not result.empty:
            from influxdb_client_3 import Point

            for _, row in result.iterrows():
                point = Point("mv_hourly_room_activity") \
                    .tag("area", row['area']) \
                    .field("hour", int(row['hour'])) \
                    .field("day_of_week", int(row['day_of_week'])) \
                    .field("motion_count", int(row['motion_count'])) \
                    .field("occupancy_rate", float(row['occupancy_rate'])) \
                    .time(datetime.now())

                self.client.write(point)

            logger.info(f"Created/updated hourly room activity view with {len(result)} records")

    async def create_daily_carbon_summary_view(self):
        """Create materialized view for daily carbon summary"""

        logger.info("Creating daily carbon summary view...")

        query = '''
        SELECT
            DATE_TRUNC('day', time) as day,
            AVG(carbon_intensity_gco2_kwh) as avg_carbon,
            MIN(carbon_intensity_gco2_kwh) as min_carbon,
            MAX(carbon_intensity_gco2_kwh) as max_carbon,
            AVG(renewable_percentage) as avg_renewable
        FROM carbon_intensity
        WHERE time >= NOW() - INTERVAL '90 days'
        GROUP BY DATE_TRUNC('day', time)
        '''

        result = self.client.query(query, language='sql', mode='pandas')

        if not result.empty:
            from influxdb_client_3 import Point

            for _, row in result.iterrows():
                point = Point("mv_daily_carbon_summary") \
                    .field("avg_carbon", float(row['avg_carbon'])) \
                    .field("min_carbon", float(row['min_carbon'])) \
                    .field("max_carbon", float(row['max_carbon'])) \
                    .field("avg_renewable", float(row['avg_renewable'])) \
                    .time(row['day'])

                self.client.write(point)

            logger.info(f"Created/updated daily carbon summary view with {len(result)} records")

    async def refresh_all_views(self):
        """Refresh all materialized views"""

        logger.info("Refreshing all materialized views...")

        start_time = datetime.now()

        try:
            await self.create_daily_energy_view()
            await self.create_hourly_room_activity_view()
            await self.create_daily_carbon_summary_view()

            duration = (datetime.now() - start_time).total_seconds()
            logger.info(f"All views refreshed in {duration:.2f}s")

            return {
                'status': 'success',
                'duration_seconds': duration,
                'views_refreshed': 3,
                'timestamp': datetime.now()
            }

        except Exception as e:
            logger.error(f"Error refreshing views: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'timestamp': datetime.now()
            }

    async def query_view(self, view_name: str, filters: dict[str, Any] = None) -> list[dict]:
        """Query materialized view (fast)"""

        query = f"SELECT * FROM {view_name}"

        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, str):
                    conditions.append(f"{key} = '{value}'")
                else:
                    conditions.append(f"{key} = {value}")

            if conditions:
                query += f" WHERE {' AND '.join(conditions)}"

        query += " ORDER BY time DESC LIMIT 1000"

        result = self.client.query(query, language='sql', mode='pandas')

        return result.to_dict('records') if not result.empty else []

    async def benchmark_performance(self):
        """Benchmark query performance improvement"""

        import time

        # Original complex query
        original_query = '''
        SELECT 
            entity_id,
            DATE_TRUNC('day', time) as day,
            SUM(energy_consumption) as total_kwh
        FROM home_assistant_events
        WHERE time >= NOW() - INTERVAL '30 days'
        AND energy_consumption > 0
        GROUP BY entity_id, DATE_TRUNC('day', time)
        '''

        # Time original query
        start = time.time()
        self.client.query(original_query, language='sql', mode='pandas')
        original_time = (time.time() - start) * 1000  # ms

        # Time materialized view query
        start = time.time()
        await self.query_view("mv_daily_energy_by_device")
        view_time = (time.time() - start) * 1000  # ms

        improvement = original_time / view_time if view_time > 0 else 0

        logger.info("Query performance:")
        logger.info(f"  Original: {original_time:.0f}ms")
        logger.info(f"  View: {view_time:.0f}ms")
        logger.info(f"  Improvement: {improvement:.1f}x faster")

        return {
            'original_ms': original_time,
            'view_ms': view_time,
            'improvement_factor': improvement
        }

