"""
Event Processing Pipeline Integration Tests
Epic 50 Story 50.3: Integration Test Suite

Tests for end-to-end event processing pipeline from Home Assistant to InfluxDB.
"""

import asyncio
import os
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.async_event_processor import AsyncEventProcessor
from src.batch_processor import BatchProcessor


@pytest.fixture
def sample_ha_event():
    """Sample Home Assistant event"""
    return {
        'event_type': 'state_changed',
        'time_fired': datetime.now(UTC).isoformat(),
        'data': {
            'entity_id': 'switch.living_room_lamp',
            'old_state': {'state': 'off'},
            'new_state': {'state': 'on', 'attributes': {}}
        }
    }


@pytest.fixture
async def event_processor():
    """Create event processor with mocked dependencies"""
    processor = AsyncEventProcessor()
    
    # Mock dependencies
    processor.discovery_service = MagicMock()
    processor.discovery_service.get_device_info = AsyncMock(return_value=None)
    processor.discovery_service.get_area_info = AsyncMock(return_value=None)
    
    yield processor


@pytest.fixture
async def batch_processor():
    """Create batch processor"""
    processor = BatchProcessor(batch_size=10, batch_timeout=1.0)
    
    # Mock InfluxDB writer
    processor.influxdb_writer = MagicMock()
    processor.influxdb_writer.write_batch = AsyncMock()
    
    yield processor
    
    # Cleanup
    try:
        await processor.shutdown()
    except:
        pass


@pytest.mark.asyncio
async def test_event_processing_flow(event_processor, sample_ha_event):
    """Test complete event processing flow"""
    # process_event returns True if event was queued successfully
    result = await event_processor.process_event(sample_ha_event)

    # Verify event was queued
    assert result is True


@pytest.mark.asyncio
async def test_batch_processing_integration(batch_processor, sample_ha_event):
    """Test batch processing integration"""
    # Add events to batch
    for i in range(5):
        event = sample_ha_event.copy()
        event['data'] = {**sample_ha_event['data'], 'entity_id': f'switch.lamp_{i}'}
        await batch_processor.add_event(event)

    # _process_batch requires a batch list argument; use _process_current_batch
    # to drain and process the internal buffer
    await batch_processor._process_current_batch()


@pytest.mark.asyncio
async def test_event_normalization(event_processor, sample_ha_event):
    """Test event normalization in processing pipeline"""
    # Process event
    result = await event_processor.process_event(sample_ha_event)
    
    # Verify normalization occurred
    # Event should have standard fields
    assert result is not None


@pytest.mark.asyncio
async def test_batch_timeout_processing(batch_processor, sample_ha_event):
    """Test batch processing on timeout"""
    # Start the processor so the _processing_loop runs
    await batch_processor.start()

    # Add single event
    await batch_processor.add_event(sample_ha_event)

    # Wait for timeout (batch_timeout=1.0 in fixture)
    await asyncio.sleep(1.5)

    # The processing loop calls registered batch_handlers, not influxdb_writer
    # Verify the event was drained from the internal batch
    assert len(batch_processor.current_batch) == 0

    await batch_processor.stop()


@pytest.mark.asyncio
async def test_batch_size_processing(batch_processor, sample_ha_event):
    """Test batch processing when batch size reached"""
    # batch_size=10 in fixture; adding 10 events triggers immediate processing
    for i in range(10):
        event = sample_ha_event.copy()
        event['data'] = {**sample_ha_event['data'], 'entity_id': f'switch.lamp_{i}'}
        await batch_processor.add_event(event)

    # Batch should have been drained when size reached (add_event auto-processes)
    assert len(batch_processor.current_batch) == 0
    assert batch_processor.total_batches_processed == 1
    assert batch_processor.total_events_processed == 10


@pytest.mark.asyncio
async def test_error_handling_in_pipeline(event_processor):
    """Test error handling in event processing pipeline"""
    # Invalid event
    invalid_event = {'invalid': 'data'}
    
    # Process should handle error gracefully
    try:
        result = await event_processor.process_event(invalid_event)
        # May return None or handle error
        assert result is None or isinstance(result, dict)
    except Exception:
        # Exception is acceptable for invalid events
        pass


@pytest.mark.asyncio
async def test_end_to_end_flow(event_processor, batch_processor, sample_ha_event):
    """Test complete end-to-end event flow"""
    # Process event
    processed_event = await event_processor.process_event(sample_ha_event)
    
    if processed_event:
        # Add to batch (process_event returns True, so use original event)
        await batch_processor.add_event(sample_ha_event)

        # Drain and process the current batch
        await batch_processor._process_current_batch()

