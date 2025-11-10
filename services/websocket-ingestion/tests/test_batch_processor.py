"""
Unit tests for BatchProcessor - Critical performance component
"""

import pytest
import asyncio
from datetime import datetime
from batch_processor import BatchProcessor


class TestBatchProcessorInitialization:
    """Test batch processor initialization"""

    def test_init_default_values(self):
        """Test initialization with default values"""
        processor = BatchProcessor()

        assert processor.batch_size == 100
        assert processor.batch_timeout == 5.0
        assert processor.current_batch == []
        assert processor.batch_start_time is None
        assert processor.total_batches_processed == 0
        assert processor.total_events_processed == 0
        assert processor.total_events_failed == 0
        assert processor.is_running is False
        assert processor.retry_attempts == 3
        assert processor.retry_delay == 1.0
        assert len(processor.batch_handlers) == 0

    def test_init_custom_values(self):
        """Test initialization with custom values"""
        processor = BatchProcessor(batch_size=50, batch_timeout=2.0)

        assert processor.batch_size == 50
        assert processor.batch_timeout == 2.0


class TestBatchProcessorLifecycle:
    """Test batch processor lifecycle management"""

    @pytest.mark.asyncio
    async def test_start(self):
        """Test starting the batch processor"""
        processor = BatchProcessor()

        await processor.start()

        assert processor.is_running is True
        assert processor.processing_task is not None

        await processor.stop()

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting when already running"""
        processor = BatchProcessor()

        await processor.start()
        await processor.start()  # Should log warning but not fail

        assert processor.is_running is True

        await processor.stop()

    @pytest.mark.asyncio
    async def test_stop(self):
        """Test stopping the batch processor"""
        processor = BatchProcessor()

        await processor.start()
        await processor.stop()

        assert processor.is_running is False

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self):
        """Test stopping when not running"""
        processor = BatchProcessor()

        await processor.stop()  # Should not fail

        assert processor.is_running is False


class TestBatchProcessorEventHandling:
    """Test batch processor event handling"""

    @pytest.mark.asyncio
    async def test_add_single_event(self):
        """Test adding a single event"""
        processor = BatchProcessor(batch_size=10)

        event = {"entity_id": "light.living_room", "state": "on"}
        result = await processor.add_event(event)

        assert result is True
        assert len(processor.current_batch) == 1
        assert processor.current_batch[0] == event
        assert processor.batch_start_time is not None

    @pytest.mark.asyncio
    async def test_add_event_triggers_batch_when_full(self):
        """Test that batch is processed when it reaches batch_size"""
        processor = BatchProcessor(batch_size=3)
        processed_batches = []

        async def mock_handler(batch):
            processed_batches.append(batch.copy())

        processor.add_batch_handler(mock_handler)

        # Add events to fill the batch
        for i in range(3):
            await processor.add_event({"id": i})

        # Batch should be processed immediately
        assert len(processor.current_batch) == 0
        assert len(processed_batches) == 1
        assert len(processed_batches[0]) == 3
        assert processor.total_events_processed == 3

    @pytest.mark.asyncio
    async def test_batch_timeout_processing(self):
        """Test that batch is processed after timeout"""
        processor = BatchProcessor(batch_size=10, batch_timeout=0.5)
        processed_batches = []

        async def mock_handler(batch):
            processed_batches.append(batch.copy())

        processor.add_batch_handler(mock_handler)
        await processor.start()

        # Add events but not enough to fill batch
        await processor.add_event({"id": 1})
        await processor.add_event({"id": 2})

        # Wait for timeout
        await asyncio.sleep(0.7)

        await processor.stop()

        # Batch should be processed due to timeout
        assert len(processed_batches) >= 1
        assert processor.total_events_processed == 2


class TestBatchProcessorHandlers:
    """Test batch handler management"""

    @pytest.mark.asyncio
    async def test_add_batch_handler(self):
        """Test adding a batch handler"""
        processor = BatchProcessor()

        async def mock_handler(batch):
            pass

        processor.add_batch_handler(mock_handler)

        assert len(processor.batch_handlers) == 1
        assert processor.batch_handlers[0] == mock_handler

    @pytest.mark.asyncio
    async def test_remove_batch_handler(self):
        """Test removing a batch handler"""
        processor = BatchProcessor()

        async def mock_handler(batch):
            pass

        processor.add_batch_handler(mock_handler)
        processor.remove_batch_handler(mock_handler)

        assert len(processor.batch_handlers) == 0

    @pytest.mark.asyncio
    async def test_multiple_handlers(self):
        """Test that multiple handlers are called"""
        processor = BatchProcessor(batch_size=2)
        handler1_calls = []
        handler2_calls = []

        async def handler1(batch):
            handler1_calls.append(len(batch))

        async def handler2(batch):
            handler2_calls.append(len(batch))

        processor.add_batch_handler(handler1)
        processor.add_batch_handler(handler2)

        await processor.add_event({"id": 1})
        await processor.add_event({"id": 2})

        assert len(handler1_calls) == 1
        assert len(handler2_calls) == 1
        assert handler1_calls[0] == 2
        assert handler2_calls[0] == 2


class TestBatchProcessorErrorHandling:
    """Test batch processor error handling"""

    @pytest.mark.asyncio
    async def test_handler_error_with_retry(self):
        """Test that handler errors trigger retries"""
        processor = BatchProcessor(batch_size=2)
        processor.configure_retry_settings(attempts=2, delay=0.1)

        attempt_count = []

        async def failing_handler(batch):
            attempt_count.append(1)
            raise Exception("Handler error")

        processor.add_batch_handler(failing_handler)

        await processor.add_event({"id": 1})
        await processor.add_event({"id": 2})

        # Should retry
        assert len(attempt_count) == 2
        assert processor.total_events_failed == 2
        assert processor.total_events_processed == 0

    @pytest.mark.asyncio
    async def test_handler_success_after_retry(self):
        """Test successful processing after initial failure"""
        processor = BatchProcessor(batch_size=2)
        processor.configure_retry_settings(attempts=3, delay=0.05)

        attempt_count = []

        async def flaky_handler(batch):
            attempt_count.append(1)
            if len(attempt_count) < 2:
                raise Exception("Temporary error")
            # Success on second attempt

        processor.add_batch_handler(flaky_handler)

        await processor.add_event({"id": 1})
        await processor.add_event({"id": 2})

        assert len(attempt_count) == 2
        assert processor.total_events_processed == 2
        assert processor.total_events_failed == 0


class TestBatchProcessorConfiguration:
    """Test batch processor configuration"""

    def test_configure_batch_size(self):
        """Test configuring batch size"""
        processor = BatchProcessor()

        processor.configure_batch_size(50)

        assert processor.batch_size == 50

    def test_configure_batch_size_invalid(self):
        """Test configuring batch size with invalid value"""
        processor = BatchProcessor()

        with pytest.raises(ValueError):
            processor.configure_batch_size(0)

        with pytest.raises(ValueError):
            processor.configure_batch_size(-10)

    def test_configure_batch_timeout(self):
        """Test configuring batch timeout"""
        processor = BatchProcessor()

        processor.configure_batch_timeout(10.0)

        assert processor.batch_timeout == 10.0

    def test_configure_batch_timeout_invalid(self):
        """Test configuring batch timeout with invalid value"""
        processor = BatchProcessor()

        with pytest.raises(ValueError):
            processor.configure_batch_timeout(0)

        with pytest.raises(ValueError):
            processor.configure_batch_timeout(-5.0)

    def test_configure_retry_settings(self):
        """Test configuring retry settings"""
        processor = BatchProcessor()

        processor.configure_retry_settings(attempts=5, delay=2.0)

        assert processor.retry_attempts == 5
        assert processor.retry_delay == 2.0

    def test_configure_retry_settings_invalid(self):
        """Test configuring retry settings with invalid values"""
        processor = BatchProcessor()

        with pytest.raises(ValueError):
            processor.configure_retry_settings(attempts=-1, delay=1.0)

        with pytest.raises(ValueError):
            processor.configure_retry_settings(attempts=3, delay=-1.0)


class TestBatchProcessorStatistics:
    """Test batch processor statistics"""

    @pytest.mark.asyncio
    async def test_get_processing_statistics(self):
        """Test getting processing statistics"""
        processor = BatchProcessor(batch_size=2)

        async def mock_handler(batch):
            pass

        processor.add_batch_handler(mock_handler)

        # Process some events
        await processor.add_event({"id": 1})
        await processor.add_event({"id": 2})

        stats = processor.get_processing_statistics()

        assert "is_running" in stats
        assert "batch_size" in stats
        assert "batch_timeout" in stats
        assert "current_batch_size" in stats
        assert "total_batches_processed" in stats
        assert "total_events_processed" in stats
        assert "total_events_failed" in stats
        assert "success_rate" in stats
        assert "average_batch_size" in stats
        assert "average_processing_time_ms" in stats
        assert "uptime_seconds" in stats

        assert stats["batch_size"] == 2
        assert stats["total_batches_processed"] == 1
        assert stats["total_events_processed"] == 2
        assert stats["success_rate"] == 100.0

    @pytest.mark.asyncio
    async def test_reset_statistics(self):
        """Test resetting statistics"""
        processor = BatchProcessor(batch_size=2)

        async def mock_handler(batch):
            pass

        processor.add_batch_handler(mock_handler)

        # Process some events
        await processor.add_event({"id": 1})
        await processor.add_event({"id": 2})

        assert processor.total_batches_processed == 1
        assert processor.total_events_processed == 2

        # Reset statistics
        processor.reset_statistics()

        assert processor.total_batches_processed == 0
        assert processor.total_events_processed == 0
        assert processor.total_events_failed == 0
        assert len(processor.batch_processing_times) == 0
        assert len(processor.batch_sizes) == 0
        assert len(processor.processing_rates) == 0

    @pytest.mark.asyncio
    async def test_success_rate_calculation(self):
        """Test success rate calculation"""
        processor = BatchProcessor(batch_size=2)

        call_count = []

        async def flaky_handler(batch):
            call_count.append(1)
            if len(call_count) == 1:
                # First batch succeeds
                pass
            else:
                # Second batch fails all retries
                raise Exception("Error")

        processor.add_batch_handler(flaky_handler)
        processor.configure_retry_settings(attempts=1, delay=0.01)

        # First batch - success
        await processor.add_event({"id": 1})
        await processor.add_event({"id": 2})

        # Second batch - failure
        await processor.add_event({"id": 3})
        await processor.add_event({"id": 4})

        stats = processor.get_processing_statistics()

        assert stats["total_events_processed"] == 2
        assert stats["total_events_failed"] == 2
        assert stats["success_rate"] == 50.0


class TestBatchProcessorPerformance:
    """Test batch processor performance characteristics"""

    @pytest.mark.asyncio
    async def test_high_volume_processing(self):
        """Test processing high volume of events"""
        processor = BatchProcessor(batch_size=100, batch_timeout=1.0)
        processed_count = []

        async def mock_handler(batch):
            processed_count.append(len(batch))

        processor.add_batch_handler(mock_handler)
        await processor.start()

        # Add 250 events
        for i in range(250):
            await processor.add_event({"id": i})

        await processor.stop()

        # Should have processed 3 batches (100, 100, 50)
        assert processor.total_batches_processed >= 2
        assert processor.total_events_processed == 250

    @pytest.mark.asyncio
    async def test_processing_rate_tracking(self):
        """Test that processing rates are tracked"""
        processor = BatchProcessor(batch_size=5)

        async def mock_handler(batch):
            await asyncio.sleep(0.01)  # Simulate some processing time

        processor.add_batch_handler(mock_handler)

        # Process a batch
        for i in range(5):
            await processor.add_event({"id": i})

        stats = processor.get_processing_statistics()

        assert len(processor.batch_processing_times) == 1
        assert len(processor.batch_sizes) == 1
        assert len(processor.processing_rates) == 1
        assert stats["average_processing_rate_per_second"] > 0
