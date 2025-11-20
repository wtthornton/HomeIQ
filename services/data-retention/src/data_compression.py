"""Data compression and optimization service."""

import asyncio
import gzip
import json
import logging
import lzma
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

class CompressionAlgorithm(Enum):
    """Compression algorithm types."""
    GZIP = "gzip"
    LZMA = "lzma"
    ZLIB = "zlib"

@dataclass
class CompressionResult:
    """Result of a compression operation."""

    algorithm: CompressionAlgorithm
    original_size_bytes: int
    compressed_size_bytes: int
    compression_ratio: float
    compression_duration: float
    success: bool
    error_message: str | None = None
    compression_timestamp: datetime = None

    def __post_init__(self):
        if self.compression_timestamp is None:
            self.compression_timestamp = datetime.utcnow()

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "algorithm": self.algorithm.value,
            "original_size_bytes": self.original_size_bytes,
            "compressed_size_bytes": self.compressed_size_bytes,
            "compression_ratio": self.compression_ratio,
            "compression_duration": self.compression_duration,
            "success": self.success,
            "error_message": self.error_message,
            "compression_timestamp": self.compression_timestamp.isoformat(),
            "space_saved_bytes": self.original_size_bytes - self.compressed_size_bytes,
            "space_saved_percentage": (1 - self.compression_ratio) * 100
        }

class DataCompressionService:
    """Service for compressing and optimizing data storage."""

    def __init__(self, influxdb_client=None):
        """
        Initialize data compression service.
        
        Args:
            influxdb_client: InfluxDB client for data operations
        """
        self.influxdb_client = influxdb_client
        self.compression_history: list[CompressionResult] = []
        self.is_running = False
        self.compression_task: asyncio.Task | None = None

        # Compression settings
        self.compression_algorithms = [
            CompressionAlgorithm.GZIP,
            CompressionAlgorithm.LZMA,
            CompressionAlgorithm.ZLIB
        ]

        logger.info("Data compression service initialized")

    async def start(self) -> None:
        """Start the compression service."""
        if self.is_running:
            logger.warning("Compression service is already running")
            return

        self.is_running = True
        logger.info("Data compression service started")

    async def stop(self) -> None:
        """Stop the compression service."""
        if not self.is_running:
            return

        self.is_running = False

        if self.compression_task and not self.compression_task.done():
            self.compression_task.cancel()
            try:
                await self.compression_task
            except asyncio.CancelledError:
                pass

        logger.info("Data compression service stopped")

    async def compress_data(self, data: bytes, algorithm: CompressionAlgorithm) -> CompressionResult:
        """
        Compress data using specified algorithm.
        
        Args:
            data: Data to compress
            algorithm: Compression algorithm to use
            
        Returns:
            CompressionResult: Result of compression operation
        """
        start_time = datetime.utcnow()
        original_size = len(data)

        try:
            if algorithm == CompressionAlgorithm.GZIP:
                compressed_data = gzip.compress(data, compresslevel=9)
            elif algorithm == CompressionAlgorithm.LZMA:
                compressed_data = lzma.compress(data, preset=9)
            elif algorithm == CompressionAlgorithm.ZLIB:
                compressed_data = zlib.compress(data, level=9)
            else:
                raise ValueError(f"Unsupported compression algorithm: {algorithm}")

            compressed_size = len(compressed_data)
            compression_ratio = compressed_size / original_size
            compression_duration = (datetime.utcnow() - start_time).total_seconds()

            result = CompressionResult(
                algorithm=algorithm,
                original_size_bytes=original_size,
                compressed_size_bytes=compressed_size,
                compression_ratio=compression_ratio,
                compression_duration=compression_duration,
                success=True
            )

            self.compression_history.append(result)

            logger.info(f"Data compressed with {algorithm.value}: "
                       f"{original_size} -> {compressed_size} bytes "
                       f"({compression_ratio:.2%} ratio)")

            return result

        except Exception as e:
            compression_duration = (datetime.utcnow() - start_time).total_seconds()
            result = CompressionResult(
                algorithm=algorithm,
                original_size_bytes=original_size,
                compressed_size_bytes=0,
                compression_ratio=1.0,
                compression_duration=compression_duration,
                success=False,
                error_message=str(e)
            )

            self.compression_history.append(result)
            logger.error(f"Data compression failed with {algorithm.value}: {e}")

            return result

    async def find_best_compression(self, data: bytes) -> CompressionResult:
        """
        Find the best compression algorithm for given data.
        
        Args:
            data: Data to compress
            
        Returns:
            CompressionResult: Best compression result
        """
        best_result = None
        best_ratio = 1.0

        for algorithm in self.compression_algorithms:
            result = await self.compress_data(data, algorithm)

            if result.success and result.compression_ratio < best_ratio:
                best_ratio = result.compression_ratio
                best_result = result

        return best_result or CompressionResult(
            algorithm=CompressionAlgorithm.GZIP,
            original_size_bytes=len(data),
            compressed_size_bytes=len(data),
            compression_ratio=1.0,
            compression_duration=0.0,
            success=False,
            error_message="No compression algorithm succeeded"
        )

    async def compress_old_data(self, days_old: int = 30) -> list[CompressionResult]:
        """
        Compress old data in the database.
        
        Args:
            days_old: Age of data to compress in days
            
        Returns:
            List of compression results
        """
        results = []

        try:
            # Get old data from InfluxDB
            old_data = await self._get_old_data(days_old)

            for data_chunk in old_data:
                # Find best compression for this chunk
                result = await self.find_best_compression(data_chunk)
                results.append(result)

                # Apply compression to database if successful
                if result.success:
                    await self._apply_compression_to_database(data_chunk, result)

            logger.info(f"Compressed {len(results)} data chunks")

        except Exception as e:
            logger.error(f"Failed to compress old data: {e}")

        return results

    async def _get_old_data(self, days_old: int) -> list[bytes]:
        """
        Get old data from database.
        
        Args:
            days_old: Age of data to retrieve in days
            
        Returns:
            List of data chunks
        """
        if not self.influxdb_client:
            # Mock implementation for testing
            return [
                json.dumps({"timestamp": f"2024-01-{i:02d}T00:00:00Z", "value": i}).encode()
                for i in range(1, 11)
            ]

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            # Query InfluxDB for old data
            query = f"""
            from(bucket: "home-assistant-events")
                |> range(start: 1970-01-01T00:00:00Z, stop: {cutoff_date.isoformat()}Z)
                |> limit(n: 1000)
            """

            result = await self.influxdb_client.query(query)
            data_chunks = []

            for table in result:
                chunk_data = []
                for record in table.records:
                    chunk_data.append({
                        "timestamp": record.get_time().isoformat(),
                        "measurement": record.get_measurement(),
                        "field": record.get_field(),
                        "value": record.get_value(),
                        "tags": record.values
                    })

                if chunk_data:
                    data_chunks.append(json.dumps(chunk_data).encode())

            return data_chunks

        except Exception as e:
            logger.error(f"Failed to get old data: {e}")
            return []

    async def _apply_compression_to_database(self, data: bytes, result: CompressionResult) -> None:
        """
        Apply compression to database storage.
        
        Args:
            data: Original data
            result: Compression result
        """
        if not self.influxdb_client:
            return  # Mock implementation

        try:
            # In a real implementation, you would:
            # 1. Store compressed data in a separate compressed table
            # 2. Update metadata to indicate compression
            # 3. Remove original data if compression is successful

            logger.debug(f"Applied compression to database: {result.algorithm.value}")

        except Exception as e:
            logger.error(f"Failed to apply compression to database: {e}")

    async def schedule_compression(self, interval_hours: int = 24) -> None:
        """
        Schedule periodic data compression.
        
        Args:
            interval_hours: Interval between compression runs in hours
        """
        if self.compression_task and not self.compression_task.done():
            logger.warning("Compression task is already running")
            return

        async def compression_loop():
            while self.is_running:
                try:
                    logger.info("Starting scheduled compression")
                    results = await self.compress_old_data(days_old=30)

                    total_saved = sum(result.original_size_bytes - result.compressed_size_bytes
                                    for result in results if result.success)
                    logger.info(f"Scheduled compression completed: {total_saved} bytes saved")

                except Exception as e:
                    logger.error(f"Scheduled compression failed: {e}")

                # Wait for next compression cycle
                await asyncio.sleep(interval_hours * 3600)

        self.compression_task = asyncio.create_task(compression_loop())
        logger.info(f"Scheduled compression every {interval_hours} hours")

    def get_compression_history(self, limit: int = 100) -> list[CompressionResult]:
        """
        Get compression history.
        
        Args:
            limit: Maximum number of history entries to return
            
        Returns:
            List of compression results
        """
        return self.compression_history[-limit:] if self.compression_history else []

    def get_compression_statistics(self) -> dict[str, Any]:
        """
        Get compression statistics.
        
        Returns:
            Dictionary containing compression statistics
        """
        if not self.compression_history:
            return {
                "total_compressions": 0,
                "total_bytes_saved": 0,
                "average_compression_ratio": 1.0,
                "best_compression_ratio": 1.0,
                "success_rate": 0.0,
                "last_compression": None
            }

        successful_results = [result for result in self.compression_history if result.success]

        if not successful_results:
            return {
                "total_compressions": len(self.compression_history),
                "total_bytes_saved": 0,
                "average_compression_ratio": 1.0,
                "best_compression_ratio": 1.0,
                "success_rate": 0.0,
                "last_compression": self.compression_history[-1].compression_timestamp.isoformat()
            }

        total_bytes_saved = sum(
            result.original_size_bytes - result.compressed_size_bytes
            for result in successful_results
        )

        compression_ratios = [result.compression_ratio for result in successful_results]

        return {
            "total_compressions": len(self.compression_history),
            "successful_compressions": len(successful_results),
            "total_bytes_saved": total_bytes_saved,
            "average_compression_ratio": sum(compression_ratios) / len(compression_ratios),
            "best_compression_ratio": min(compression_ratios),
            "success_rate": len(successful_results) / len(self.compression_history),
            "last_compression": self.compression_history[-1].compression_timestamp.isoformat()
        }

    def get_algorithm_performance(self) -> dict[str, Any]:
        """
        Get performance statistics by algorithm.
        
        Returns:
            Dictionary containing algorithm performance statistics
        """
        algorithm_stats = {}

        for algorithm in self.compression_algorithms:
            algorithm_results = [
                result for result in self.compression_history
                if result.algorithm == algorithm and result.success
            ]

            if algorithm_results:
                ratios = [result.compression_ratio for result in algorithm_results]
                durations = [result.compression_duration for result in algorithm_results]

                algorithm_stats[algorithm.value] = {
                    "count": len(algorithm_results),
                    "average_ratio": sum(ratios) / len(ratios),
                    "best_ratio": min(ratios),
                    "average_duration": sum(durations) / len(durations),
                    "total_bytes_saved": sum(
                        result.original_size_bytes - result.compressed_size_bytes
                        for result in algorithm_results
                    )
                }
            else:
                algorithm_stats[algorithm.value] = {
                    "count": 0,
                    "average_ratio": 1.0,
                    "best_ratio": 1.0,
                    "average_duration": 0.0,
                    "total_bytes_saved": 0
                }

        return algorithm_stats
