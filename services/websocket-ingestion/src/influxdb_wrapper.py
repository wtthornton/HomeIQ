"""
InfluxDB Client for Time-Series Data Storage
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

try:
    from influxdb_client import InfluxDBClient, Point, WritePrecision
    from influxdb_client.client.exceptions import InfluxDBError
    from influxdb_client.client.write_api import ASYNCHRONOUS, SYNCHRONOUS
except ImportError:
    # Fallback for development without InfluxDB
    InfluxDBClient = None
    Point = None
    WritePrecision = None
    SYNCHRONOUS = None
    ASYNCHRONOUS = None
    InfluxDBError = Exception

logger = logging.getLogger(__name__)


class InfluxDBConnectionManager:
    """Manages InfluxDB connection with automatic reconnection"""

    def __init__(self,
                 url: str,
                 token: str,
                 org: str,
                 bucket: str,
                 timeout: int = 30,
                 retry_attempts: int = 3,
                 retry_delay: float = 1.0):
        """
        Initialize InfluxDB connection manager
        
        Args:
            url: InfluxDB server URL
            token: InfluxDB authentication token
            org: InfluxDB organization
            bucket: InfluxDB bucket name
            timeout: Connection timeout in seconds
            retry_attempts: Number of retry attempts on failure
            retry_delay: Delay between retry attempts in seconds
        """
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay

        # Connection management
        self.client: InfluxDBClient | None = None
        self.write_api = None
        self.query_api = None
        self.is_connected = False

        # Statistics
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.last_connection_time: datetime | None = None
        self.last_error: str | None = None

        # Health monitoring
        self.last_health_check: datetime | None = None
        self.health_check_interval = 60  # seconds
        self.health_check_task: asyncio.Task | None = None
        self.is_running = False

    async def start(self):
        """Start the InfluxDB connection manager"""
        if self.is_running:
            logger.warning("InfluxDB connection manager is already running")
            return

        self.is_running = True

        # Start connection
        await self._connect()

        # Start health check task
        self.health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info("InfluxDB connection manager started")

    async def stop(self):
        """Stop the InfluxDB connection manager"""
        if not self.is_running:
            return

        self.is_running = False

        # Stop health check task
        if self.health_check_task:
            self.health_check_task.cancel()
            try:
                await self.health_check_task
            except asyncio.CancelledError:
                pass

        # Close connection
        await self._disconnect()

        logger.info("InfluxDB connection manager stopped")

    async def _connect(self) -> bool:
        """Establish connection to InfluxDB"""
        try:
            self.connection_attempts += 1

            # Create InfluxDB client
            self.client = InfluxDBClient(
                url=self.url,
                token=self.token,
                org=self.org,
                timeout=self.timeout * 1000  # Convert to milliseconds
            )

            # Test connection
            await self._test_connection()

            # Initialize APIs
            self.write_api = self.client.write_api(write_options=ASYNCHRONOUS)
            self.query_api = self.client.query_api()

            self.is_connected = True
            self.successful_connections += 1
            self.last_connection_time = datetime.now()
            self.last_error = None

            logger.info("Successfully connected to InfluxDB")
            return True

        except Exception as e:
            self.failed_connections += 1
            self.last_error = str(e)
            self.is_connected = False

            logger.error(f"Failed to connect to InfluxDB: {e}")
            return False

    async def _test_connection(self):
        """Test InfluxDB connection using health check endpoint"""
        if not self.client:
            raise Exception("Client not initialized")

        # Test connection using the health check endpoint (more reliable than Flux queries)
        import aiohttp

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.url}/health", timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                    if response.status == 200:
                        logger.debug("InfluxDB health check passed")
                        return
                    else:
                        raise Exception(f"InfluxDB health check failed with status {response.status}")
        except Exception as e:
            # Fallback to simple ping endpoint
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{self.url}/ping", timeout=aiohttp.ClientTimeout(total=self.timeout)) as response:
                        if response.status == 204:  # Ping returns 204 No Content on success
                            logger.debug("InfluxDB ping check passed")
                            return
                        else:
                            raise Exception(f"InfluxDB ping check failed with status {response.status}")
            except Exception as ping_error:
                raise Exception(f"InfluxDB connection test failed: {e}, ping also failed: {ping_error}")

    async def _disconnect(self):
        """Disconnect from InfluxDB"""
        try:
            if self.write_api:
                self.write_api.close()
                self.write_api = None

            if self.query_api:
                self.query_api = None

            if self.client:
                self.client.close()
                self.client = None

            self.is_connected = False
            logger.info("Disconnected from InfluxDB")

        except Exception as e:
            logger.error(f"Error disconnecting from InfluxDB: {e}")

    async def _health_check_loop(self):
        """Health check loop"""
        while self.is_running:
            try:
                await asyncio.sleep(self.health_check_interval)

                if not self.is_running:
                    break

                await self._perform_health_check()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def _perform_health_check(self):
        """Perform health check"""
        try:
            if not self.is_connected:
                # Try to reconnect
                await self._connect()
            else:
                # Test existing connection
                await self._test_connection()

            self.last_health_check = datetime.now()

        except Exception as e:
            logger.warning(f"InfluxDB health check failed: {e}")
            self.is_connected = False

    async def write_points(self, points: list[Point]) -> bool:
        """
        Write points to InfluxDB
        
        Args:
            points: List of InfluxDB Point objects
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected or not self.write_api:
            logger.error("InfluxDB not connected")
            return False

        try:
            # Write points asynchronously
            await asyncio.to_thread(
                self.write_api.write,
                bucket=self.bucket,
                org=self.org,
                record=points
            )

            logger.debug(f"Successfully wrote {len(points)} points to InfluxDB")
            return True

        except Exception as e:
            logger.error(f"Error writing points to InfluxDB: {e}")
            self.last_error = str(e)
            return False

    async def query_data(self, query: str) -> list[dict[str, Any]]:
        """
        Query data from InfluxDB
        
        Args:
            query: InfluxDB query string
            
        Returns:
            List of query results
        """
        if not self.is_connected or not self.query_api:
            logger.error("InfluxDB not connected")
            return []

        try:
            # Execute query
            result = await asyncio.to_thread(
                self.query_api.query,
                query,
                org=self.org
            )

            # Convert result to list of dictionaries
            data = []
            for table in result:
                for record in table.records:
                    data.append({
                        "time": record.get_time(),
                        "measurement": record.get_measurement(),
                        "tags": record.values,
                        "fields": record.values
                    })

            logger.debug(f"Successfully queried {len(data)} records from InfluxDB")
            return data

        except Exception as e:
            logger.error(f"Error querying InfluxDB: {e}")
            self.last_error = str(e)
            return []

    async def write_device(self, device_point: dict[str, Any], bucket: str = None) -> bool:
        """
        Write device data to InfluxDB
        
        Args:
            device_point: Device data in InfluxDB point format
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            True if successful, False otherwise
        """
        target_bucket = bucket or self.bucket

        try:
            point = Point(device_point["measurement"])

            # Add tags
            for tag_key, tag_value in device_point["tags"].items():
                point = point.tag(tag_key, tag_value)

            # Add fields
            for field_key, field_value in device_point["fields"].items():
                point = point.field(field_key, field_value)

            # Add timestamp
            if "time" in device_point:
                point = point.time(device_point["time"], WritePrecision.S)

            return await self._write_point_to_bucket(point, target_bucket)

        except Exception as e:
            logger.error(f"Error writing device to InfluxDB: {e}")
            return False

    async def write_entity(self, entity_point: dict[str, Any], bucket: str = None) -> bool:
        """
        Write entity data to InfluxDB
        
        Args:
            entity_point: Entity data in InfluxDB point format
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            True if successful, False otherwise
        """
        target_bucket = bucket or self.bucket

        try:
            point = Point(entity_point["measurement"])

            # Add tags
            for tag_key, tag_value in entity_point["tags"].items():
                point = point.tag(tag_key, tag_value)

            # Add fields
            for field_key, field_value in entity_point["fields"].items():
                point = point.field(field_key, field_value)

            # Add timestamp
            if "time" in entity_point:
                point = point.time(entity_point["time"], WritePrecision.S)

            return await self._write_point_to_bucket(point, target_bucket)

        except Exception as e:
            logger.error(f"Error writing entity to InfluxDB: {e}")
            return False

    async def batch_write_devices(self, device_points: list[dict[str, Any]], bucket: str = None) -> bool:
        """
        Batch write multiple devices to InfluxDB
        
        Args:
            device_points: List of device data in InfluxDB point format
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            True if successful, False otherwise
        """
        target_bucket = bucket or self.bucket

        try:
            points = []
            for device_point in device_points:
                point = Point(device_point["measurement"])

                for tag_key, tag_value in device_point["tags"].items():
                    point = point.tag(tag_key, tag_value)

                for field_key, field_value in device_point["fields"].items():
                    point = point.field(field_key, field_value)

                if "time" in device_point:
                    point = point.time(device_point["time"], WritePrecision.S)

                points.append(point)

            return await self._write_points_to_bucket(points, target_bucket)

        except Exception as e:
            logger.error(f"Error batch writing devices to InfluxDB: {e}")
            return False

    async def batch_write_entities(self, entity_points: list[dict[str, Any]], bucket: str = None) -> bool:
        """
        Batch write multiple entities to InfluxDB
        
        Args:
            entity_points: List of entity data in InfluxDB point format
            bucket: Bucket name (defaults to self.bucket)
            
        Returns:
            True if successful, False otherwise
        """
        target_bucket = bucket or self.bucket

        try:
            points = []
            for entity_point in entity_points:
                point = Point(entity_point["measurement"])

                for tag_key, tag_value in entity_point["tags"].items():
                    point = point.tag(tag_key, tag_value)

                for field_key, field_value in entity_point["fields"].items():
                    point = point.field(field_key, field_value)

                if "time" in entity_point:
                    point = point.time(entity_point["time"], WritePrecision.S)

                points.append(point)

            return await self._write_points_to_bucket(points, target_bucket)

        except Exception as e:
            logger.error(f"Error batch writing entities to InfluxDB: {e}")
            return False

    async def _write_point_to_bucket(self, point: Point, bucket: str) -> bool:
        """Helper to write a single point to specified bucket"""
        if not self.is_connected or not self.write_api:
            logger.error("InfluxDB not connected")
            return False

        try:
            await asyncio.to_thread(
                self.write_api.write,
                bucket=bucket,
                org=self.org,
                record=point
            )
            return True
        except Exception as e:
            logger.error(f"Error writing point to bucket {bucket}: {e}")
            return False

    async def _write_points_to_bucket(self, points: list[Point], bucket: str) -> bool:
        """Helper to write multiple points to specified bucket"""
        if not self.is_connected or not self.write_api:
            logger.error("InfluxDB not connected")
            return False

        try:
            await asyncio.to_thread(
                self.write_api.write,
                bucket=bucket,
                org=self.org,
                record=points
            )
            logger.info(f"Successfully wrote {len(points)} points to bucket {bucket}")
            return True
        except Exception as e:
            logger.error(f"Error writing {len(points)} points to bucket {bucket}: {e}")
            return False

    async def query_devices(self, filters: dict[str, Any] = None, bucket: str = "devices") -> list[dict[str, Any]]:
        """
        Query devices from InfluxDB
        
        Args:
            filters: Optional filters (manufacturer, model, area_id)
            bucket: Bucket name (defaults to 'devices')
            
        Returns:
            List of device dictionaries
        """
        filters = filters or {}

        # Build Flux query
        query = f'''
            from(bucket: "{bucket}")
                |> range(start: -90d)
                |> filter(fn: (r) => r["_measurement"] == "devices")
        '''

        # Add filters
        if filters.get("manufacturer"):
            query += f'\n    |> filter(fn: (r) => r["manufacturer"] == "{filters["manufacturer"]}")'
        if filters.get("model"):
            query += f'\n    |> filter(fn: (r) => r["model"] == "{filters["model"]}")'
        if filters.get("area_id"):
            query += f'\n    |> filter(fn: (r) => r["area_id"] == "{filters["area_id"]}")'

        query += '\n    |> last()'

        return await self.query_data(query)

    async def query_entities(self, filters: dict[str, Any] = None, bucket: str = "entities") -> list[dict[str, Any]]:
        """
        Query entities from InfluxDB
        
        Args:
            filters: Optional filters (domain, platform, device_id)
            bucket: Bucket name (defaults to 'entities')
            
        Returns:
            List of entity dictionaries
        """
        filters = filters or {}

        # Build Flux query
        query = f'''
            from(bucket: "{bucket}")
                |> range(start: -90d)
                |> filter(fn: (r) => r["_measurement"] == "entities")
        '''

        # Add filters
        if filters.get("domain"):
            query += f'\n    |> filter(fn: (r) => r["domain"] == "{filters["domain"]}")'
        if filters.get("platform"):
            query += f'\n    |> filter(fn: (r) => r["platform"] == "{filters["platform"]}")'
        if filters.get("device_id"):
            query += f'\n    |> filter(fn: (r) => r["device_id"] == "{filters["device_id"]}")'

        query += '\n    |> last()'

        return await self.query_data(query)

    def get_connection_status(self) -> dict[str, Any]:
        """Get connection status"""
        return {
            "is_connected": self.is_connected,
            "url": self.url,
            "org": self.org,
            "bucket": self.bucket,
            "connection_attempts": self.connection_attempts,
            "successful_connections": self.successful_connections,
            "failed_connections": self.failed_connections,
            "last_connection_time": self.last_connection_time.isoformat() if self.last_connection_time else None,
            "last_error": self.last_error,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "health_check_interval": self.health_check_interval,
            "timeout": self.timeout,
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay
        }

    def configure_health_check_interval(self, interval: int):
        """Configure health check interval"""
        if interval <= 0:
            raise ValueError("Health check interval must be positive")

        self.health_check_interval = interval
        logger.info(f"Updated health check interval to {interval}s")

    def configure_retry_settings(self, attempts: int, delay: float):
        """Configure retry settings"""
        if attempts < 0:
            raise ValueError("Retry attempts must be non-negative")
        if delay < 0:
            raise ValueError("Retry delay must be non-negative")

        self.retry_attempts = attempts
        self.retry_delay = delay
        logger.info(f"Updated retry settings: attempts={attempts}, delay={delay}s")

    def reset_statistics(self):
        """Reset connection statistics"""
        self.connection_attempts = 0
        self.successful_connections = 0
        self.failed_connections = 0
        self.last_connection_time = None
        self.last_error = None
        self.last_health_check = None
        logger.info("InfluxDB connection statistics reset")
