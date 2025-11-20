"""
Event Queue System for High-Volume Event Processing
"""

import asyncio
import json
import logging
import os
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EventQueue:
    """High-performance event queue with overflow handling and persistence"""

    def __init__(self, maxsize: int = 10000, persistence_path: str | None = None):
        """
        Initialize event queue
        
        Args:
            maxsize: Maximum queue size
            persistence_path: Path for queue persistence (optional)
        """
        self.maxsize = maxsize
        self.persistence_path = persistence_path

        # Queue management
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        self.overflow_queue: deque = deque(maxlen=maxsize)  # For overflow events

        # Statistics
        self.total_events_received = 0
        self.total_events_processed = 0
        self.total_events_dropped = 0
        self.overflow_events = 0

        # Performance monitoring
        self.queue_size_history: deque = deque(maxlen=100)
        self.processing_rate_history: deque = deque(maxlen=100)
        self.last_processing_time: datetime | None = None

        # Health monitoring
        self.health_check_interval = 60  # seconds
        self.last_health_check = datetime.now()

        # Persistence
        if self.persistence_path:
            self._ensure_persistence_directory()

    def _ensure_persistence_directory(self):
        """Ensure persistence directory exists"""
        if self.persistence_path:
            Path(self.persistence_path).mkdir(parents=True, exist_ok=True)

    async def put(self, event_data: dict[str, Any], priority: int = 0) -> bool:
        """
        Put an event in the queue
        
        Args:
            event_data: Event data to queue
            priority: Event priority (higher = more important)
            
        Returns:
            True if event was queued successfully, False otherwise
        """
        self.total_events_received += 1

        # Create queue item with metadata
        queue_item = {
            "data": event_data,
            "priority": priority,
            "timestamp": datetime.now().isoformat(),
            "id": f"{self.total_events_received}_{datetime.now().timestamp()}"
        }

        try:
            # Try to put in main queue
            self.queue.put_nowait(queue_item)
            return True

        except asyncio.QueueFull:
            # Queue is full, handle overflow
            return await self._handle_overflow(queue_item)

    async def _handle_overflow(self, queue_item: dict[str, Any]) -> bool:
        """Handle queue overflow"""
        self.overflow_events += 1

        # Add to overflow queue
        self.overflow_queue.append(queue_item)

        # Try to persist overflow events
        if self.persistence_path:
            await self._persist_overflow_event(queue_item)

        logger.warning(f"Queue overflow: {self.overflow_events} events in overflow")
        return False

    async def get(self) -> dict[str, Any] | None:
        """
        Get an event from the queue
        
        Returns:
            Event data or None if queue is empty
        """
        try:
            # Try to get from main queue first
            queue_item = await asyncio.wait_for(self.queue.get(), timeout=0.1)
            self.total_events_processed += 1
            self.last_processing_time = datetime.now()

            # Update queue size history
            self.queue_size_history.append(self.queue.qsize())

            return queue_item

        except asyncio.TimeoutError:
            # Try to get from overflow queue
            if self.overflow_queue:
                queue_item = self.overflow_queue.popleft()
                self.total_events_processed += 1
                self.last_processing_time = datetime.now()
                return queue_item

            return None

    async def get_nowait(self) -> dict[str, Any] | None:
        """
        Get an event from the queue without waiting
        
        Returns:
            Event data or None if queue is empty
        """
        try:
            # Try main queue first
            queue_item = self.queue.get_nowait()
            self.total_events_processed += 1
            self.last_processing_time = datetime.now()

            # Update queue size history
            self.queue_size_history.append(self.queue.qsize())

            return queue_item

        except asyncio.QueueEmpty:
            # Try overflow queue
            if self.overflow_queue:
                queue_item = self.overflow_queue.popleft()
                self.total_events_processed += 1
                self.last_processing_time = datetime.now()
                return queue_item

            return None

    async def _persist_overflow_event(self, queue_item: dict[str, Any]):
        """Persist overflow event to disk"""
        try:
            if not self.persistence_path:
                return

            # Create persistence file path
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"overflow_events_{timestamp}.jsonl"
            filepath = os.path.join(self.persistence_path, filename)

            # Append event to file
            with open(filepath, "a", encoding="utf-8") as f:
                f.write(json.dumps(queue_item) + "\n")

        except Exception as e:
            logger.error(f"Error persisting overflow event: {e}")

    async def recover_overflow_events(self) -> int:
        """
        Recover overflow events from persistence files
        
        Returns:
            Number of events recovered
        """
        if not self.persistence_path:
            return 0

        recovered_count = 0

        try:
            # Find overflow files
            overflow_files = list(Path(self.persistence_path).glob("overflow_events_*.jsonl"))

            for filepath in overflow_files:
                try:
                    with open(filepath, encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                queue_item = json.loads(line.strip())
                                self.overflow_queue.append(queue_item)
                                recovered_count += 1

                    # Remove processed file
                    filepath.unlink()

                except Exception as e:
                    logger.error(f"Error recovering from {filepath}: {e}")

            if recovered_count > 0:
                logger.info(f"Recovered {recovered_count} overflow events")

        except Exception as e:
            logger.error(f"Error recovering overflow events: {e}")

        return recovered_count

    def get_queue_statistics(self) -> dict[str, Any]:
        """Get queue statistics"""
        # Calculate processing rate
        processing_rate = 0
        if self.processing_rate_history:
            processing_rate = sum(self.processing_rate_history) / len(self.processing_rate_history)

        # Calculate average queue size
        avg_queue_size = 0
        if self.queue_size_history:
            avg_queue_size = sum(self.queue_size_history) / len(self.queue_size_history)

        # Calculate drop rate
        drop_rate = 0
        if self.total_events_received > 0:
            drop_rate = (self.total_events_dropped / self.total_events_received) * 100

        return {
            "queue_size": self.queue.qsize(),
            "queue_maxsize": self.queue.maxsize,
            "overflow_queue_size": len(self.overflow_queue),
            "total_events_received": self.total_events_received,
            "total_events_processed": self.total_events_processed,
            "total_events_dropped": self.total_events_dropped,
            "overflow_events": self.overflow_events,
            "drop_rate_percent": round(drop_rate, 2),
            "processing_rate_per_second": round(processing_rate, 2),
            "average_queue_size": round(avg_queue_size, 2),
            "last_processing_time": self.last_processing_time.isoformat() if self.last_processing_time else None,
            "persistence_enabled": self.persistence_path is not None,
            "persistence_path": self.persistence_path
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get queue health status"""
        current_size = self.queue.qsize()
        overflow_size = len(self.overflow_queue)

        # Determine health status
        if current_size >= self.maxsize * 0.9:
            health_status = "critical"
        elif current_size >= self.maxsize * 0.7 or overflow_size > 0:
            health_status = "warning"
        else:
            health_status = "healthy"

        return {
            "status": health_status,
            "queue_size": current_size,
            "queue_maxsize": self.maxsize,
            "overflow_size": overflow_size,
            "utilization_percent": round((current_size / self.maxsize) * 100, 2),
            "last_health_check": self.last_health_check.isoformat(),
            "persistence_enabled": self.persistence_path is not None
        }

    def configure_maxsize(self, maxsize: int):
        """Configure maximum queue size"""
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")

        self.maxsize = maxsize
        logger.info(f"Updated queue maxsize to {maxsize}")

    def configure_persistence(self, persistence_path: str | None):
        """Configure queue persistence"""
        self.persistence_path = persistence_path
        if persistence_path:
            self._ensure_persistence_directory()
            logger.info(f"Enabled queue persistence at {persistence_path}")
        else:
            logger.info("Disabled queue persistence")

    def reset_statistics(self):
        """Reset queue statistics"""
        self.total_events_received = 0
        self.total_events_processed = 0
        self.total_events_dropped = 0
        self.overflow_events = 0
        self.queue_size_history.clear()
        self.processing_rate_history.clear()
        self.last_processing_time = None
        logger.info("Queue statistics reset")
