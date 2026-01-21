"""
Unit Tests for WebSocket Ingestion Service Main Application

Target: 80% test coverage for main.py
Following data-api test patterns and TappsCodingAgents best practices
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from dotenv import load_dotenv

# Setup path for imports
from tests.path_setup import add_service_src

add_service_src(__file__)

# Load environment variables for testing
load_dotenv()


@pytest.fixture
def mock_shared_modules():
    """Mock shared modules that may not be available in test environment"""
    with patch.dict(sys.modules, {
        'shared.correlation_middleware': MagicMock(),
        'shared.enhanced_ha_connection_manager': MagicMock(),
        'shared.logging_config': MagicMock(),
    }):
        yield


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up mock environment variables"""
    monkeypatch.setenv('HA_HTTP_URL', 'http://test:8123')
    monkeypatch.setenv('HA_WS_URL', 'ws://test:8123/api/websocket')
    monkeypatch.setenv('HA_TOKEN', 'test-token')
    monkeypatch.setenv('ENABLE_HOME_ASSISTANT', 'false')  # Disable HA for unit tests
    monkeypatch.setenv('INFLUXDB_URL', 'http://test-influxdb:8086')
    monkeypatch.setenv('INFLUXDB_TOKEN', 'test-token')
    monkeypatch.setenv('INFLUXDB_ORG', 'test-org')
    monkeypatch.setenv('INFLUXDB_BUCKET', 'test-bucket')
    monkeypatch.setenv('MAX_WORKERS', '5')
    monkeypatch.setenv('PROCESSING_RATE_LIMIT', '500')
    monkeypatch.setenv('BATCH_SIZE', '50')
    monkeypatch.setenv('BATCH_TIMEOUT', '2.5')
    monkeypatch.setenv('MAX_MEMORY_MB', '512')


class TestWebSocketIngestionService:
    """Test WebSocketIngestionService class"""

    @pytest.fixture
    def service(self, mock_env_vars, mock_shared_modules):
        """Create service instance with mocked dependencies"""
        from src.main import WebSocketIngestionService
        
        with patch('src.main.setup_logging'):
            service = WebSocketIngestionService()
            return service

    def test_init(self, service):
        """Test service initialization"""
        assert service.start_time is not None
        assert isinstance(service.start_time, datetime)
        assert service.connection_manager is None
        assert service.health_handler is not None
        assert service.async_event_processor is None
        assert service.event_queue is None
        assert service.batch_processor is None
        assert service.memory_manager is None
        assert service.influxdb_manager is None
        assert service.home_assistant_url == 'http://test:8123'
        assert service.home_assistant_ws_url == 'ws://test:8123/api/websocket'
        assert service.home_assistant_token == 'test-token'
        assert service.home_assistant_enabled is False
        assert service.max_workers == 5
        assert service.processing_rate_limit == 500
        assert service.batch_size == 50
        assert service.batch_timeout == 2.5
        assert service.max_memory_mb == 512
        assert service.influxdb_url == 'http://test-influxdb:8086'
        assert service.influxdb_token == 'test-token'
        assert service.influxdb_org == 'test-org'
        assert service.influxdb_bucket == 'test-bucket'

    def test_entity_filter_initialization_no_config(self, service):
        """Test entity filter initialization when no config provided"""
        # Entity filter should be None when no config
        assert service.entity_filter is None

    @pytest.mark.asyncio
    async def test_startup_without_home_assistant(self, service):
        """Test service startup without Home Assistant enabled"""
        # Mock all async components
        with patch.object(service, 'memory_manager', new_callable=AsyncMock) as mock_memory:
            with patch.object(service, 'event_queue', new_callable=Mock) as mock_queue:
                with patch.object(service, 'batch_processor', new_callable=AsyncMock) as mock_batch:
                    with patch.object(service, 'async_event_processor', new_callable=AsyncMock) as mock_async:
                        with patch('src.main.MemoryManager', return_value=mock_memory):
                            with patch('src.main.EventQueue', return_value=mock_queue):
                                with patch('src.main.BatchProcessor', return_value=mock_batch):
                                    with patch('src.main.AsyncEventProcessor', return_value=mock_async):
                                        with patch('src.main.InfluxDBConnectionManager') as mock_influxdb_mgr:
                                            with patch('src.influxdb_batch_writer.InfluxDBBatchWriter') as mock_batch_writer:
                                                with patch('src.main.HistoricalEventCounter') as mock_counter:
                                                    # Setup mocks
                                                    mock_influxdb_mgr.return_value.start = AsyncMock()
                                                    mock_batch_writer.return_value.start = AsyncMock()
                                                    mock_counter.return_value.initialize_historical_totals = AsyncMock(
                                                        return_value={'total_events_received': 0}
                                                    )
                                                    mock_memory.start = AsyncMock()
                                                    mock_batch.start = AsyncMock()
                                                    mock_async.start = AsyncMock()
                                                    
                                                    # Execute
                                                    await service.start()
                                                    
                                                    # Verify
                                                    assert service.memory_manager is not None
                                                    assert service.event_queue is not None
                                                    assert service.batch_processor is not None
                                                    assert service.async_event_processor is not None

    @pytest.mark.asyncio
    async def test_startup_with_influxdb_failure(self, service):
        """Test service startup when InfluxDB connection fails"""
        with patch('src.main.MemoryManager') as mock_memory:
            with patch('src.main.EventQueue'):
                with patch('src.main.BatchProcessor'):
                    with patch('src.main.AsyncEventProcessor'):
                        with patch('src.main.InfluxDBConnectionManager') as mock_influxdb_mgr:
                            with patch('src.main.HistoricalEventCounter'):
                                with patch('src.influxdb_batch_writer.InfluxDBBatchWriter'):
                                    # Setup InfluxDB to fail
                                    mock_influxdb_mgr.return_value.start = AsyncMock(side_effect=Exception("Connection failed"))
                                    
                                    # Should raise exception
                                    with pytest.raises(Exception):
                                        await service.start()

    @pytest.mark.asyncio
    async def test_startup_with_batch_writer_failure(self, service):
        """Test service startup when batch writer fails to start"""
        with patch('src.main.MemoryManager'):
            with patch('src.main.EventQueue'):
                with patch('src.main.BatchProcessor'):
                    with patch('src.main.AsyncEventProcessor'):
                        with patch('src.main.InfluxDBConnectionManager') as mock_influxdb_mgr:
                            with patch('src.main.HistoricalEventCounter'):
                                with patch('src.influxdb_batch_writer.InfluxDBBatchWriter') as mock_batch_writer:
                                    # Setup InfluxDB to succeed
                                    mock_influxdb_mgr.return_value.start = AsyncMock()
                                    # Setup batch writer to fail
                                    mock_batch_writer.return_value.start = AsyncMock(side_effect=Exception("Batch writer failed"))

                                    # Should raise exception
                                    with pytest.raises(Exception):
                                        await service.start()

    @pytest.mark.asyncio
    async def test_stop_with_partial_initialization(self, service):
        """Test service stop when only some components are initialized"""
        # Setup partial initialization
        service.async_event_processor = AsyncMock()
        service.batch_processor = None  # Not initialized
        service.memory_manager = AsyncMock()
        service.influxdb_batch_writer = None  # Not initialized
        service.influxdb_manager = AsyncMock()
        service.connection_manager = None  # Not initialized
        
        # Should not raise exception
        await service.stop()
        
        # Verify initialized components were stopped
        service.async_event_processor.stop.assert_called_once()
        service.memory_manager.stop.assert_called_once()
        service.influxdb_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_exception(self, service):
        """Test service stop when component raises exception"""
        service.async_event_processor = AsyncMock()
        service.async_event_processor.stop = AsyncMock(side_effect=Exception("Stop failed"))
        service.batch_processor = AsyncMock()
        service.memory_manager = AsyncMock()
        
        # Should not raise exception (errors are logged but don't stop cleanup)
        await service.stop()
        
        # Verify all stop methods were called
        service.async_event_processor.stop.assert_called_once()
        service.batch_processor.stop.assert_called_once()
        service.memory_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop(self, service):
        """Test service stop"""
        # Setup mocks
        service.async_event_processor = AsyncMock()
        service.batch_processor = AsyncMock()
        service.memory_manager = AsyncMock()
        service.influxdb_batch_writer = AsyncMock()
        service.influxdb_manager = AsyncMock()
        service.connection_manager = AsyncMock()
        
        # Execute
        await service.stop()
        
        # Verify cleanup called
        service.async_event_processor.stop.assert_called_once()
        service.batch_processor.stop.assert_called_once()
        service.memory_manager.stop.assert_called_once()
        service.influxdb_batch_writer.stop.assert_called_once()
        service.influxdb_manager.stop.assert_called_once()
        service.connection_manager.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_status_no_manager(self, service):
        """Test connection status check when manager is None"""
        service.connection_manager = None
        result = await service._check_connection_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_status_no_client(self, service):
        """Test connection status check when client is None"""
        service.connection_manager = Mock()
        service.connection_manager.client = None
        result = await service._check_connection_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_check_connection_status_connected(self, service):
        """Test connection status check when connected"""
        mock_websocket = Mock()
        mock_websocket.closed = False
        mock_client = Mock()
        mock_client.websocket = mock_websocket
        service.connection_manager = Mock()
        service.connection_manager.client = mock_client
        
        result = await service._check_connection_status()
        assert result is True

    @pytest.mark.asyncio
    async def test_check_connection_status_disconnected(self, service):
        """Test connection status check when disconnected"""
        mock_websocket = Mock()
        mock_websocket.closed = True
        mock_client = Mock()
        mock_client.websocket = mock_websocket
        service.connection_manager = Mock()
        service.connection_manager.client = mock_client
        
        result = await service._check_connection_status()
        assert result is False

    @pytest.mark.asyncio
    async def test_on_connect(self, service):
        """Test on_connect handler"""
        mock_manager = AsyncMock()
        mock_manager._subscribe_to_events = AsyncMock()
        mock_manager.discovery_service = Mock()
        mock_manager.discovery_service.discover_all = AsyncMock()
        mock_manager.client = Mock()
        mock_manager.client.websocket = Mock()
        mock_manager.client.is_connected = True
        mock_manager.client.is_authenticated = True
        
        service.connection_manager = mock_manager
        
        await service._on_connect()
        
        # Verify subscription was called
        mock_manager._subscribe_to_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_connect_with_subscription_error(self, service):
        """Test on_connect handler when subscription fails"""
        mock_manager = AsyncMock()
        mock_manager._subscribe_to_events = AsyncMock(side_effect=Exception("Subscription failed"))
        mock_manager.discovery_service = Mock()
        mock_manager.discovery_service.discover_all = AsyncMock()
        mock_manager.client = Mock()
        mock_manager.client.websocket = Mock()
        mock_manager.client.is_connected = True
        mock_manager.client.is_authenticated = True
        
        service.connection_manager = mock_manager
        
        # Should not raise exception (errors are logged)
        await service._on_connect()
        
        # Verify subscription was attempted
        mock_manager._subscribe_to_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_connect_with_discovery_error(self, service):
        """Test on_connect handler when discovery fails"""
        mock_manager = AsyncMock()
        mock_manager._subscribe_to_events = AsyncMock()
        mock_manager.discovery_service = Mock()
        mock_manager.discovery_service.discover_all = AsyncMock(side_effect=Exception("Discovery failed"))
        mock_manager.client = Mock()
        mock_manager.client.websocket = Mock()
        mock_manager.client.is_connected = True
        mock_manager.client.is_authenticated = True
        
        service.connection_manager = mock_manager
        
        # Should not raise exception (errors are logged)
        await service._on_connect()
        
        # Verify both subscription and discovery were attempted
        mock_manager._subscribe_to_events.assert_called_once()
        mock_manager.discovery_service.discover_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_connect_without_websocket(self, service):
        """Test on_connect handler when websocket is not ready"""
        mock_manager = AsyncMock()
        mock_manager._subscribe_to_events = AsyncMock()
        mock_manager.discovery_service = Mock()
        mock_manager.discovery_service.discover_all = AsyncMock()
        mock_manager.client = Mock()
        mock_manager.client.websocket = None  # No websocket
        mock_manager.client.is_connected = False
        mock_manager.client.is_authenticated = False
        
        service.connection_manager = mock_manager
        
        # Should not raise exception
        await service._on_connect()
        
        # Verify subscription was attempted
        mock_manager._subscribe_to_events.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_connect_no_connection_manager(self, service):
        """Test on_connect handler when connection manager is None"""
        service.connection_manager = None
        
        # Should not raise exception
        await service._on_connect()

    @pytest.mark.asyncio
    async def test_on_disconnect(self, service):
        """Test on_disconnect handler"""
        # Should not raise exception
        await service._on_disconnect()

    @pytest.mark.asyncio
    async def test_on_message(self, service):
        """Test on_message handler"""
        test_message = {"type": "test", "data": "test"}
        # Should not raise exception
        await service._on_message(test_message)

    @pytest.mark.asyncio
    async def test_on_event_with_entity_filter_exclude(self, service):
        """Test on_event handler with entity filter excluding event"""
        # Setup entity filter
        mock_filter = Mock()
        mock_filter.should_include = Mock(return_value=False)
        service.entity_filter = mock_filter
        service.batch_processor = AsyncMock()
        
        event = {
            'event_type': 'state_changed',
            'entity_id': 'test.entity',
            'domain': 'test'
        }
        
        await service._on_event(event)
        
        # Verify filter was checked and event was not added to batch
        mock_filter.should_include.assert_called_once_with(event)
        service.batch_processor.add_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_event_with_entity_filter_include(self, service):
        """Test on_event handler with entity filter including event"""
        # Setup entity filter
        mock_filter = Mock()
        mock_filter.should_include = Mock(return_value=True)
        service.entity_filter = mock_filter
        service.batch_processor = AsyncMock()
        
        event = {
            'event_type': 'state_changed',
            'entity_id': 'test.entity',
            'domain': 'test'
        }
        
        await service._on_event(event)
        
        # Verify filter was checked and event was added to batch
        mock_filter.should_include.assert_called_once_with(event)
        service.batch_processor.add_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_on_event_no_filter(self, service):
        """Test on_event handler without entity filter"""
        service.entity_filter = None
        service.batch_processor = AsyncMock()
        
        event = {
            'event_type': 'state_changed',
            'entity_id': 'test.entity',
            'domain': 'test'
        }
        
        await service._on_event(event)
        
        # Verify event was added to batch
        service.batch_processor.add_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_on_event_with_batch_processor_error(self, service):
        """Test on_event handler when batch processor raises error"""
        service.entity_filter = None
        service.batch_processor = AsyncMock()
        service.batch_processor.add_event = AsyncMock(side_effect=Exception("Batch processor error"))
        
        event = {
            'event_type': 'state_changed',
            'entity_id': 'test.entity',
            'domain': 'test'
        }
        
        # Should not raise exception (errors are logged)
        await service._on_event(event)
        
        # Verify add_event was attempted
        service.batch_processor.add_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_on_event_no_batch_processor(self, service):
        """Test on_event handler when batch processor is None"""
        service.entity_filter = None
        service.batch_processor = None
        
        event = {
            'event_type': 'state_changed',
            'entity_id': 'test.entity',
            'domain': 'test'
        }
        
        # Should not raise exception
        await service._on_event(event)

    @pytest.mark.asyncio
    async def test_on_event_missing_fields(self, service):
        """Test on_event handler with event missing fields"""
        service.entity_filter = None
        service.batch_processor = AsyncMock()
        
        # Event with minimal fields
        event = {
            'event_type': 'state_changed'
        }
        
        await service._on_event(event)
        
        # Verify event was still added to batch
        service.batch_processor.add_event.assert_called_once_with(event)

    @pytest.mark.asyncio
    async def test_write_event_to_influxdb_success(self, service):
        """Test writing event to InfluxDB successfully"""
        mock_writer = AsyncMock()
        mock_writer.write_event = AsyncMock(return_value=True)
        service.influxdb_batch_writer = mock_writer
        
        event_data = {'event_type': 'test', 'data': 'test'}
        await service._write_event_to_influxdb(event_data)
        
        mock_writer.write_event.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_write_event_to_influxdb_failure(self, service):
        """Test writing event to InfluxDB with failure"""
        mock_writer = AsyncMock()
        mock_writer.write_event = AsyncMock(return_value=False)
        service.influxdb_batch_writer = mock_writer
        
        event_data = {'event_type': 'test', 'data': 'test'}
        await service._write_event_to_influxdb(event_data)
        
        mock_writer.write_event.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_write_event_to_influxdb_no_writer(self, service):
        """Test writing event when batch writer is None"""
        service.influxdb_batch_writer = None
        
        event_data = {'event_type': 'test', 'data': 'test'}
        # Should not raise exception
        await service._write_event_to_influxdb(event_data)

    @pytest.mark.asyncio
    async def test_write_event_to_influxdb_exception(self, service):
        """Test writing event when batch writer raises exception"""
        mock_writer = AsyncMock()
        mock_writer.write_event = AsyncMock(side_effect=Exception("Write failed"))
        service.influxdb_batch_writer = mock_writer
        
        event_data = {'event_type': 'test', 'data': 'test'}
        # Should not raise exception (errors are logged)
        await service._write_event_to_influxdb(event_data)
        
        # Verify write was attempted
        mock_writer.write_event.assert_called_once_with(event_data)

    @pytest.mark.asyncio
    async def test_process_batch(self, service):
        """Test batch processing"""
        mock_processor = AsyncMock()
        mock_processor.process_event = AsyncMock()
        service.async_event_processor = mock_processor
        
        batch = [
            {'event_type': 'test1', 'data': 'test1'},
            {'event_type': 'test2', 'data': 'test2'}
        ]
        
        await service._process_batch(batch)
        
        # Verify all events were processed
        assert mock_processor.process_event.call_count == 2

    @pytest.mark.asyncio
    async def test_process_batch_empty(self, service):
        """Test batch processing with empty batch"""
        mock_processor = AsyncMock()
        service.async_event_processor = mock_processor
        
        await service._process_batch([])
        
        # Should not call process_event
        mock_processor.process_event.assert_not_called()

    @pytest.mark.asyncio
    async def test_process_batch_with_processor_error(self, service):
        """Test batch processing when processor raises error"""
        mock_processor = AsyncMock()
        mock_processor.process_event = AsyncMock(side_effect=Exception("Processing failed"))
        service.async_event_processor = mock_processor
        
        batch = [
            {'event_type': 'test1', 'data': 'test1'},
            {'event_type': 'test2', 'data': 'test2'}
        ]
        
        # Should not raise exception (errors are logged)
        await service._process_batch(batch)
        
        # Verify processing was attempted for all events
        assert mock_processor.process_event.call_count == 2

    @pytest.mark.asyncio
    async def test_process_batch_no_processor(self, service):
        """Test batch processing when processor is None"""
        service.async_event_processor = None
        
        batch = [
            {'event_type': 'test1', 'data': 'test1'}
        ]
        
        # Should not raise exception
        await service._process_batch(batch)

    @pytest.mark.asyncio
    async def test_on_error(self, service):
        """Test error handler"""
        test_error = ValueError("Test error")
        # Should not raise exception
        await service._on_error(test_error)

    @pytest.mark.asyncio
    async def test_on_error_with_none(self, service):
        """Test error handler with None error"""
        # Should not raise exception
        await service._on_error(None)

    @pytest.mark.asyncio
    async def test_on_error_with_string(self, service):
        """Test error handler with string error"""
        # Should not raise exception
        await service._on_error("String error message")

    @pytest.mark.asyncio
    async def test_on_event_entity_deletion(self, service):
        """Test on_event handler with entity deletion (new_state is None)"""
        """CRITICAL: This test prevents AttributeError crashes when entities are deleted"""
        service.entity_filter = None
        service.batch_processor = AsyncMock()
        
        # Simulate entity deletion event (new_state is None)
        event = {
            'event_type': 'state_changed',
            'entity_id': 'test.entity',
            'old_state': {
                'entity_id': 'test.entity',
                'state': 'on',
                'last_changed': '2025-01-01T00:00:00Z'
            },
            'new_state': None  # Entity deleted
        }
        
        # Should not raise AttributeError
        await service._on_event(event)
        
        # Verify event was still added to batch (deletion events should be processed)
        service.batch_processor.add_event.assert_called_once()


class TestMainFunction:
    """Test main() function"""

    @pytest.mark.asyncio
    async def test_main_function(self, monkeypatch):
        """Test main() function calls uvicorn.run"""
        mock_uvicorn = Mock()
        mock_uvicorn.run = Mock()
        monkeypatch.setenv('WEBSOCKET_INGESTION_PORT', '8001')
        monkeypatch.setenv('WEBSOCKET_INGESTION_HOST', '127.0.0.1')
        
        with patch.dict('sys.modules', {'uvicorn': mock_uvicorn}):
            with patch('src.main.app'):
                from src.main import main
                # Note: main() will block, so we can't easily test it in unit tests
                # This is more of an integration test scenario
                pass  # Placeholder for main() testing


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.main", "--cov-report=term-missing"])

