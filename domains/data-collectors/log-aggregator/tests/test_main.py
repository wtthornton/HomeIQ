"""
Unit tests for Log Aggregator Service Main Application

Tests for main.py application initialization, log collection, and API endpoints.
"""

import asyncio
import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

# Mock dependencies before importing main
sys.modules['aiohttp_cors'] = MagicMock()
sys.modules['docker'] = MagicMock()
sys.modules['shared'] = MagicMock()
sys.modules['shared.logging_config'] = MagicMock()
mock_logger = MagicMock()
sys.modules['shared.logging_config'].setup_logging = MagicMock(return_value=mock_logger)

from src.main import (
    LogAggregator,
    _background_log_collection,
    app,
)


class TestLogAggregator:
    """Test suite for LogAggregator class."""

    @pytest.fixture
    def aggregator(self):
        """Create LogAggregator instance with mocked Docker client."""
        with patch('aggregator.docker') as mock_docker:
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
        with patch('aggregator.docker') as mock_docker:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_docker.from_env.return_value = mock_client
            
            agg = LogAggregator()
            
            assert agg.docker_client is not None
            assert agg.log_directory.is_dir()
            assert len(agg.aggregated_logs) == 0
            assert agg.max_logs == 10000

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_initialization_docker_failure(self):
        """Test LogAggregator initialization with Docker client failure."""
        with patch('aggregator.docker') as mock_docker:
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
        with patch('aggregator.docker') as mock_docker:
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
    """Test suite for API endpoints.

    The service is FastAPI (it was aiohttp historically), so these drive the
    real app through TestClient with the module-level aggregator stubbed.
    """

    @pytest.fixture
    def client(self):
        return TestClient(app)

    @pytest.fixture
    def mock_agg(self):
        agg = MagicMock()
        agg._api_key = ""
        agg._last_manual_collect = 0.0
        agg.aggregated_logs = []
        agg.get_recent_logs = AsyncMock(return_value=[])
        agg.search_logs = AsyncMock(return_value=[])
        agg.collect_logs = AsyncMock(return_value=[])
        with patch("src.main._aggregator", agg):
            yield agg

    @pytest.mark.unit
    def test_health_check(self, client):
        """The shared StandardHealthCheck serves /health."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "log-aggregator"
        assert "status" in data

    @pytest.mark.unit
    def test_get_logs_no_filters(self, client, mock_agg):
        """get_logs returns the aggregator's logs with echoed filters."""
        mock_agg.get_recent_logs.return_value = [{"message": "a"}, {"message": "b"}]

        response = client.get("/api/v1/logs")

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2
        assert data["filters"] == {"service": None, "level": None, "limit": 100}
        mock_agg.get_recent_logs.assert_awaited_once_with(None, None, 100)

    @pytest.mark.unit
    def test_get_logs_with_filters(self, client, mock_agg):
        """Query params are passed through to the aggregator."""
        response = client.get("/api/v1/logs?service=admin-api&level=ERROR&limit=25")

        assert response.status_code == 200
        mock_agg.get_recent_logs.assert_awaited_once_with("admin-api", "ERROR", 25)

    @pytest.mark.unit
    @pytest.mark.parametrize("limit", [0, 10001])
    def test_get_logs_rejects_out_of_range_limit(self, client, mock_agg, limit):
        """limit must fall within 1..10000."""
        response = client.get(f"/api/v1/logs?limit={limit}")

        assert response.status_code == 400
        mock_agg.get_recent_logs.assert_not_awaited()

    @pytest.mark.unit
    def test_search_logs(self, client, mock_agg):
        """search_logs echoes the query and delegates to the aggregator."""
        mock_agg.search_logs.return_value = [{"message": "hit"}]

        response = client.get("/api/v1/logs/search?q=timeout&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "timeout"
        assert data["count"] == 1
        mock_agg.search_logs.assert_awaited_once_with("timeout", 10)

    @pytest.mark.unit
    def test_search_logs_requires_query(self, client, mock_agg):
        """A missing 'q' is a client error."""
        response = client.get("/api/v1/logs/search")

        assert response.status_code == 400
        mock_agg.search_logs.assert_not_awaited()

    @pytest.mark.unit
    def test_collect_logs(self, client, mock_agg):
        """Manual collection reports how much it gathered."""
        mock_agg.collect_logs.return_value = [{"message": "1"}, {"message": "2"}]
        mock_agg.aggregated_logs = [{"message": "1"}, {"message": "2"}]

        response = client.post("/api/v1/logs/collect")

        assert response.status_code == 200
        data = response.json()
        assert data["logs_collected"] == 2
        assert data["total_logs"] == 2
        mock_agg.collect_logs.assert_awaited_once()

    @pytest.mark.unit
    def test_collect_logs_is_rate_limited(self, client, mock_agg):
        """A second collect inside the 10s window is rejected."""
        assert client.post("/api/v1/logs/collect").status_code == 200

        response = client.post("/api/v1/logs/collect")

        assert response.status_code == 429
        assert mock_agg.collect_logs.await_count == 1

    @pytest.mark.unit
    def test_collect_logs_requires_api_key_when_configured(self, client, mock_agg):
        """With an API key set, an unauthenticated collect is refused."""
        mock_agg._api_key = "secret"

        response = client.post("/api/v1/logs/collect")

        assert response.status_code == 403
        mock_agg.collect_logs.assert_not_awaited()

    @pytest.mark.unit
    def test_collect_logs_accepts_valid_api_key(self, client, mock_agg):
        """The configured key unlocks manual collection."""
        mock_agg._api_key = "secret"

        response = client.post("/api/v1/logs/collect", headers={"X-API-Key": "secret"})

        assert response.status_code == 200
        mock_agg.collect_logs.assert_awaited_once()

    @pytest.mark.unit
    def test_get_log_stats(self, client, mock_agg):
        """Stats aggregate by service and level."""
        mock_agg.aggregated_logs = [
            {"service": "admin-api", "level": "INFO"},
            {"service": "admin-api", "level": "ERROR"},
            {"service": "data-api", "level": "INFO"},
        ]

        response = client.get("/api/v1/logs/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_logs"] == 3
        assert data["services"] == {"admin-api": 2, "data-api": 1}
        assert data["levels"] == {"INFO": 2, "ERROR": 1}

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_background_log_collection(self, mock_agg):
        """The background task keeps collecting until cancelled."""
        with patch("src.main.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            mock_sleep.side_effect = [None, asyncio.CancelledError()]

            with contextlib.suppress(asyncio.CancelledError):
                await _background_log_collection()

        assert mock_agg.collect_logs.await_count >= 1
