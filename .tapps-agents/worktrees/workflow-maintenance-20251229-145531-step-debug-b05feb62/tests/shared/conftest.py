"""
Shared Test Fixtures for HomeIQ Shared Library Tests
Modern 2025 patterns with pytest-asyncio 1.0+
"""

import asyncio
import os
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock
from typing import AsyncGenerator, Generator

# Add shared directory to path
shared_path = Path(__file__).parent.parent.parent / "shared"
sys.path.insert(0, str(shared_path))


# ============================================================================
# Test Environment Configuration
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def test_env():
    """Set up test environment variables"""
    os.environ.update({
        "LOG_LEVEL": "DEBUG",
        "LOG_FORMAT": "text",  # Easier to read in tests
        "LOG_OUTPUT": "stdout",
        "INFLUXDB_URL": "http://localhost:8086",
        "INFLUXDB_TOKEN": "test-token",
        "INFLUXDB_ORG": "test-org",
        "INFLUXDB_BUCKET": "test-bucket",
        "HA_HTTP_URL": "http://localhost:8123",
        "HA_TOKEN": "test-ha-token",
        "DOCKER_CONTAINER": "false"  # Disable SSL workarounds in tests
    })
    yield
    # Cleanup not needed as subprocess exits


# ============================================================================
# HA Connection Manager Fixtures
# ============================================================================

@pytest.fixture
def mock_websocket_connection():
    """Mock WebSocket connection for testing"""
    mock_ws = AsyncMock()
    mock_ws.recv = AsyncMock(side_effect=[
        '{"type": "auth_required", "ha_version": "2024.1.0"}',
        '{"type": "auth_ok", "ha_version": "2024.1.0"}'
    ])
    mock_ws.send = AsyncMock()
    mock_ws.close = AsyncMock()
    return mock_ws


@pytest.fixture
def mock_websockets_connect(mock_websocket_connection):
    """Mock websockets.connect() context manager"""
    async def mock_connect(*args, **kwargs):
        return mock_websocket_connection

    return Mock(return_value=mock_connect())


@pytest.fixture
def ha_connection_config():
    """Sample HA connection configuration"""
    from ha_connection_manager import HAConnectionConfig, ConnectionType

    return HAConnectionConfig(
        name="Test HA",
        url="ws://localhost:8123/api/websocket",
        token="test-token",
        connection_type=ConnectionType.PRIMARY_HA,
        priority=1,
        timeout=10,
        max_retries=3,
        retry_delay=1.0
    )


# ============================================================================
# Metrics Collector Fixtures
# ============================================================================

@pytest.fixture
def metrics_collector():
    """Create a fresh metrics collector for testing"""
    from metrics_collector import MetricsCollector

    collector = MetricsCollector(service_name="test-service")
    yield collector
    collector.reset_metrics()


@pytest.fixture
def mock_influxdb_client():
    """Mock InfluxDB client for metrics testing"""
    mock_client = Mock()
    mock_write_api = Mock()
    mock_client.write_api = Mock(return_value=mock_write_api)
    return mock_client


# ============================================================================
# InfluxDB Query Client Fixtures
# ============================================================================

@pytest.fixture
async def influxdb_query_client():
    """Create InfluxDB query client for testing"""
    from influxdb_query_client import InfluxDBQueryClient

    client = InfluxDBQueryClient()
    yield client
    await client.close()


@pytest.fixture
def mock_influxdb_query_api():
    """Mock InfluxDB query API"""
    mock_api = Mock()

    # Mock query response
    mock_record = Mock()
    mock_record.values = {
        "_time": "2025-11-15T00:00:00Z",
        "_value": 100,
        "_field": "test_field",
        "_measurement": "test_measurement",
        "service": "test-service"
    }

    mock_table = Mock()
    mock_table.records = [mock_record]

    mock_api.query = Mock(return_value=[mock_table])

    return mock_api


# ============================================================================
# Logging Fixtures
# ============================================================================

@pytest.fixture
def test_logger():
    """Create a test logger"""
    from logging_config import setup_logging

    logger = setup_logging("test-service", log_level="DEBUG", log_format="text")
    yield logger

    # Cleanup handlers
    logger.handlers.clear()


@pytest.fixture
def correlation_id_context():
    """Set up correlation ID context for testing"""
    from logging_config import set_correlation_id, correlation_id

    test_corr_id = "test_corr_12345678"
    set_correlation_id(test_corr_id)

    yield test_corr_id

    # Cleanup
    correlation_id.set(None)


# ============================================================================
# Correlation Middleware Fixtures
# ============================================================================

@pytest.fixture
def mock_request():
    """Mock HTTP request with headers"""
    request = Mock()
    request.headers = {
        "X-Correlation-ID": "test_correlation_123",
        "Content-Type": "application/json"
    }
    return request


@pytest.fixture
def mock_response():
    """Mock HTTP response"""
    response = Mock()
    response.headers = {}
    response.status = 200
    return response


# ============================================================================
# Async Utilities
# ============================================================================

@pytest.fixture
def anyio_backend():
    """Use asyncio as the async backend"""
    return "asyncio"


# ============================================================================
# Property-Based Testing Configuration
# ============================================================================

from hypothesis import settings, Verbosity

# Configure Hypothesis for testing
settings.register_profile("default", max_examples=50, deadline=5000)
settings.register_profile("ci", max_examples=100, deadline=10000)
settings.register_profile("debug", max_examples=10, verbosity=Verbosity.verbose)

# Activate default profile
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "default"))


# ============================================================================
# Benchmark Fixtures
# ============================================================================

@pytest.fixture
def benchmark_timer():
    """Simple benchmark timer for performance tests"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.duration_ms = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()
            self.duration_ms = (self.end_time - self.start_time) * 1000

    return Timer


# ============================================================================
# Cleanup
# ============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests"""
    yield

    # Clear metrics collectors
    try:
        from metrics_collector import _metrics_collectors
        _metrics_collectors.clear()
    except:
        pass
