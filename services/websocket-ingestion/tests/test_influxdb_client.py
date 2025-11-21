"""
Tests for InfluxDB Client
"""

import pytest

pytest.skip(
    "Legacy websocket-ingestion InfluxDB client tests require removed module",
    allow_module_level=True,
)

import asyncio
from unittest.mock import Mock, patch

from src.influxdb_client import InfluxDBConnectionManager


class TestInfluxDBConnectionManager:
    """Test cases for InfluxDBConnectionManager class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.connection_manager = InfluxDBConnectionManager(
            url="http://localhost:8086",
            token="test-token",
            org="test-org",
            bucket="test-bucket",
        )

    def teardown_method(self):
        """Clean up after tests"""
        if self.connection_manager.is_running:
            asyncio.run(self.connection_manager.stop())

    def test_initialization(self):
        """Test connection manager initialization"""
        assert self.connection_manager.url == "http://localhost:8086"
        assert self.connection_manager.token == "test-token"
        assert self.connection_manager.org == "test-org"
        assert self.connection_manager.bucket == "test-bucket"
        assert self.connection_manager.timeout == 30
        assert self.connection_manager.retry_attempts == 3
        assert self.connection_manager.retry_delay == 1.0
        assert not self.connection_manager.is_connected
        assert not self.connection_manager.is_running

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test starting and stopping the connection manager"""
        # Mock InfluxDB client
        with patch("src.influxdb_client.InfluxDBClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock query API
            mock_query_api = Mock()
            mock_client.query_api.return_value = mock_query_api

            # Mock write API
            mock_write_api = Mock()
            mock_client.write_api.return_value = mock_write_api

            # Start connection manager
            await self.connection_manager.start()
            assert self.connection_manager.is_running
            assert self.connection_manager.client is not None

            # Stop connection manager
            await self.connection_manager.stop()
            assert not self.connection_manager.is_running
            assert self.connection_manager.client is None

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test successful connection"""
        with patch("src.influxdb_client.InfluxDBClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock query API for connection test
            mock_query_api = Mock()
            mock_client.query_api.return_value = mock_query_api

            # Mock write API
            mock_write_api = Mock()
            mock_client.write_api.return_value = mock_write_api

            # Mock successful query
            mock_query_api.query.return_value = []

            # Test connection
            success = await self.connection_manager._connect()

            assert success
            assert self.connection_manager.is_connected
            assert self.connection_manager.successful_connections == 1
            assert self.connection_manager.failed_connections == 0

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test connection failure"""
        with patch("src.influxdb_client.InfluxDBClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock query API for connection test
            mock_query_api = Mock()
            mock_client.query_api.return_value = mock_query_api

            # Mock failed query
            mock_query_api.query.side_effect = Exception("Connection failed")

            # Test connection
            success = await self.connection_manager._connect()

            assert not success
            assert not self.connection_manager.is_connected
            assert self.connection_manager.successful_connections == 0
            assert self.connection_manager.failed_connections == 1
            assert "Connection failed" in self.connection_manager.last_error

    @pytest.mark.asyncio
    async def test_write_points_success(self):
        """Test successful point writing"""
        with patch("src.influxdb_client.InfluxDBClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock query API for connection test
            mock_query_api = Mock()
            mock_client.query_api.return_value = mock_query_api

            # Mock write API
            mock_write_api = Mock()
            mock_client.write_api.return_value = mock_write_api

            # Mock successful query for connection test
            mock_query_api.query.return_value = []

            # Start connection manager
            await self.connection_manager.start()

            # Mock successful write
            mock_write_api.write.return_value = None

            # Test writing points
            mock_points = [Mock(), Mock()]
            success = await self.connection_manager.write_points(mock_points)

            assert success
            mock_write_api.write.assert_called_once()

    @pytest.mark.asyncio
    async def test_write_points_failure(self):
        """Test point writing failure"""
        with patch("src.influxdb_client.InfluxDBClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock query API for connection test
            mock_query_api = Mock()
            mock_client.query_api.return_value = mock_query_api

            # Mock write API
            mock_write_api = Mock()
            mock_client.write_api.return_value = mock_write_api

            # Mock successful query for connection test
            mock_query_api.query.return_value = []

            # Start connection manager
            await self.connection_manager.start()

            # Mock failed write
            mock_write_api.write.side_effect = Exception("Write failed")

            # Test writing points
            mock_points = [Mock(), Mock()]
            success = await self.connection_manager.write_points(mock_points)

            assert not success
            assert "Write failed" in self.connection_manager.last_error

    @pytest.mark.asyncio
    async def test_query_data_success(self):
        """Test successful data querying"""
        with patch("src.influxdb_client.InfluxDBClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock query API for connection test
            mock_query_api = Mock()
            mock_client.query_api.return_value = mock_query_api

            # Mock write API
            mock_write_api = Mock()
            mock_client.write_api.return_value = mock_write_api

            # Mock successful query for connection test
            mock_query_api.query.return_value = []

            # Start connection manager
            await self.connection_manager.start()

            # Mock query result
            mock_record = Mock()
            mock_record.get_time.return_value = "2023-01-01T00:00:00Z"
            mock_record.get_measurement.return_value = "test_measurement"
            mock_record.values = {"field1": "value1", "field2": "value2"}

            mock_table = Mock()
            mock_table.records = [mock_record]
            mock_query_api.query.return_value = [mock_table]

            # Test querying data
            result = await self.connection_manager.query_data("SELECT * FROM test_measurement")

            assert len(result) == 1
            assert result[0]["measurement"] == "test_measurement"
            assert result[0]["fields"]["field1"] == "value1"

    @pytest.mark.asyncio
    async def test_query_data_failure(self):
        """Test data querying failure"""
        with patch("src.influxdb_client.InfluxDBClient") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock query API for connection test
            mock_query_api = Mock()
            mock_client.query_api.return_value = mock_query_api

            # Mock write API
            mock_write_api = Mock()
            mock_client.write_api.return_value = mock_write_api

            # Mock successful query for connection test
            mock_query_api.query.return_value = []

            # Start connection manager
            await self.connection_manager.start()

            # Mock failed query
            mock_query_api.query.side_effect = Exception("Query failed")

            # Test querying data
            result = await self.connection_manager.query_data("SELECT * FROM test_measurement")

            assert result == []
            assert "Query failed" in self.connection_manager.last_error

    def test_get_connection_status(self):
        """Test getting connection status"""
        # Set some status
        self.connection_manager.connection_attempts = 5
        self.connection_manager.successful_connections = 3
        self.connection_manager.failed_connections = 2
        self.connection_manager.last_error = "Test error"

        status = self.connection_manager.get_connection_status()

        assert status["url"] == "http://localhost:8086"
        assert status["org"] == "test-org"
        assert status["bucket"] == "test-bucket"
        assert status["connection_attempts"] == 5
        assert status["successful_connections"] == 3
        assert status["failed_connections"] == 2
        assert status["last_error"] == "Test error"
        assert status["timeout"] == 30
        assert status["retry_attempts"] == 3
        assert status["retry_delay"] == 1.0

    def test_configure_health_check_interval(self):
        """Test configuring health check interval"""
        self.connection_manager.configure_health_check_interval(120)
        assert self.connection_manager.health_check_interval == 120

        # Test invalid interval
        with pytest.raises(ValueError):
            self.connection_manager.configure_health_check_interval(0)

    def test_configure_retry_settings(self):
        """Test configuring retry settings"""
        self.connection_manager.configure_retry_settings(5, 2.0)
        assert self.connection_manager.retry_attempts == 5
        assert self.connection_manager.retry_delay == 2.0

        # Test invalid settings
        with pytest.raises(ValueError):
            self.connection_manager.configure_retry_settings(-1, 1.0)

        with pytest.raises(ValueError):
            self.connection_manager.configure_retry_settings(3, -1.0)

    def test_reset_statistics(self):
        """Test resetting statistics"""
        # Set some statistics
        self.connection_manager.connection_attempts = 10
        self.connection_manager.successful_connections = 8
        self.connection_manager.failed_connections = 2
        self.connection_manager.last_error = "Test error"

        # Reset statistics
        self.connection_manager.reset_statistics()

        assert self.connection_manager.connection_attempts == 0
        assert self.connection_manager.successful_connections == 0
        assert self.connection_manager.failed_connections == 0
        assert self.connection_manager.last_error is None
