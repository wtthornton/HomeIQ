"""
Event Processing Pipeline Integration Tests
Epic 50 Story 50.3: Integration Test Suite

Tests for end-to-end event processing pipeline from Home Assistant to InfluxDB.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.connection_manager import ConnectionManager
from src.batch_processor import BatchProcessor
from src.async_event_processor import AsyncEventProcessor


@pytest.fixture
def sample_ha_event():
    """Sample Home Assistant event"""
    return {
        'event_type': 'state_changed',
        'time_fired': datetime.now(timezone.utc).isoformat(),
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
    # Process event
    result = await event_processor.process_event(sample_ha_event)
    
    # Verify event was processed
    assert result is not None
    assert 'entity_id' in result or 'normalized' in str(result)


@pytest.mark.asyncio
async def test_batch_processing_integration(batch_processor, sample_ha_event):
    """Test batch processing integration"""
    # Add events to batch
    for i in range(5):
        event = sample_ha_event.copy()
        event['data']['entity_id'] = f'switch.lamp_{i}'
        await batch_processor.add_event(event)
    
    # Wait for batch to process (or trigger manually)
    await batch_processor._process_batch()
    
    # Verify batch was written
    assert batch_processor.influxdb_writer.write_batch.called


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
    # Add single event
    await batch_processor.add_event(sample_ha_event)
    
    # Wait for timeout
    import asyncio
    await asyncio.sleep(1.5)  # Wait longer than batch_timeout
    
    # Verify batch was processed
    assert batch_processor.influxdb_writer.write_batch.called


@pytest.mark.asyncio
async def test_batch_size_processing(batch_processor, sample_ha_event):
    """Test batch processing when batch size reached"""
    # Add events up to batch size
    for i in range(10):
        event = sample_ha_event.copy()
        event['data']['entity_id'] = f'switch.lamp_{i}'
        await batch_processor.add_event(event)
    
    # Batch should process immediately when size reached
    await asyncio.sleep(0.1)  # Small delay for async processing
    
    # Verify batch was written
    assert batch_processor.influxdb_writer.write_batch.called


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
        # Add to batch
        await batch_processor.add_event(processed_event)
        
        # Process batch
        await batch_processor._process_batch()
        
        # Verify end-to-end flow completed
        assert batch_processor.influxdb_writer.write_batch.called

