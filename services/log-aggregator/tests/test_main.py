"""
Unit tests for Log Aggregator Service Main Application

Tests for main.py application initialization, log collection, and API endpoints.
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Mock dependencies before importing main
sys.modules['aiohttp_cors'] = MagicMock()
sys.modules['docker'] = MagicMock()
sys.modules['shared'] = MagicMock()
sys.modules['shared.logging_config'] = MagicMock()
mock_logger = MagicMock()
sys.modules['shared.logging_config'].setup_logging = MagicMock(return_value=mock_logger)

from src.main import (
    LogAggregator,
    background_log_collection,
    collect_logs,
    get_log_stats,
    get_logs,
    health_check,
    search_logs,
)


class TestLogAggregator:
    """Test suite for LogAggregator class."""

    @pytest.fixture
    def aggregator(self):
        """Create LogAggregator instance with mocked Docker client."""
        with patch('src.main.docker') as mock_docker:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_docker.from_env.return_value = mock_client
            
            agg = LogAggregator()
            agg.docker_client = mock_client
            return agg

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initialization_success(self):
        """Test LogAggregator initialization with successful Docker client."""
        with patch('src.main.docker') as mock_docker:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_docker.from_env.return_value = mock_client
            
            agg = LogAggregator()
            
            assert agg.docker_client is not None
            assert agg.log_directory == Path("/app/logs")
            assert len(agg.aggregated_logs) == 0
            assert agg.max_logs == 10000

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initialization_docker_failure(self):
        """Test LogAggregator initialization with Docker client failure."""
        with patch('src.main.docker') as mock_docker:
            mock_docker.from_env.side_effect = Exception("Docker not available")
            
            agg = LogAggregator()
            
            assert agg.docker_client is None

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_logs_success(self, aggregator):
        """Test successful log collection from Docker containers."""
        # Mock container with JSON logs
        mock_container1 = MagicMock()
        mock_container1.name = "service1"
        mock_container1.short_id = "abc123"
        mock_container1.logs.return_value = b'{"timestamp": "2025-01-01T00:00:00Z", "level": "INFO", "message": "Test log 1"}\n{"timestamp": "2025-01-01T00:00:01Z", "level": "ERROR", "message": "Test log 2"}'
        
        mock_container2 = MagicMock()
        mock_container2.name = "service2"
        mock_container2.short_id = "def456"
        mock_container2.logs.return_value = b'{"timestamp": "2025-01-01T00:00:02Z", "level": "WARNING", "message": "Test log 3"}'
        
        aggregator.docker_client.containers.list.return_value = [mock_container1, mock_container2]
        
        logs = await aggregator.collect_logs()
        
        assert len(logs) == 3
        assert logs[0]['container_name'] == "service1"
        assert logs[0]['message'] == "Test log 1"
        assert logs[1]['container_name'] == "service1"
        assert logs[2]['container_name'] == "service2"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_logs_non_json(self, aggregator):
        """Test log collection with non-JSON logs."""
        mock_container = MagicMock()
        mock_container.name = "service1"
        mock_container.short_id = "abc123"
        mock_container.logs.return_value = b'2025-01-01T00:00:00Z This is a plain text log'
        
        aggregator.docker_client.containers.list.return_value = [mock_container]
        
        logs = await aggregator.collect_logs()
        
        assert len(logs) == 1
        assert logs[0]['container_name'] == "service1"
        assert logs[0]['message'] == "This is a plain text log"
        assert logs[0]['level'] == "INFO"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_logs_no_docker_client(self):
        """Test log collection when Docker client is not available."""
        with patch('src.main.docker') as mock_docker:
            mock_docker.from_env.side_effect = Exception("Docker not available")
            
            agg = LogAggregator()
            logs = await agg.collect_logs()
            
            assert logs == []

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_logs_container_error(self, aggregator):
        """Test log collection handles container errors gracefully."""
        mock_container = MagicMock()
        mock_container.name = "service1"
        mock_container.logs.side_effect = Exception("Container error")
        
        aggregator.docker_client.containers.list.return_value = [mock_container]
        
        logs = await aggregator.collect_logs()
        
        assert len(logs) == 0

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_logs_max_logs_limit(self, aggregator):
        """Test that aggregated logs are limited to max_logs."""
        aggregator.max_logs = 5
        aggregator.aggregated_logs = [{"message": f"log{i}"} for i in range(10)]
        
        mock_container = MagicMock()
        mock_container.name = "service1"
        mock_container.short_id = "abc123"
        mock_container.logs.return_value = b'{"message": "new log"}'
        
        aggregator.docker_client.containers.list.return_value = [mock_container]
        
        await aggregator.collect_logs()
        
        assert len(aggregator.aggregated_logs) == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_recent_logs_no_filters(self, aggregator):
        """Test getting recent logs without filters."""
        aggregator.aggregated_logs = [
            {"timestamp": "2025-01-01T00:00:01Z", "message": "log1"},
            {"timestamp": "2025-01-01T00:00:02Z", "message": "log2"},
            {"timestamp": "2025-01-01T00:00:03Z", "message": "log3"},
        ]
        
        logs = await aggregator.get_recent_logs()
        
        assert len(logs) == 3
        assert logs[0]['message'] == "log3"  # Most recent first

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_recent_logs_with_service_filter(self, aggregator):
        """Test getting recent logs filtered by service."""
        aggregator.aggregated_logs = [
            {"timestamp": "2025-01-01T00:00:01Z", "service": "service1", "message": "log1"},
            {"timestamp": "2025-01-01T00:00:02Z", "service": "service2", "message": "log2"},
            {"timestamp": "2025-01-01T00:00:03Z", "service": "service1", "message": "log3"},
        ]
        
        logs = await aggregator.get_recent_logs(service="service1")
        
        assert len(logs) == 2
        assert all(log['service'] == "service1" for log in logs)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_recent_logs_with_level_filter(self, aggregator):
        """Test getting recent logs filtered by level."""
        aggregator.aggregated_logs = [
            {"timestamp": "2025-01-01T00:00:01Z", "level": "INFO", "message": "log1"},
            {"timestamp": "2025-01-01T00:00:02Z", "level": "ERROR", "message": "log2"},
            {"timestamp": "2025-01-01T00:00:03Z", "level": "INFO", "message": "log3"},
        ]
        
        logs = await aggregator.get_recent_logs(level="ERROR")
        
        assert len(logs) == 1
        assert logs[0]['level'] == "ERROR"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_recent_logs_with_limit(self, aggregator):
        """Test getting recent logs with limit."""
        aggregator.aggregated_logs = [
            {"timestamp": f"2025-01-01T00:00:{i:02d}Z", "message": f"log{i}"}
            for i in range(10)
        ]
        
        logs = await aggregator.get_recent_logs(limit=5)
        
        assert len(logs) == 5

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_logs(self, aggregator):
        """Test searching logs by query."""
        aggregator.aggregated_logs = [
            {"timestamp": "2025-01-01T00:00:01Z", "message": "Error occurred"},
            {"timestamp": "2025-01-01T00:00:02Z", "message": "Success message"},
            {"timestamp": "2025-01-01T00:00:03Z", "message": "Another error"},
        ]
        
        logs = await aggregator.search_logs("error")
        
        assert len(logs) == 2
        assert all("error" in log['message'].lower() for log in logs)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_logs_case_insensitive(self, aggregator):
        """Test search is case insensitive."""
        aggregator.aggregated_logs = [
            {"timestamp": "2025-01-01T00:00:01Z", "message": "ERROR occurred"},
            {"timestamp": "2025-01-01T00:00:02Z", "message": "Success message"},
        ]
        
        logs = await aggregator.search_logs("error")
        
        assert len(logs) == 1


class TestAPIEndpoints:
    """Test suite for API endpoints."""

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_health_check(self):
        """Test health check endpoint."""
        from aiohttp import web
        
        request = MagicMock(spec=web.Request)
        
        response = await health_check(request)
        
        assert response.status == 200
        data = json.loads(response.text)
        assert data['status'] == "healthy"
        assert data['service'] == "log-aggregator"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_logs_no_filters(self):
        """Test get_logs endpoint without filters."""
        from aiohttp import web
        
        request = MagicMock(spec=web.Request)
        request.query = {}
        
        with patch('src.main.log_aggregator') as mock_agg:
            mock_agg.get_recent_logs = AsyncMock(return_value=[
                {"timestamp": "2025-01-01T00:00:01Z", "message": "log1"}
            ])
            
            response = await get_logs(request)
            
            assert response.status == 200
            data = json.loads(response.text)
            assert len(data['logs']) == 1
            mock_agg.get_recent_logs.assert_called_once_with(None, None, 100)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_logs_with_filters(self):
        """Test get_logs endpoint with filters."""
        from aiohttp import web
        
        request = MagicMock(spec=web.Request)
        request.query = {'service': 'service1', 'level': 'ERROR', 'limit': '50'}
        
        with patch('src.main.log_aggregator') as mock_agg:
            mock_agg.get_recent_logs = AsyncMock(return_value=[])
            
            response = await get_logs(request)
            
            assert response.status == 200
            mock_agg.get_recent_logs.assert_called_once_with('service1', 'ERROR', 50)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_logs_success(self):
        """Test search_logs endpoint with query."""
        from aiohttp import web
        
        request = MagicMock(spec=web.Request)
        request.query = {'q': 'error', 'limit': '10'}
        
        with patch('src.main.log_aggregator') as mock_agg:
            mock_agg.search_logs = AsyncMock(return_value=[
                {"timestamp": "2025-01-01T00:00:01Z", "message": "Error occurred"}
            ])
            
            response = await search_logs(request)
            
            assert response.status == 200
            data = json.loads(response.text)
            assert len(data['logs']) == 1
            mock_agg.search_logs.assert_called_once_with('error', 10)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_search_logs_missing_query(self):
        """Test search_logs endpoint without query parameter."""
        from aiohttp import web
        
        request = MagicMock(spec=web.Request)
        request.query = {}
        
        response = await search_logs(request)
        
        assert response.status == 400
        data = json.loads(response.text)
        assert 'error' in data

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_collect_logs_endpoint(self):
        """Test collect_logs endpoint."""
        from aiohttp import web
        
        request = MagicMock(spec=web.Request)
        
        with patch('src.main.log_aggregator') as mock_agg:
            mock_agg.collect_logs = AsyncMock(return_value=[
                {"message": "log1"}, {"message": "log2"}
            ])
            mock_agg.aggregated_logs = [{"message": "log1"}, {"message": "log2"}]
            
            response = await collect_logs(request)
            
            assert response.status == 200
            data = json.loads(response.text)
            assert data['logs_collected'] == 2
            mock_agg.collect_logs.assert_called_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_get_log_stats(self):
        """Test get_log_stats endpoint."""
        from aiohttp import web
        
        request = MagicMock(spec=web.Request)
        
        with patch('src.main.log_aggregator') as mock_agg:
            mock_agg.aggregated_logs = [
                {"service": "service1", "level": "INFO"},
                {"service": "service1", "level": "ERROR"},
                {"service": "service2", "level": "INFO"},
            ]
            
            with patch('src.main.datetime') as mock_datetime:
                mock_datetime.utcnow.return_value = datetime(2025, 1, 1, 1, 0, 0)
                mock_datetime.fromisoformat.return_value = datetime(2025, 1, 1, 0, 30, 0)
                
                response = await get_log_stats(request)
                
                assert response.status == 200
                data = json.loads(response.text)
                assert data['total_logs'] == 3
                assert 'services' in data
                assert 'levels' in data

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_background_log_collection(self):
        """Test background log collection task."""
        with patch('src.main.log_aggregator') as mock_agg:
            mock_agg.collect_logs = AsyncMock()
            
            with patch('src.main.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
                mock_sleep.side_effect = [None, asyncio.CancelledError()]
                
                task = asyncio.create_task(background_log_collection())
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                
                assert mock_agg.collect_logs.call_count >= 1

