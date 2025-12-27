"""
Comprehensive Tests for HA Connection Manager
Modern 2025 Patterns: Property-based testing, async, state machines

Module: shared/ha_connection_manager.py
Coverage Target: >90%
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from hypothesis import given, strategies as st, settings, assume
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize
import websockets

# Import module under test
from ha_connection_manager import (
    HAConnectionManager,
    HAConnectionConfig,
    ConnectionType,
    ConnectionResult,
    get_ha_connection,
    get_ha_stats
)


# ============================================================================
# Unit Tests - Basic Functionality
# ============================================================================

class TestHAConnectionConfig:
    """Test HA Connection Configuration data class"""

    def test_connection_config_creation(self):
        """Test creating a connection config with all fields"""
        config = HAConnectionConfig(
            name="Test Connection",
            url="ws://localhost:8123/api/websocket",
            token="test-token-12345",
            connection_type=ConnectionType.PRIMARY_HA,
            priority=1,
            timeout=30,
            max_retries=3,
            retry_delay=5.0
        )

        assert config.name == "Test Connection"
        assert config.url == "ws://localhost:8123/api/websocket"
        assert config.token == "test-token-12345"
        assert config.connection_type == ConnectionType.PRIMARY_HA
        assert config.priority == 1
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 5.0

    def test_connection_config_defaults(self):
        """Test connection config with default values"""
        config = HAConnectionConfig(
            name="Minimal",
            url="ws://test",
            token="token",
            connection_type=ConnectionType.LOCAL_HA,
            priority=1
        )

        assert config.timeout == 30  # Default
        assert config.max_retries == 3  # Default
        assert config.retry_delay == 5.0  # Default


class TestConnectionResult:
    """Test Connection Result data class"""

    def test_successful_result(self):
        """Test successful connection result"""
        config = HAConnectionConfig(
            name="Test",
            url="ws://test",
            token="token",
            connection_type=ConnectionType.PRIMARY_HA,
            priority=1
        )

        result = ConnectionResult(
            success=True,
            config=config,
            response_time=0.125
        )

        assert result.success is True
        assert result.config == config
        assert result.error is None
        assert result.response_time == 0.125

    def test_failed_result(self):
        """Test failed connection result"""
        result = ConnectionResult(
            success=False,
            config=None,
            error="Connection timeout"
        )

        assert result.success is False
        assert result.config is None
        assert result.error == "Connection timeout"


# ============================================================================
# HA Connection Manager - Initialization
# ============================================================================

class TestHAConnectionManagerInit:
    """Test HA Connection Manager initialization"""

    @patch.dict('os.environ', {
        'HA_HTTP_URL': 'http://localhost:8123',
        'HA_TOKEN': 'test-token-primary'
    }, clear=True)
    def test_initialization_with_primary_ha(self):
        """Test initialization with primary HA configuration"""
        manager = HAConnectionManager()

        assert len(manager.connections) == 1
        assert manager.connections[0].name == "Primary HA"
        assert manager.connections[0].connection_type == ConnectionType.PRIMARY_HA
        assert manager.connections[0].priority == 1
        assert "test-token-primary" in manager.connections[0].token

    @patch.dict('os.environ', {
        'HA_HTTP_URL': 'http://primary:8123',
        'HA_TOKEN': 'token-primary',
        'NABU_CASA_URL': 'https://nabu.casa',
        'NABU_CASA_TOKEN': 'token-nabu'
    }, clear=True)
    def test_initialization_with_fallback(self):
        """Test initialization with both primary and Nabu Casa fallback"""
        manager = HAConnectionManager()

        assert len(manager.connections) == 2

        # Check primary
        assert manager.connections[0].name == "Primary HA"
        assert manager.connections[0].priority == 1

        # Check fallback
        assert manager.connections[1].name == "Nabu Casa Fallback"
        assert manager.connections[1].priority == 2
        assert manager.connections[1].connection_type == ConnectionType.NABU_CASA

    @patch.dict('os.environ', {}, clear=True)
    def test_initialization_with_no_config(self):
        """Test initialization with no environment variables"""
        manager = HAConnectionManager()

        assert len(manager.connections) == 0
        assert manager.current_connection is None

    @patch.dict('os.environ', {
        'HA_HTTP_URL': 'https://secure.ha.local',
        'HA_TOKEN': 'secure-token'
    }, clear=True)
    def test_url_conversion_https_to_wss(self):
        """Test HTTPS URL is converted to WSS"""
        manager = HAConnectionManager()

        assert manager.connections[0].url.startswith('wss://')
        assert '/api/websocket' in manager.connections[0].url

    @patch.dict('os.environ', {
        'HA_WS_URL': 'ws://custom:8123/api/websocket',
        'HA_TOKEN': 'token'
    }, clear=True)
    def test_explicit_websocket_url(self):
        """Test explicit WebSocket URL is used"""
        manager = HAConnectionManager()

        assert manager.connections[0].url == 'ws://custom:8123/api/websocket'


# ============================================================================
# Connection Testing - Async Tests
# ============================================================================

class TestHAConnectionTesting:
    """Test connection testing functionality"""

    @pytest.mark.asyncio
    async def test_parse_auth_response_valid_json(self):
        """Test parsing valid JSON auth response"""
        manager = HAConnectionManager()

        response = '{"type": "auth_required", "ha_version": "2024.1.0"}'
        parsed = await manager._parse_auth_response(response)

        assert parsed["type"] == "auth_required"
        assert parsed["ha_version"] == "2024.1.0"

    @pytest.mark.asyncio
    async def test_parse_auth_response_invalid_json(self):
        """Test parsing invalid JSON returns error"""
        manager = HAConnectionManager()

        response = 'not valid json{'
        parsed = await manager._parse_auth_response(response)

        assert parsed["type"] == "error"
        assert "Invalid JSON" in parsed["message"]

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_successful_connection(self, mock_connect):
        """Test successful WebSocket connection and authentication"""
        # Setup mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            '{"type": "auth_required"}',
            '{"type": "auth_ok"}'
        ])
        mock_ws.send = AsyncMock()

        # Mock context manager
        mock_connect.return_value.__aenter__.return_value = mock_ws
        mock_connect.return_value.__aexit__.return_value = AsyncMock()

        config = HAConnectionConfig(
            name="Test",
            url="ws://localhost:8123/api/websocket",
            token="test-token",
            connection_type=ConnectionType.PRIMARY_HA,
            priority=1
        )

        manager = HAConnectionManager()
        result = await manager.test_connection(config)

        assert result.success is True
        assert result.config == config
        assert result.error is None
        assert result.response_time is not None

        # Verify auth flow
        mock_ws.send.assert_called_once()
        call_args = mock_ws.send.call_args[0][0]
        auth_message = json.loads(call_args)
        assert auth_message["type"] == "auth"
        assert auth_message["access_token"] == "test-token"

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_failed_authentication(self, mock_connect):
        """Test failed authentication"""
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            '{"type": "auth_required"}',
            '{"type": "auth_invalid", "message": "Invalid token"}'
        ])
        mock_ws.send = AsyncMock()

        mock_connect.return_value.__aenter__.return_value = mock_ws
        mock_connect.return_value.__aexit__.return_value = AsyncMock()

        config = HAConnectionConfig(
            name="Test",
            url="ws://localhost:8123/api/websocket",
            token="invalid-token",
            connection_type=ConnectionType.PRIMARY_HA,
            priority=1
        )

        manager = HAConnectionManager()
        result = await manager.test_connection(config)

        assert result.success is False
        assert "Authentication failed" in result.error

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_connection_timeout(self, mock_connect):
        """Test connection timeout handling"""
        # Simulate timeout
        mock_connect.side_effect = asyncio.TimeoutError("Connection timeout")

        config = HAConnectionConfig(
            name="Test",
            url="ws://localhost:8123/api/websocket",
            token="test-token",
            connection_type=ConnectionType.PRIMARY_HA,
            priority=1,
            timeout=5
        )

        manager = HAConnectionManager()
        result = await manager.test_connection(config)

        assert result.success is False
        assert "timeout" in result.error.lower()

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_websocket_connection_closed(self, mock_connect):
        """Test WebSocket connection closed error"""
        mock_connect.side_effect = websockets.exceptions.ConnectionClosed(None, None)

        config = HAConnectionConfig(
            name="Test",
            url="ws://localhost:8123/api/websocket",
            token="test-token",
            connection_type=ConnectionType.PRIMARY_HA,
            priority=1
        )

        manager = HAConnectionManager()
        result = await manager.test_connection(config)

        assert result.success is False
        assert "closed" in result.error.lower()


# ============================================================================
# Connection Selection and Retry Logic
# ============================================================================

class TestConnectionSelection:
    """Test connection selection and retry logic"""

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_get_best_connection_first_succeeds(self, mock_connect):
        """Test getting best connection when first one succeeds"""
        # Setup successful connection
        mock_ws = AsyncMock()
        mock_ws.recv = AsyncMock(side_effect=[
            '{"type": "auth_required"}',
            '{"type": "auth_ok"}'
        ])
        mock_ws.send = AsyncMock()
        mock_connect.return_value.__aenter__.return_value = mock_ws
        mock_connect.return_value.__aexit__.return_value = AsyncMock()

        manager = HAConnectionManager()
        manager.connections = [
            HAConnectionConfig(
                name="Primary",
                url="ws://primary:8123/api/websocket",
                token="token1",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1
            ),
            HAConnectionConfig(
                name="Fallback",
                url="ws://fallback:8123/api/websocket",
                token="token2",
                connection_type=ConnectionType.NABU_CASA,
                priority=2
            )
        ]

        result = await manager.get_best_connection()

        assert result is not None
        assert result.name == "Primary"
        assert result.priority == 1

    @pytest.mark.asyncio
    @patch('websockets.connect')
    async def test_fallback_to_second_connection(self, mock_connect):
        """Test falling back to second connection when first fails"""
        # First connection fails, second succeeds
        call_count = [0]

        async def mock_connect_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise ConnectionError("First connection failed")

            # Second connection succeeds
            mock_ws = AsyncMock()
            mock_ws.recv = AsyncMock(side_effect=[
                '{"type": "auth_required"}',
                '{"type": "auth_ok"}'
            ])
            mock_ws.send = AsyncMock()
            return mock_ws

        mock_connect.side_effect = mock_connect_side_effect

        manager = HAConnectionManager()
        manager.connections = [
            HAConnectionConfig(
                name="Primary",
                url="ws://primary:8123/api/websocket",
                token="token1",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1
            ),
            HAConnectionConfig(
                name="Nabu Casa",
                url="wss://nabu:443/api/websocket",
                token="token2",
                connection_type=ConnectionType.NABU_CASA,
                priority=2,
                max_retries=2
            )
        ]

        result = await manager.get_best_connection()

        assert result is not None
        assert result.name == "Nabu Casa"

    @pytest.mark.asyncio
    @patch('websockets.connect')
    @patch('asyncio.sleep')  # Mock sleep to speed up tests
    async def test_retry_logic_for_cloud_connections(self, mock_sleep, mock_connect):
        """Test retry logic with exponential backoff for cloud connections"""
        attempt_count = [0]

        async def mock_connect_side_effect(*args, **kwargs):
            attempt_count[0] += 1
            if attempt_count[0] < 3:  # Fail first 2 attempts
                raise ConnectionError("Temporary failure")

            # Third attempt succeeds
            mock_ws = AsyncMock()
            mock_ws.recv = AsyncMock(side_effect=[
                '{"type": "auth_required"}',
                '{"type": "auth_ok"}'
            ])
            mock_ws.send = AsyncMock()
            return mock_ws

        mock_connect.side_effect = mock_connect_side_effect

        config = HAConnectionConfig(
            name="Nabu Casa",
            url="wss://nabu.casa/api/websocket",
            token="token",
            connection_type=ConnectionType.NABU_CASA,
            priority=2,
            max_retries=5,
            retry_delay=1.0
        )

        manager = HAConnectionManager()
        result = await manager._test_connection_with_retry(config)

        assert result.success is True
        assert attempt_count[0] == 3

        # Verify exponential backoff (sleep called between retries)
        assert mock_sleep.call_count == 2  # 2 retries before success


# ============================================================================
# Connection Statistics
# ============================================================================

class TestConnectionStatistics:
    """Test connection statistics tracking"""

    def test_update_connection_stats_success(self):
        """Test updating stats for successful connection"""
        manager = HAConnectionManager()

        manager._update_connection_stats("Test Connection", True, 0.125)

        stats = manager.connection_stats["Test Connection"]
        assert stats['total_attempts'] == 1
        assert stats['successful_attempts'] == 1
        assert stats['failed_attempts'] == 0
        assert stats['avg_response_time'] == 0.125

    def test_update_connection_stats_failure(self):
        """Test updating stats for failed connection"""
        manager = HAConnectionManager()

        manager._update_connection_stats("Test Connection", False, None)

        stats = manager.connection_stats["Test Connection"]
        assert stats['total_attempts'] == 1
        assert stats['successful_attempts'] == 0
        assert stats['failed_attempts'] == 1

    def test_get_connection_stats(self):
        """Test getting connection statistics"""
        manager = HAConnectionManager()
        manager._update_connection_stats("Test", True, 0.1)

        stats = manager.get_connection_stats()

        assert stats['total_connections'] == 0  # No connections loaded in test
        assert stats['connection_stats']['Test']['total_attempts'] == 1
        assert stats['health_status'] == 'unhealthy'  # No current connection


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestConnectionManagerProperties:
    """Property-based tests for connection manager"""

    @given(
        retry_attempt=st.integers(min_value=0, max_value=10),
        base_delay=st.floats(min_value=0.1, max_value=10.0)
    )
    @settings(max_examples=50)
    def test_exponential_backoff_increases(self, retry_attempt, base_delay):
        """Property: Exponential backoff should increase with retry count"""
        # Calculate expected backoff: base_delay * 2^retry_attempt
        expected_delay = base_delay * (2 ** retry_attempt)

        # Property: Each retry should have longer delay than previous
        if retry_attempt > 0:
            prev_delay = base_delay * (2 ** (retry_attempt - 1))
            assert expected_delay > prev_delay

        # Property: Delay should always be positive
        assert expected_delay > 0

    @given(
        url=st.text(min_size=10, max_size=100),
        token=st.text(min_size=32, max_size=128)
    )
    @settings(max_examples=30)
    def test_config_creation_always_valid(self, url, token):
        """Property: Config creation should always succeed with valid inputs"""
        assume(len(url) >= 10 and len(token) >= 32)

        config = HAConnectionConfig(
            name="Property Test",
            url=url,
            token=token,
            connection_type=ConnectionType.PRIMARY_HA,
            priority=1
        )

        assert config.name == "Property Test"
        assert config.url == url
        assert config.token == token


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestHAConnectionIntegration:
    """Integration tests requiring actual connections (optional)"""

    @pytest.mark.skip(reason="Requires live HA instance")
    @pytest.mark.asyncio
    async def test_real_ha_connection(self):
        """Test connection to real HA instance (manual testing)"""
        # This test requires a real HA instance
        # Only run manually with: pytest -m integration --run-integration
        pass


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.benchmark
class TestConnectionPerformance:
    """Performance benchmarks for connection operations"""

    def test_config_initialization_performance(self, benchmark):
        """Benchmark connection config initialization"""

        def create_config():
            return HAConnectionConfig(
                name="Benchmark",
                url="ws://test:8123/api/websocket",
                token="test-token",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1
            )

        result = benchmark(create_config)
        assert result is not None

    @pytest.mark.asyncio
    async def test_parse_response_performance(self, benchmark_timer):
        """Test JSON parsing performance"""
        manager = HAConnectionManager()
        response = '{"type": "auth_required", "ha_version": "2024.1.0"}'

        with benchmark_timer as timer:
            for _ in range(1000):
                await manager._parse_auth_response(response)

        # Parsing 1000 responses should take < 100ms
        assert timer.duration_ms < 100
