#!/usr/bin/env python3
"""
Sync Devices from InfluxDB to PostgreSQL

This script reads discovered devices from InfluxDB and populates the PostgreSQL database
in the data-api service so the devices API endpoint works properly.
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, List

import aiohttp
from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DeviceSync:
    """Sync devices from InfluxDB to PostgreSQL via data API"""
    
    def __init__(self):
        # InfluxDB configuration
        self.influxdb_url = os.getenv("INFLUXDB_URL", "http://localhost:8086")
        self.influxdb_token = os.getenv("INFLUXDB_TOKEN", "homeiq-token")
        self.influxdb_org = os.getenv("INFLUXDB_ORG", "homeiq")
        self.influxdb_bucket = os.getenv("INFLUXDB_BUCKET", "home_assistant_events")
        
        # Data API configuration
        self.data_api_url = os.getenv("DATA_API_URL", "http://localhost:8006")
        
    async def sync_devices(self):
        """Sync devices from InfluxDB to PostgreSQL"""
        try:
            logger.info("Starting device sync from InfluxDB to PostgreSQL...")
            
            # Get devices from InfluxDB
            devices = await self._get_devices_from_influxdb()
            logger.info(f"Found {len(devices)} devices in InfluxDB")
            
            if not devices:
                logger.warning("No devices found in InfluxDB")
                return False
            
            # Store devices in PostgreSQL via data API
            success = await self._store_devices_in_pg(devices)
            
            if success:
                logger.info(f"Successfully synced {len(devices)} devices to PostgreSQL")
                return True
            else:
                logger.error("Failed to sync devices to PostgreSQL")
                return False
                
        except Exception as e:
            logger.error(f"Error during device sync: {e}")
            return False
    
    async def _get_devices_from_influxdb(self) -> List[Dict[str, Any]]:
        """Get devices from InfluxDB"""
        try:
            client = InfluxDBClient(
                url=self.influxdb_url,
                token=self.influxdb_token,
                org=self.influxdb_org
            )
            
            query_api = client.query_api()
            
            # Query devices from InfluxDB
            query = f'''
            from(bucket: "{self.influxdb_bucket}")
              |> range(start: -24h)
              |> filter(fn: (r) => r._measurement == "devices")
              |> group(columns: ["device_id"])
              |> first()
            '''
            
            result = query_api.query(query)
            
            devices = []
            for table in result:
                for record in table.records:
                    device_data = {
                        "device_id": record.values.get("device_id"),
                        "name": record.values.get("name"),
                        "manufacturer": record.values.get("manufacturer"),
                        "model": record.values.get("model"),
                        "sw_version": record.values.get("sw_version"),
                        "area_id": record.values.get("area_id"),
                        "last_seen": record.get_time()
                    }
                    devices.append(device_data)
            
            client.close()
            return devices
            
        except Exception as e:
            logger.error(f"Error getting devices from InfluxDB: {e}")
            return []
    
    async def _store_devices_in_pg(self, devices: List[Dict[str, Any]]) -> bool:
        """Store devices in PostgreSQL via data API bulk upsert endpoint."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.data_api_url}/internal/devices/bulk_upsert",
                    json=devices,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Stored {result.get('upserted', 0)} devices via data-api")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to store devices: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error storing devices in PostgreSQL: {e}")
            return False

async def main():
    """Main entry point"""
    logger.info("Starting device sync process...")
    
    sync = DeviceSync()
    success = await sync.sync_devices()
    
    if success:
        logger.info("Device sync completed successfully")
        sys.exit(0)
    else:
        logger.error("Device sync failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
