"""
InfluxDB Batch Writer for Optimal Performance
"""

import asyncio
import logging
from collections import deque
from collections.abc import Callable
from datetime import datetime
from typing import Any

try:
    from influxdb_client import Point
except ImportError:
    Point = None

from .influxdb_schema import InfluxDBSchema
from .influxdb_wrapper import InfluxDBConnectionManager

logger = logging.getLogger(__name__)


class InfluxDBBatchWriter:
    """High-performance batch writer for InfluxDB"""

    def __init__(self,
                 connection_manager: InfluxDBConnectionManager,
                 batch_size: int = 1000,
                 batch_timeout: float = 5.0,
                 max_retries: int = 3,
                 retry_delay: float = 1.0,
                 max_pending_points: int = 20000,
                 overflow_strategy: str = "drop_oldest"):
        """
        Initialize InfluxDB batch writer
        
        Args:
            connection_manager: InfluxDB connection manager
            batch_size: Maximum number of points per batch
            batch_timeout: Maximum time to wait before processing partial batch (seconds)
            max_retries: Maximum number of retry attempts
            retry_delay: Delay between retry attempts (seconds)
        """
        self.connection_manager = connection_manager
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.max_pending_points = max_pending_points
        self.overflow_strategy = overflow_strategy

        # Schema for point creation
        self.schema = InfluxDBSchema()

        # Batch management
        self.current_batch: list[Point] = []
        self.batch_start_time: datetime | None = None
        self.batch_lock = asyncio.Lock()

        # Processing statistics
        self.total_batches_written = 0
        self.total_points_written = 0
        self.total_points_failed = 0
        self.processing_start_time = datetime.now()

        # Performance monitoring
        self.batch_write_times: deque = deque(maxlen=100)
        self.batch_sizes: deque = deque(maxlen=100)
        self.write_rates: deque = deque(maxlen=100)

        # Processing task
        self.processing_task: asyncio.Task | None = None
        self.is_running = False

        # Error handling
        self.error_callbacks: list[Callable] = []
        self.queue_overflow_events = 0
        self.dropped_points = 0

    async def start(self):
        """Start the batch writer"""
        if self.is_running:
            logger.warning("InfluxDB batch writer is already running")
            return

        self.is_running = True
        self.processing_start_time = datetime.now()

        # Start processing task
        self.processing_task = asyncio.create_task(self._processing_loop())

        logger.info(f"Started InfluxDB batch writer with batch_size={self.batch_size}, timeout={self.batch_timeout}s")

    async def stop(self):
        """Stop the batch writer"""
        if not self.is_running:
            return

        self.is_running = False

        # Process any remaining points
        await self._process_current_batch()

        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped InfluxDB batch writer")

    async def write_event(self, event_data: dict[str, Any]) -> bool:
        """
        Write event data to InfluxDB
        
        Args:
            event_data: Event data to write
            
        Returns:
            True if event was queued successfully, False otherwise
        """
        try:
            # Create InfluxDB point from event data
            point = self.schema.create_event_point(event_data)
            if not point:
                logger.warning("Failed to create InfluxDB point from event data")
                return False

            return await self._enqueue_point(point)

        except Exception as e:
            logger.error(f"Error writing event to InfluxDB: {e}")
            return False

    async def write_weather_data(self, weather_data: dict[str, Any], location: str) -> bool:
        """
        Write weather data to InfluxDB
        
        Args:
            weather_data: Weather data to write
            location: Location string
            
        Returns:
            True if weather data was queued successfully, False otherwise
        """
        try:
            # Create InfluxDB point from weather data
            point = self.schema.create_weather_point(weather_data, location)
            if not point:
                logger.warning("Failed to create InfluxDB point from weather data")
                return False

            return await self._enqueue_point(point)

        except Exception as e:
            logger.error(f"Error writing weather data to InfluxDB: {e}")
            return False

    async def _processing_loop(self):
        """Main processing loop"""
        while self.is_running:
            try:
                # Wait for batch timeout
                await asyncio.sleep(self.batch_timeout)

                # Process current batch if it has points
                await self._process_current_batch()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")

    async def _process_current_batch(self):
        """Process the current batch"""
        batch_to_process = await self._drain_current_batch()
        if not batch_to_process:
            return

        await self._process_batch_with_metrics(batch_to_process)

    async def _enqueue_point(self, point: Point) -> bool:
        batch_to_process: list[Point] | None = None

        async with self.batch_lock:
            if not self._apply_backpressure_locked():
                logger.error(
                    "InfluxDB batch queue is full; dropping new point per overflow strategy %s",
                    self.overflow_strategy,
                )
                return False

            self.current_batch.append(point)

            if len(self.current_batch) >= self.batch_size:
                batch_to_process = self._drain_current_batch_locked()
            elif self.batch_start_time is None:
                self.batch_start_time = datetime.now()

        if batch_to_process:
            await self._process_batch_with_metrics(batch_to_process)

        return True

    async def _drain_current_batch(self) -> list[Point]:
        async with self.batch_lock:
            return self._drain_current_batch_locked()

    def _drain_current_batch_locked(self) -> list[Point]:
        batch_to_process = self.current_batch.copy()
        self.current_batch.clear()
        self.batch_start_time = None
        return batch_to_process

    def _apply_backpressure_locked(self) -> bool:
        if self.max_pending_points <= 0:
            return True

        if len(self.current_batch) < self.max_pending_points:
            return True

        self.queue_overflow_events += 1

        overflow = len(self.current_batch) - self.max_pending_points + 1
        if self.overflow_strategy == "drop_oldest":
            dropped = min(overflow, len(self.current_batch))
            self.dropped_points += dropped
            del self.current_batch[:dropped]
            logger.warning(
                "Backpressure triggered: dropped %s oldest points to stay under %s pending limit",
                dropped,
                self.max_pending_points,
            )
            return True

        if self.overflow_strategy == "drop_new":
            self.dropped_points += 1
            logger.error(
                "Backpressure triggered: rejecting newest point because queue exceeded %s entries",
                self.max_pending_points,
            )
            return False

        logger.warning(
            "Unknown overflow strategy %s; defaulting to drop_oldest",
            self.overflow_strategy,
        )
        self.overflow_strategy = "drop_oldest"
        return self._apply_backpressure_locked()

    async def _process_batch_with_metrics(self, batch_to_process: list[Point]):
        if not batch_to_process:
            return

        start_time = datetime.now()
        success = await self._write_batch(batch_to_process)
        write_time = (datetime.now() - start_time).total_seconds()

        self.batch_write_times.append(write_time)
        self.batch_sizes.append(len(batch_to_process))

        if success:
            self.total_batches_written += 1
            self.total_points_written += len(batch_to_process)
        else:
            self.total_points_failed += len(batch_to_process)

        if write_time > 0:
            rate = len(batch_to_process) / write_time
            self.write_rates.append(rate)

    async def _write_batch(self, batch: list[Point]) -> bool:
        """
        Write a batch of points to InfluxDB
        
        Args:
            batch: List of InfluxDB points to write
            
        Returns:
            True if batch was written successfully, False otherwise
        """
        for attempt in range(self.max_retries):
            try:
                # Validate points before writing
                valid_points = []
                for point in batch:
                    is_valid, errors = self.schema.validate_point(point)
                    if is_valid:
                        valid_points.append(point)
                    else:
                        logger.warning(f"Invalid point: {errors}")

                if not valid_points:
                    logger.error("No valid points in batch")
                    return False

                # Write points to InfluxDB
                success = await self.connection_manager.write_points(valid_points)

                if success:
                    logger.debug(f"Successfully wrote batch of {len(valid_points)} points to InfluxDB")
                    return True
                else:
                    logger.error(f"Failed to write batch to InfluxDB (attempt {attempt + 1})")

                    if attempt < self.max_retries - 1:
                        # Wait before retry
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                    else:
                        # All retries failed
                        logger.error(f"Failed to write batch after {self.max_retries} attempts")
                        return False

            except Exception as e:
                logger.error(f"Error writing batch (attempt {attempt + 1}): {e}")

                if attempt < self.max_retries - 1:
                    # Wait before retry
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    # All retries failed
                    logger.error(f"Failed to write batch after {self.max_retries} attempts")
                    return False

        return False

    def add_error_callback(self, callback: Callable):
        """Add error callback"""
        self.error_callbacks.append(callback)
        logger.debug(f"Added error callback: {callback.__name__}")

    def remove_error_callback(self, callback: Callable):
        """Remove error callback"""
        if callback in self.error_callbacks:
            self.error_callbacks.remove(callback)
            logger.debug(f"Removed error callback: {callback.__name__}")

    def configure_batch_size(self, batch_size: int):
        """Configure batch size"""
        if batch_size <= 0:
            raise ValueError("batch_size must be positive")

        self.batch_size = batch_size
        logger.info(f"Updated batch size to {batch_size}")

    def configure_batch_timeout(self, timeout: float):
        """Configure batch timeout"""
        if timeout <= 0:
            raise ValueError("timeout must be positive")

        self.batch_timeout = timeout
        logger.info(f"Updated batch timeout to {timeout}s")

    def configure_retry_settings(self, max_retries: int, retry_delay: float):
        """Configure retry settings"""
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if retry_delay < 0:
            raise ValueError("retry_delay must be non-negative")

        self.max_retries = max_retries
        self.retry_delay = retry_delay
        logger.info(f"Updated retry settings: max_retries={max_retries}, retry_delay={retry_delay}s")

    def get_writing_statistics(self) -> dict[str, Any]:
        """Get writing statistics"""
        uptime = (datetime.now() - self.processing_start_time).total_seconds()

        # Calculate average batch size
        avg_batch_size = 0
        if self.batch_sizes:
            avg_batch_size = sum(self.batch_sizes) / len(self.batch_sizes)

        # Calculate average write time
        avg_write_time = 0
        if self.batch_write_times:
            avg_write_time = sum(self.batch_write_times) / len(self.batch_write_times)

        # Calculate average write rate
        avg_write_rate = 0
        if self.write_rates:
            avg_write_rate = sum(self.write_rates) / len(self.write_rates)

        # Calculate overall write rate
        overall_rate = 0
        if uptime > 0:
            overall_rate = self.total_points_written / uptime

        # Calculate success rate
        total_points = self.total_points_written + self.total_points_failed
        success_rate = (self.total_points_written / total_points * 100) if total_points > 0 else 0

        return {
            "is_running": self.is_running,
            "batch_size": self.batch_size,
            "batch_timeout": self.batch_timeout,
            "current_batch_size": len(self.current_batch),
            "total_batches_written": self.total_batches_written,
            "total_points_written": self.total_points_written,
            "total_points_failed": self.total_points_failed,
            "success_rate": round(success_rate, 2),
            "average_batch_size": round(avg_batch_size, 2),
            "average_write_time_ms": round(avg_write_time * 1000, 2),
            "average_write_rate_per_second": round(avg_write_rate, 2),
            "overall_write_rate_per_second": round(overall_rate, 2),
            "uptime_seconds": round(uptime, 2),
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "error_callbacks_count": len(self.error_callbacks),
            "max_pending_points": self.max_pending_points,
            "overflow_strategy": self.overflow_strategy,
            "queue_overflow_events": self.queue_overflow_events,
            "dropped_points": self.dropped_points
        }

    def reset_statistics(self):
        """Reset writing statistics"""
        self.total_batches_written = 0
        self.total_points_written = 0
        self.total_points_failed = 0
        self.processing_start_time = datetime.now()
        self.batch_write_times.clear()
        self.batch_sizes.clear()
        self.write_rates.clear()
        self.queue_overflow_events = 0
        self.dropped_points = 0
        logger.info("InfluxDB batch writer statistics reset")

    def configure_queue_limits(self, max_pending_points: int, overflow_strategy: str = "drop_oldest"):
        """Update queue/backpressure configuration"""
        if max_pending_points <= 0:
            raise ValueError("max_pending_points must be positive")

        self.max_pending_points = max_pending_points
        self.overflow_strategy = overflow_strategy
        logger.info(
            "Updated queue limits: max_pending_points=%s, overflow_strategy=%s",
            max_pending_points,
            overflow_strategy,
        )
