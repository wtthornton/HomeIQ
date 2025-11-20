"""
Memory Manager for High-Volume Event Processing
"""

import asyncio
import gc
import logging
import weakref
from collections import deque
from datetime import datetime
from typing import Any

import psutil

logger = logging.getLogger(__name__)


class MemoryManager:
    """Memory management and monitoring for high-volume processing"""

    def __init__(self,
                 max_memory_mb: int = 1024,
                 memory_check_interval: float = 30.0,
                 gc_threshold: float = 0.8):
        """
        Initialize memory manager
        
        Args:
            max_memory_mb: Maximum memory usage in MB
            memory_check_interval: Interval for memory checks in seconds
            gc_threshold: Threshold for garbage collection (0.0 to 1.0)
        """
        self.max_memory_mb = max_memory_mb
        self.memory_check_interval = memory_check_interval
        self.gc_threshold = gc_threshold

        # Memory monitoring
        self.memory_samples: deque = deque(maxlen=100)
        self.gc_count_samples: deque = deque(maxlen=100)
        self.memory_alerts: deque = deque(maxlen=50)

        # Memory management
        self.weak_references: list[weakref.ref] = []
        self.memory_cleanup_callbacks: list[callable] = []

        # Statistics
        self.total_gc_runs = 0
        self.total_memory_cleanups = 0
        self.monitoring_start_time = datetime.now()

        # Monitoring task
        self.monitoring_task: asyncio.Task | None = None
        self.is_running = False

        # Memory usage tracking
        self.process = psutil.Process()

    async def start(self):
        """Start memory monitoring"""
        if self.is_running:
            logger.warning("Memory manager is already running")
            return

        self.is_running = True
        self.monitoring_start_time = datetime.now()

        # Start monitoring task
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info(f"Started memory manager with max_memory={self.max_memory_mb}MB, "
                   f"check_interval={self.memory_check_interval}s")

    async def stop(self):
        """Stop memory monitoring"""
        if not self.is_running:
            return

        self.is_running = False

        # Cancel monitoring task
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped memory manager")

    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.is_running:
            try:
                # Check memory usage
                await self._check_memory_usage()

                # Wait for next check
                await asyncio.sleep(self.memory_check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in memory monitoring loop: {e}")

    async def _check_memory_usage(self):
        """Check current memory usage and take action if needed"""
        try:
            # Get current memory usage
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024

            # Record memory sample
            self.memory_samples.append({
                "timestamp": datetime.now(),
                "memory_mb": memory_mb,
                "memory_percent": self.process.memory_percent()
            })

            # Check if memory usage exceeds threshold
            if memory_mb > self.max_memory_mb:
                await self._handle_memory_overflow(memory_mb)

            # Check if garbage collection is needed
            if memory_mb > self.max_memory_mb * self.gc_threshold:
                await self._run_garbage_collection()

        except Exception as e:
            logger.error(f"Error checking memory usage: {e}")

    async def _handle_memory_overflow(self, current_memory_mb: float):
        """Handle memory overflow"""
        logger.warning(f"Memory overflow detected: {current_memory_mb:.2f}MB > {self.max_memory_mb}MB")

        # Record alert
        alert = {
            "timestamp": datetime.now(),
            "type": "memory_overflow",
            "current_memory_mb": current_memory_mb,
            "max_memory_mb": self.max_memory_mb,
            "excess_mb": current_memory_mb - self.max_memory_mb
        }
        self.memory_alerts.append(alert)

        # Run cleanup
        await self._run_memory_cleanup()

        # Force garbage collection
        await self._run_garbage_collection()

    async def _run_garbage_collection(self):
        """Run garbage collection"""
        try:
            # Get GC counts before
            gc_counts_before = gc.get_count()

            # Run garbage collection
            collected = gc.collect()

            # Get GC counts after
            gc_counts_after = gc.get_count()

            # Record GC run
            self.gc_count_samples.append({
                "timestamp": datetime.now(),
                "collected": collected,
                "counts_before": gc_counts_before,
                "counts_after": gc_counts_after
            })

            self.total_gc_runs += 1

            logger.debug(f"Garbage collection: collected {collected} objects")

        except Exception as e:
            logger.error(f"Error running garbage collection: {e}")

    async def _run_memory_cleanup(self):
        """Run memory cleanup"""
        try:
            # Call registered cleanup callbacks
            for callback in self.memory_cleanup_callbacks:
                try:
                    await callback()
                except Exception as e:
                    logger.error(f"Error in memory cleanup callback: {e}")

            # Clean up weak references
            self._cleanup_weak_references()

            self.total_memory_cleanups += 1

            logger.debug("Memory cleanup completed")

        except Exception as e:
            logger.error(f"Error running memory cleanup: {e}")

    def _cleanup_weak_references(self):
        """Clean up dead weak references"""
        alive_refs = []
        for ref in self.weak_references:
            if ref() is not None:
                alive_refs.append(ref)

        cleaned_count = len(self.weak_references) - len(alive_refs)
        self.weak_references = alive_refs

        if cleaned_count > 0:
            logger.debug(f"Cleaned up {cleaned_count} dead weak references")

    def add_weak_reference(self, obj):
        """Add a weak reference to an object"""
        ref = weakref.ref(obj)
        self.weak_references.append(ref)
        return ref

    def add_cleanup_callback(self, callback: callable):
        """Add a memory cleanup callback"""
        self.memory_cleanup_callbacks.append(callback)
        logger.debug(f"Added memory cleanup callback: {callback.__name__}")

    def remove_cleanup_callback(self, callback: callable):
        """Remove a memory cleanup callback"""
        if callback in self.memory_cleanup_callbacks:
            self.memory_cleanup_callbacks.remove(callback)
            logger.debug(f"Removed memory cleanup callback: {callback.__name__}")

    def get_memory_statistics(self) -> dict[str, Any]:
        """Get memory statistics"""
        try:
            # Get current memory info
            memory_info = self.process.memory_info()
            current_memory_mb = memory_info.rss / 1024 / 1024
            current_memory_percent = self.process.memory_percent()

            # Calculate average memory usage
            avg_memory_mb = 0
            if self.memory_samples:
                avg_memory_mb = sum(sample["memory_mb"] for sample in self.memory_samples) / len(self.memory_samples)

            # Calculate memory trend
            memory_trend = "stable"
            if len(self.memory_samples) >= 2:
                recent_samples = list(self.memory_samples)[-5:]  # Last 5 samples
                if len(recent_samples) >= 2:
                    first_memory = recent_samples[0]["memory_mb"]
                    last_memory = recent_samples[-1]["memory_mb"]
                    if last_memory > first_memory * 1.1:
                        memory_trend = "increasing"
                    elif last_memory < first_memory * 0.9:
                        memory_trend = "decreasing"

            # Calculate GC statistics
            total_collected = 0
            if self.gc_count_samples:
                total_collected = sum(sample["collected"] for sample in self.gc_count_samples)

            # Calculate uptime
            uptime = (datetime.now() - self.monitoring_start_time).total_seconds()

            return {
                "is_running": self.is_running,
                "current_memory_mb": round(current_memory_mb, 2),
                "current_memory_percent": round(current_memory_percent, 2),
                "max_memory_mb": self.max_memory_mb,
                "memory_utilization_percent": round((current_memory_mb / self.max_memory_mb) * 100, 2),
                "average_memory_mb": round(avg_memory_mb, 2),
                "memory_trend": memory_trend,
                "total_gc_runs": self.total_gc_runs,
                "total_collected_objects": total_collected,
                "total_memory_cleanups": self.total_memory_cleanups,
                "weak_references_count": len(self.weak_references),
                "cleanup_callbacks_count": len(self.memory_cleanup_callbacks),
                "memory_alerts_count": len(self.memory_alerts),
                "uptime_seconds": round(uptime, 2),
                "gc_threshold": self.gc_threshold,
                "memory_check_interval": self.memory_check_interval
            }

        except Exception as e:
            logger.error(f"Error getting memory statistics: {e}")
            return {"error": str(e)}

    def get_memory_alerts(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent memory alerts"""
        return list(self.memory_alerts)[-limit:] if self.memory_alerts else []

    def configure_memory_limits(self, max_memory_mb: int, gc_threshold: float):
        """Configure memory limits"""
        if max_memory_mb <= 0:
            raise ValueError("max_memory_mb must be positive")
        if not 0.0 <= gc_threshold <= 1.0:
            raise ValueError("gc_threshold must be between 0.0 and 1.0")

        self.max_memory_mb = max_memory_mb
        self.gc_threshold = gc_threshold

        logger.info(f"Updated memory limits: max_memory={max_memory_mb}MB, gc_threshold={gc_threshold}")

    def configure_monitoring_interval(self, interval: float):
        """Configure monitoring interval"""
        if interval <= 0:
            raise ValueError("interval must be positive")

        self.memory_check_interval = interval
        logger.info(f"Updated monitoring interval to {interval}s")

    def reset_statistics(self):
        """Reset memory statistics"""
        self.memory_samples.clear()
        self.gc_count_samples.clear()
        self.memory_alerts.clear()
        self.total_gc_runs = 0
        self.total_memory_cleanups = 0
        self.monitoring_start_time = datetime.now()
        logger.info("Memory statistics reset")
