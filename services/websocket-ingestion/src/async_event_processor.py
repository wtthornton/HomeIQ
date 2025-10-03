"""
Async Event Processor for High-Volume Event Processing
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timedelta
from collections import deque
import weakref

logger = logging.getLogger(__name__)


class AsyncEventProcessor:
    """High-performance async event processor with concurrent handling"""
    
    def __init__(self, max_workers: int = 10, processing_rate_limit: int = 1000):
        """
        Initialize async event processor
        
        Args:
            max_workers: Maximum number of concurrent processing workers
            processing_rate_limit: Maximum events per second to process
        """
        self.max_workers = max_workers
        self.processing_rate_limit = processing_rate_limit
        
        # Processing statistics
        self.processed_events = 0
        self.failed_events = 0
        self.processing_start_time = datetime.now()
        self.last_processing_time: Optional[datetime] = None
        
        # Rate limiting
        self.rate_limiter = RateLimiter(processing_rate_limit)
        
        # Worker management
        self.workers: List[asyncio.Task] = []
        self.is_running = False
        self.event_queue: asyncio.Queue = asyncio.Queue(maxsize=10000)
        
        # Event handlers
        self.event_handlers: List[Callable] = []
        
        # Performance monitoring
        self.processing_times: deque = deque(maxlen=1000)  # Keep last 1000 processing times
        self.memory_usage_samples: deque = deque(maxlen=100)  # Keep last 100 memory samples
        
    async def start(self):
        """Start the async event processor"""
        if self.is_running:
            logger.warning("Event processor is already running")
            return
        
        self.is_running = True
        self.processing_start_time = datetime.now()
        
        # Start worker tasks
        for i in range(self.max_workers):
            worker_task = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker_task)
        
        logger.info(f"Started async event processor with {self.max_workers} workers")
    
    async def stop(self):
        """Stop the async event processor"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()
        
        logger.info("Stopped async event processor")
    
    async def process_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Queue an event for processing
        
        Args:
            event_data: Event data to process
            
        Returns:
            True if event was queued successfully, False otherwise
        """
        try:
            # Apply rate limiting
            if not await self.rate_limiter.acquire():
                logger.warning("Rate limit exceeded, dropping event")
                return False
            
            # Try to put event in queue
            self.event_queue.put_nowait(event_data)
            return True
            
        except asyncio.QueueFull:
            logger.warning("Event queue is full, dropping event")
            return False
        except Exception as e:
            logger.error(f"Error queuing event: {e}")
            return False
    
    async def _worker(self, worker_name: str):
        """Worker task for processing events"""
        logger.debug(f"Started worker {worker_name}")
        
        while self.is_running:
            try:
                # Get event from queue with timeout
                event_data = await asyncio.wait_for(
                    self.event_queue.get(), 
                    timeout=1.0
                )
                
                # Process the event
                start_time = datetime.now()
                await self._process_single_event(event_data)
                processing_time = (datetime.now() - start_time).total_seconds()
                
                # Record processing time
                self.processing_times.append(processing_time)
                
                # Mark task as done
                self.event_queue.task_done()
                
            except asyncio.TimeoutError:
                # No events to process, continue
                continue
            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                self.failed_events += 1
        
        logger.debug(f"Worker {worker_name} stopped")
    
    async def _process_single_event(self, event_data: Dict[str, Any]):
        """Process a single event"""
        try:
            # Call registered handlers
            for handler in self.event_handlers:
                try:
                    await handler(event_data)
                except Exception as e:
                    logger.error(f"Error in event handler: {e}")
            
            self.processed_events += 1
            self.last_processing_time = datetime.now()
            
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            self.failed_events += 1
    
    def add_event_handler(self, handler: Callable):
        """Add an event handler"""
        self.event_handlers.append(handler)
        logger.debug(f"Added event handler: {handler.__name__}")
    
    def remove_event_handler(self, handler: Callable):
        """Remove an event handler"""
        if handler in self.event_handlers:
            self.event_handlers.remove(handler)
            logger.debug(f"Removed event handler: {handler.__name__}")
    
    def configure_processing_rate(self, rate_limit: int):
        """Configure processing rate limit"""
        self.processing_rate_limit = rate_limit
        self.rate_limiter = RateLimiter(rate_limit)
        logger.info(f"Updated processing rate limit to {rate_limit} events/second")
    
    def configure_max_workers(self, max_workers: int):
        """Configure maximum number of workers"""
        if self.is_running:
            logger.warning("Cannot change max_workers while processor is running")
            return
        
        self.max_workers = max_workers
        logger.info(f"Updated max_workers to {max_workers}")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        uptime = (datetime.now() - self.processing_start_time).total_seconds()
        
        # Calculate average processing time
        avg_processing_time = 0
        if self.processing_times:
            avg_processing_time = sum(self.processing_times) / len(self.processing_times)
        
        # Calculate processing rate
        processing_rate = 0
        if uptime > 0:
            processing_rate = self.processed_events / uptime
        
        # Calculate success rate
        total_events = self.processed_events + self.failed_events
        success_rate = (self.processed_events / total_events * 100) if total_events > 0 else 0
        
        return {
            "is_running": self.is_running,
            "max_workers": self.max_workers,
            "active_workers": len([w for w in self.workers if not w.done()]),
            "processing_rate_limit": self.processing_rate_limit,
            "processed_events": self.processed_events,
            "failed_events": self.failed_events,
            "success_rate": round(success_rate, 2),
            "processing_rate_per_second": round(processing_rate, 2),
            "average_processing_time_ms": round(avg_processing_time * 1000, 2),
            "queue_size": self.event_queue.qsize(),
            "queue_maxsize": self.event_queue.maxsize,
            "uptime_seconds": round(uptime, 2),
            "last_processing_time": self.last_processing_time.isoformat() if self.last_processing_time else None,
            "event_handlers_count": len(self.event_handlers)
        }
    
    def reset_statistics(self):
        """Reset processing statistics"""
        self.processed_events = 0
        self.failed_events = 0
        self.processing_start_time = datetime.now()
        self.last_processing_time = None
        self.processing_times.clear()
        self.memory_usage_samples.clear()
        logger.info("Processing statistics reset")


class RateLimiter:
    """Rate limiter for controlling processing rate"""
    
    def __init__(self, rate_limit: int):
        """
        Initialize rate limiter
        
        Args:
            rate_limit: Maximum events per second
        """
        self.rate_limit = rate_limit
        self.tokens = rate_limit
        self.last_update = datetime.now()
        self.lock = asyncio.Lock()
    
    async def acquire(self) -> bool:
        """
        Acquire a token for processing
        
        Returns:
            True if token was acquired, False if rate limit exceeded
        """
        async with self.lock:
            now = datetime.now()
            time_passed = (now - self.last_update).total_seconds()
            
            # Add tokens based on time passed
            self.tokens = min(self.rate_limit, self.tokens + time_passed * self.rate_limit)
            self.last_update = now
            
            if self.tokens >= 1:
                self.tokens -= 1
                return True
            
            return False
