"""
Tests for Async Event Processor
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from src.async_event_processor import AsyncEventProcessor, RateLimiter


class TestAsyncEventProcessor:
    """Test cases for AsyncEventProcessor class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.processor = AsyncEventProcessor(max_workers=2, processing_rate_limit=100)
    
    def teardown_method(self):
        """Clean up after tests"""
        if self.processor.is_running:
            asyncio.run(self.processor.stop())
    
    def test_initialization(self):
        """Test processor initialization"""
        assert self.processor.max_workers == 2
        assert self.processor.processing_rate_limit == 100
        assert self.processor.processed_events == 0
        assert self.processor.failed_events == 0
        assert not self.processor.is_running
        assert len(self.processor.workers) == 0
        assert len(self.processor.event_handlers) == 0
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the processor"""
        # Start processor
        await self.processor.start()
        assert self.processor.is_running
        assert len(self.processor.workers) == 2
        
        # Stop processor
        await self.processor.stop()
        assert not self.processor.is_running
        assert len(self.processor.workers) == 0
    
    @pytest.mark.asyncio
    async def test_process_event_success(self):
        """Test successful event processing"""
        await self.processor.start()
        
        # Add a mock event handler
        mock_handler = AsyncMock()
        self.processor.add_event_handler(mock_handler)
        
        # Process an event
        event_data = {"event_type": "state_changed", "entity_id": "sensor.test"}
        success = await self.processor.process_event(event_data)
        
        assert success
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Check that handler was called
        mock_handler.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_event_rate_limit(self):
        """Test event processing with rate limiting"""
        # Set very low rate limit
        self.processor.configure_processing_rate(1)
        await self.processor.start()
        
        # Process events rapidly
        events_processed = 0
        for i in range(5):
            event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
            if await self.processor.process_event(event_data):
                events_processed += 1
        
        # Should only process 1 event due to rate limiting
        assert events_processed <= 1
    
    @pytest.mark.asyncio
    async def test_event_handler_management(self):
        """Test adding and removing event handlers"""
        mock_handler1 = AsyncMock()
        mock_handler2 = AsyncMock()
        
        # Add handlers
        self.processor.add_event_handler(mock_handler1)
        self.processor.add_event_handler(mock_handler2)
        
        assert len(self.processor.event_handlers) == 2
        
        # Remove handler
        self.processor.remove_event_handler(mock_handler1)
        assert len(self.processor.event_handlers) == 1
        assert mock_handler2 in self.processor.event_handlers
    
    @pytest.mark.asyncio
    async def test_processing_statistics(self):
        """Test processing statistics"""
        await self.processor.start()
        
        # Add a mock handler
        mock_handler = AsyncMock()
        self.processor.add_event_handler(mock_handler)
        
        # Process some events
        for i in range(5):
            event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
            await self.processor.process_event(event_data)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Get statistics
        stats = self.processor.get_processing_statistics()
        
        assert stats["is_running"] is True
        assert stats["max_workers"] == 2
        assert stats["active_workers"] == 2
        assert stats["processing_rate_limit"] == 100
        assert stats["processed_events"] >= 0
        assert stats["success_rate"] >= 0
        assert stats["queue_size"] >= 0
        assert stats["event_handlers_count"] == 1
    
    @pytest.mark.asyncio
    async def test_configure_processing_rate(self):
        """Test configuring processing rate"""
        await self.processor.start()
        
        # Configure new rate
        self.processor.configure_processing_rate(500)
        
        assert self.processor.processing_rate_limit == 500
        assert self.processor.rate_limiter.rate_limit == 500
    
    def test_configure_max_workers_while_running(self):
        """Test configuring max workers while running"""
        # This should not be allowed
        asyncio.run(self.processor.start())
        
        # Try to configure max workers
        self.processor.configure_max_workers(5)
        
        # Should not change while running
        assert self.processor.max_workers == 2
    
    @pytest.mark.asyncio
    async def test_reset_statistics(self):
        """Test resetting statistics"""
        await self.processor.start()
        
        # Process some events
        for i in range(3):
            event_data = {"event_type": "state_changed", "entity_id": f"sensor.test{i}"}
            await self.processor.process_event(event_data)
        
        # Wait for processing
        await asyncio.sleep(0.1)
        
        # Reset statistics
        self.processor.reset_statistics()
        
        assert self.processor.processed_events == 0
        assert self.processor.failed_events == 0
        assert len(self.processor.processing_times) == 0


class TestRateLimiter:
    """Test cases for RateLimiter class"""
    
    def test_initialization(self):
        """Test rate limiter initialization"""
        limiter = RateLimiter(100)
        assert limiter.rate_limit == 100
        assert limiter.tokens == 100
    
    @pytest.mark.asyncio
    async def test_acquire_token(self):
        """Test acquiring tokens"""
        limiter = RateLimiter(2)  # 2 tokens per second
        
        # Should be able to acquire tokens initially
        assert await limiter.acquire() is True
        assert await limiter.acquire() is True
        
        # Should not be able to acquire more tokens immediately
        assert await limiter.acquire() is False
    
    @pytest.mark.asyncio
    async def test_token_refill(self):
        """Test token refill over time"""
        limiter = RateLimiter(1)  # 1 token per second
        
        # Acquire initial token
        assert await limiter.acquire() is True
        
        # Wait for token refill
        await asyncio.sleep(1.1)
        
        # Should be able to acquire token again
        assert await limiter.acquire() is True
    
    @pytest.mark.asyncio
    async def test_high_rate_limit(self):
        """Test high rate limit"""
        limiter = RateLimiter(1000)  # 1000 tokens per second
        
        # Should be able to acquire many tokens
        acquired_count = 0
        for _ in range(100):
            if await limiter.acquire():
                acquired_count += 1
        
        # Should acquire most tokens
        assert acquired_count >= 90
