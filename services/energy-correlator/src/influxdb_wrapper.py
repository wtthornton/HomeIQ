"""
InfluxDB Wrapper for Energy Correlator
Uses InfluxDB v2 client for queries (compatible with InfluxDB 2.7)
"""

import asyncio
import logging
from typing import Dict, List, Optional
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import ASYNCHRONOUS
from influxdb_client.rest import ApiException

logger = logging.getLogger(__name__)


class InfluxDBWrapper:
    """Wrapper for InfluxDB operations using v2 client"""
    
    def __init__(
        self,
        influxdb_url: str,
        influxdb_token: str,
        influxdb_org: str,
        influxdb_bucket: str
    ):
        self.influxdb_url = influxdb_url
        self.influxdb_token = influxdb_token
        self.influxdb_org = influxdb_org
        self.influxdb_bucket = influxdb_bucket
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api = None
    
    def connect(self):
        """Initialize InfluxDB connection"""
        try:
            self.client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.query_api = self.client.query_api()
            
            logger.info(f"Connected to InfluxDB at {self.influxdb_url}")
            
        except Exception as e:
            logger.error(f"Failed to connect to InfluxDB: {e}")
            raise
    
    def close(self):
        """Close InfluxDB connection"""
        if self.client:
            try:
                if self.write_api:
                    self.write_api.close()
                self.client.close()
                logger.info("InfluxDB connection closed")
            except Exception as e:
                logger.error(f"Error closing InfluxDB connection: {e}")
    
    def _execute_query(self, flux_query: str) -> List[Dict]:
        tables = self.query_api.query(flux_query, org=self.influxdb_org)
        
        results: List[Dict] = []
        for table in tables:
            for record in table.records:
                result = {
                    'time': record.get_time()
                }
                
                for key, value in record.values.items():
                    if key not in ['result', 'table']:
                        result[key] = value
                
                results.append(result)
        
        return results
    
    async def query(self, flux_query: str) -> List[Dict]:
        """
        Execute Flux query asynchronously and return results
        """
        try:
            return await asyncio.to_thread(self._execute_query, flux_query)
        except ApiException as e:
            logger.exception(f"InfluxDB API error executing query: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error executing query: {e}")
            raise
    
    def _write_points_blocking(self, points: List[Point]):
        self.write_api.write(
            bucket=self.influxdb_bucket,
            org=self.influxdb_org,
            record=points
        )
    
    async def write_points(self, points: List[Point]):
        """
        Write a batch of points to InfluxDB asynchronously
        
        Args:
            points: List of InfluxDB Point objects
        """
        if not points:
            return
        
        try:
            await asyncio.to_thread(self._write_points_blocking, points)
        except ApiException as e:
            logger.exception(f"InfluxDB API error writing points: {e}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error writing points: {e}")
            raise

