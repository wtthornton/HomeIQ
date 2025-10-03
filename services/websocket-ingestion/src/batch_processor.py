"""
Batch Processor for High-Volume Event Processing
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from collections import deque
import json

logger = logging.getLogger(__name__)


class BatchProcessor:
    """High-performance batch processor for database operations"""
    
    def __init__(self, batch_size: int = 100, batch_timeout: float = 5.0):
        """
        Initialize batch processor
        
        Args:
            batch_size: Maximum number of events per batch
            batch_timeout: Maximum time to wait before processing partial batch (seconds)
        """
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        
        # Batch management
        self.current_batch: List[Dict[str, Any]] = []
        self.batch_start_time: Optional[datetime] = None
        self.batch_lock = asyncio.Lock()
        
        # Processing statistics
        self.total_batches_processed = 0
        self.total_events_processed = 0
        self.total_events_failed = 0
        self.processing_start_time = datetime.now()
        
        # Performance monitoring
        self.batch_processing_times: deque = deque(maxlen=100)
        self.batch_sizes: deque = deque(maxlen=100)
        self.processing_rates: deque = deque(maxlen=100)
        
        # Batch handlers
        self.batch_handlers: List[Callable] = []
        
        # Processing task
        self.processing_task: Optional[asyncio.Task] = None
        self.is_running = False
        
        # Error handling
        self.retry_attempts = 3
        self.retry_delay = 1.0  # seconds
    
    async def start(self):
        """Start the batch processor"""
        if self.is_running:
            logger.warning("Batch processor is already running")
            return
        
        self.is_running = True
        self.processing_start_time = datetime.now()
        
        # Start processing task
        self.processing_task = asyncio.create_task(self._processing_loop())
        
        logger.info(f"Started batch processor with batch_size={self.batch_size}, timeout={self.batch_timeout}s")
    
    async def stop(self):
        """Stop the batch processor"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Process any remaining events
        await self._process_current_batch()
        
        # Cancel processing task
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Stopped batch processor")
    
    async def add_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Add an event to the current batch
        
        Args:
            event_data: Event data to add to batch
            
        Returns:
            True if event was added successfully, False otherwise
        """
        async with self.batch_lock:
            # Add event to current batch
            self.current_batch.append(event_data)
            
            # Check if batch is full
            if len(self.current_batch) >= self.batch_size:
                await self._process_current_batch()
                return True
            
            # Set batch start time if this is the first event
            if self.batch_start_time is None:
                self.batch_start_time = datetime.now()
            
            return True
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.is_running:
            try:
                # Wait for batch timeout
                await asyncio.sleep(self.batch_timeout)
                
                # Process current batch if it has events
                async with self.batch_lock:
                    if self.current_batch:
                        await self._process_current_batch()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
    
    async def _process_current_batch(self):
        """Process the current batch"""
        if not self.current_batch:
            return
        
        batch_to_process = self.current_batch.copy()
        self.current_batch.clear()
        self.batch_start_time = None
        
        if not batch_to_process:
            return
        
        # Process the batch
        start_time = datetime.now()
        success = await self._process_batch(batch_to_process)
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Update statistics
        self.batch_processing_times.append(processing_time)
        self.batch_sizes.append(len(batch_to_process))
        
        if success:
            self.total_batches_processed += 1
            self.total_events_processed += len(batch_to_process)
        else:
            self.total_events_failed += len(batch_to_process)
        
        # Calculate processing rate
        if processing_time > 0:
            rate = len(batch_to_process) / processing_time
            self.processing_rates.append(rate)
    
    async def _process_batch(self, batch: List[Dict[str, Any]]) -> bool:
        """
        Process a batch of events
        
        Args:
            batch: List of events to process
            
        Returns:
            True if batch was processed successfully, False otherwise
        """
        for attempt in range(self.retry_attempts):
            try:
                # Call registered batch handlers
                for handler in self.batch_handlers:
                    await handler(batch)
                
                logger.debug(f"Successfully processed batch of {len(batch)} events")
                return True
                
            except Exception as e:
                logger.error(f"Error processing batch (attempt {attempt + 1}): {e}")
                
                if attempt < self.retry_attempts - 1:
                    # Wait before retry
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    # All retries failed
                    logger.error(f"Failed to process batch after {self.retry_attempts} attempts")
                    return False
        
        return False
    
    def add_batch_handler(self, handler: Callable):
        """Add a batch handler"""
        self.batch_handlers.append(handler)
        logger.debug(f"Added batch handler: {handler.__name__}")
    
    def remove_batch_handler(self, handler: Callable):
        """Remove a batch handler"""
        if handler in self.batch_handlers:
            self.batch_handlers.remove(handler)
            logger.debug(f"Removed batch handler: {handler.__name__}")
    
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
    
    def configure_retry_settings(self, attempts: int, delay: float):
        """Configure retry settings"""
        if attempts < 0:
            raise ValueError("attempts must be non-negative")
        if delay < 0:
            raise ValueError("delay must be non-negative")
        
        self.retry_attempts = attempts
        self.retry_delay = delay
        logger.info(f"Updated retry settings: attempts={attempts}, delay={delay}s")
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """Get processing statistics"""
        uptime = (datetime.now() - self.processing_start_time).total_seconds()
        
        # Calculate average batch size
        avg_batch_size = 0
        if self.batch_sizes:
            avg_batch_size = sum(self.batch_sizes) / len(self.batch_sizes)
        
        # Calculate average processing time
        avg_processing_time = 0
        if self.batch_processing_times:
            avg_processing_time = sum(self.batch_processing_times) / len(self.batch_processing_times)
        
        # Calculate average processing rate
        avg_processing_rate = 0
        if self.processing_rates:
            avg_processing_rate = sum(self.processing_rates) / len(self.processing_rates)
        
        # Calculate overall processing rate
        overall_rate = 0
        if uptime > 0:
            overall_rate = self.total_events_processed / uptime
        
        # Calculate success rate
        total_events = self.total_events_processed + self.total_events_failed
        success_rate = (self.total_events_processed / total_events * 100) if total_events > 0 else 0
        
        return {
            "is_running": self.is_running,
            "batch_size": self.batch_size,
            "batch_timeout": self.batch_timeout,
            "current_batch_size": len(self.current_batch),
            "total_batches_processed": self.total_batches_processed,
            "total_events_processed": self.total_events_processed,
            "total_events_failed": self.total_events_failed,
            "success_rate": round(success_rate, 2),
            "average_batch_size": round(avg_batch_size, 2),
            "average_processing_time_ms": round(avg_processing_time * 1000, 2),
            "average_processing_rate_per_second": round(avg_processing_rate, 2),
            "overall_processing_rate_per_second": round(overall_rate, 2),
            "uptime_seconds": round(uptime, 2),
            "batch_handlers_count": len(self.batch_handlers),
            "retry_attempts": self.retry_attempts,
            "retry_delay": self.retry_delay
        }
    
    def reset_statistics(self):
        """Reset processing statistics"""
        self.total_batches_processed = 0
        self.total_events_processed = 0
        self.total_events_failed = 0
        self.processing_start_time = datetime.now()
        self.batch_processing_times.clear()
        self.batch_sizes.clear()
        self.processing_rates.clear()
        logger.info("Batch processing statistics reset")
