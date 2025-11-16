"""
Comprehensive Tests for InfluxDB Query Client
Modern 2025 Patterns: Async testing, mock query results

Module: shared/influxdb_query_client.py
Coverage Target: >85%
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

# Import module under test
from influxdb_query_client import InfluxDBQueryClient


# ============================================================================
# Initialization Tests
# ============================================================================

class TestInfluxDBQueryClientInit:
    """Test InfluxDB Query Client initialization"""

    @patch.dict('os.environ', {
        'INFLUXDB_URL': 'http://localhost:8086',
        'INFLUXDB_TOKEN': 'test-token',
        'INFLUXDB_ORG': 'test-org',
        'INFLUXDB_BUCKET': 'test-bucket'
    })
    def test_initialization_from_env(self):
        """Test initialization from environment variables"""
        client = InfluxDBQueryClient()

        assert client.url == 'http://localhost:8086'
        assert client.token == 'test-token'
        assert client.org == 'test-org'
        assert client.bucket == 'test-bucket'
        assert client.is_connected is False

    def test_initialization_defaults(self):
        """Test initialization with default values"""
        with patch.dict('os.environ', {}, clear=True):
            client = InfluxDBQueryClient()

            assert client.url == 'http://influxdb:8086'
            assert client.org == 'homeiq'
            assert client.bucket == 'home_assistant_events'


# ============================================================================
# Connection Tests
# ============================================================================

class TestInfluxDBConnection:
    """Test InfluxDB connection management"""

    @pytest.mark.asyncio
    @patch('influxdb_query_client.InfluxDBClient')
    @patch('aiohttp.ClientSession')
    async def test_successful_connection(self, mock_session_class, mock_client_class):
        """Test successful connection to InfluxDB"""
        # Mock health check
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock()

        mock_session_class.return_value = mock_session

        # Mock InfluxDB client
        mock_client = Mock()
        mock_query_api = Mock()
        mock_client.query_api.return_value = mock_query_api
        mock_client_class.return_value = mock_client

        client = InfluxDBQueryClient()
        result = await client.connect()

        assert result is True
        assert client.is_connected is True
        assert client.client == mock_client
        assert client.query_api == mock_query_api

    @pytest.mark.asyncio
    @patch('influxdb_query_client.InfluxDBClient', None)
    async def test_connection_without_influxdb_package(self):
        """Test graceful failure when influxdb package not installed"""
        client = InfluxDBQueryClient()
        result = await client.connect()

        assert result is False
        assert client.is_connected is False

    @pytest.mark.asyncio
    @patch('influxdb_query_client.InfluxDBClient')
    @patch('aiohttp.ClientSession')
    async def test_connection_health_check_failure(self, mock_session_class, mock_client_class):
        """Test connection failure when health check fails"""
        # Mock failed health check
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock()

        mock_session_class.return_value = mock_session

        client = InfluxDBQueryClient()

        with pytest.raises(Exception):
            await client.connect()

        assert client.is_connected is False

    @pytest.mark.asyncio
    async def test_close_connection(self, influxdb_query_client):
        """Test closing InfluxDB connection"""
        influxdb_query_client.client = Mock()
        influxdb_query_client.is_connected = True

        await influxdb_query_client.close()

        influxdb_query_client.client.close.assert_called_once()
        assert influxdb_query_client.is_connected is False
        assert influxdb_query_client.client is None


# ============================================================================
# Query Execution Tests
# ============================================================================

class TestInfluxDBQueryExecution:
    """Test query execution"""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, influxdb_query_client, mock_influxdb_query_api):
        """Test successful query execution"""
        influxdb_query_client.query_api = mock_influxdb_query_api
        influxdb_query_client.is_connected = True

        query = 'from(bucket:"test") |> range(start: -1h)'
        result = await influxdb_query_client._execute_query(query)

        assert len(result) == 1
        assert result[0]['_value'] == 100

    @pytest.mark.asyncio
    async def test_execute_query_tracks_performance(self, influxdb_query_client, mock_influxdb_query_api):
        """Test query execution tracks performance metrics"""
        influxdb_query_client.query_api = mock_influxdb_query_api
        influxdb_query_client.is_connected = True

        initial_count = influxdb_query_client.query_count

        await influxdb_query_client._execute_query('SELECT * FROM test')

        assert influxdb_query_client.query_count == initial_count + 1
        assert influxdb_query_client.avg_query_time_ms > 0

    @pytest.mark.asyncio
    async def test_execute_query_not_connected(self, influxdb_query_client):
        """Test query fails when not connected"""
        influxdb_query_client.is_connected = False

        with pytest.raises(Exception, match="not connected"):
            await influxdb_query_client._execute_query('SELECT * FROM test')


# ============================================================================
# Event Statistics Tests
# ============================================================================

class TestInfluxDBEventStatistics:
    """Test event statistics queries"""

    @pytest.mark.asyncio
    async def test_get_event_statistics(self, influxdb_query_client, mock_influxdb_query_api):
        """Test getting event statistics"""
        # Mock query response with 1000 events
        mock_record = Mock()
        mock_record.values = {"_value": 1000}
        mock_table = Mock()
        mock_table.records = [mock_record]
        mock_influxdb_query_api.query.return_value = [mock_table]

        influxdb_query_client.query_api = mock_influxdb_query_api
        influxdb_query_client.is_connected = True

        stats = await influxdb_query_client.get_event_statistics(period="1h")

        assert stats['total_events'] == 1000
        assert stats['events_per_minute'] > 0
        assert stats['period'] == "1h"

    @pytest.mark.asyncio
    async def test_get_error_rate(self, influxdb_query_client, mock_influxdb_query_api):
        """Test getting error rate statistics"""
        # Mock responses: 1000 total, 50 errors
        mock_total_record = Mock()
        mock_total_record.values = {"_value": 1000}
        mock_total_table = Mock()
        mock_total_table.records = [mock_total_record]

        mock_error_record = Mock()
        mock_error_record.values = {"_value": 50}
        mock_error_table = Mock()
        mock_error_table.records = [mock_error_record]

        mock_influxdb_query_api.query.side_effect = [
            [mock_total_table],
            [mock_error_table]
        ]

        influxdb_query_client.query_api = mock_influxdb_query_api
        influxdb_query_client.is_connected = True

        error_rate = await influxdb_query_client.get_error_rate(period="1h")

        assert error_rate['total_writes'] == 1000
        assert error_rate['write_errors'] == 50
        assert error_rate['error_rate_percent'] == 5.0


# ============================================================================
# Service Metrics Tests
# ============================================================================

class TestInfluxDBServiceMetrics:
    """Test service metrics queries"""

    @pytest.mark.asyncio
    async def test_get_service_metrics(self, influxdb_query_client, mock_influxdb_query_api):
        """Test getting service-specific metrics"""
        mock_record = Mock()
        mock_record.values = {
            "_time": "2025-11-15T00:00:00Z",
            "service": "websocket-ingestion",
            "events_processed": 5000,
            "processing_time_ms": 125.5,
            "success_rate": 99.5
        }
        mock_table = Mock()
        mock_table.records = [mock_record]
        mock_influxdb_query_api.query.return_value = [mock_table]

        influxdb_query_client.query_api = mock_influxdb_query_api
        influxdb_query_client.is_connected = True

        metrics = await influxdb_query_client.get_service_metrics("websocket-ingestion")

        assert metrics['service'] == "websocket-ingestion"
        assert metrics['events_processed'] == 5000
        assert metrics['processing_time_ms'] == 125.5
        assert metrics['success_rate'] == 99.5


# ============================================================================
# Helper Method Tests
# ============================================================================

class TestInfluxDBHelpers:
    """Test helper methods"""

    def test_period_to_seconds_conversions(self):
        """Test period string to seconds conversion"""
        client = InfluxDBQueryClient()

        assert client._period_to_seconds("15m") == 900
        assert client._period_to_seconds("1h") == 3600
        assert client._period_to_seconds("6h") == 21600
        assert client._period_to_seconds("24h") == 86400
        assert client._period_to_seconds("7d") == 604800

    def test_period_to_seconds_default(self):
        """Test unknown period returns default"""
        client = InfluxDBQueryClient()

        assert client._period_to_seconds("unknown") == 3600  # 1 hour

    def test_get_connection_status(self):
        """Test getting connection status"""
        client = InfluxDBQueryClient()
        client.is_connected = True
        client.query_count = 100
        client.error_count = 5
        client.avg_query_time_ms = 45.5

        status = client.get_connection_status()

        assert status['is_connected'] is True
        assert status['query_count'] == 100
        assert status['error_count'] == 5
        assert status['avg_query_time_ms'] == 45.5
        assert status['success_rate'] == 95.0  # (100-5)/100 * 100


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.benchmark
class TestInfluxDBPerformance:
    """Performance tests for InfluxDB client"""

    @pytest.mark.asyncio
    async def test_query_performance_target(self, influxdb_query_client, mock_influxdb_query_api, benchmark_timer):
        """Test queries meet <100ms target from CLAUDE.md"""
        influxdb_query_client.query_api = mock_influxdb_query_api
        influxdb_query_client.is_connected = True

        with benchmark_timer as timer:
            await influxdb_query_client._execute_query('SELECT * FROM test')

        # Query should be fast (mocked, but verify overhead is minimal)
        assert timer.duration_ms < 100
