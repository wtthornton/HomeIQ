"""
Comprehensive Tests for Enhanced HA Connection Manager with Circuit Breaker
Modern 2025 Patterns: State machine testing, property-based testing

Module: shared/enhanced_ha_connection_manager.py
Coverage Target: >90%
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from hypothesis import given, strategies as st, settings
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, initialize
from datetime import datetime, timedelta

# Import module under test
from enhanced_ha_connection_manager import (
    EnhancedHAConnectionManager,
    CircuitBreaker,
    CircuitBreakerState,
    HAConnectionConfig,
    ConnectionType,
    ha_connection_manager
)


# ============================================================================
# Circuit Breaker Unit Tests
# ============================================================================

class TestCircuitBreaker:
    """Test Circuit Breaker implementation"""

    def test_initial_state_is_closed(self):
        """Test circuit breaker starts in CLOSED state"""
        breaker = CircuitBreaker(name="test", fail_max=5)

        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.failures == 0
        assert breaker.successes == 0

    def test_can_execute_when_closed(self):
        """Test requests can execute when circuit is CLOSED"""
        breaker = CircuitBreaker(name="test")

        assert breaker.can_execute() is True

    def test_cannot_execute_when_open(self):
        """Test requests blocked when circuit is OPEN"""
        breaker = CircuitBreaker(name="test", fail_max=3)

        # Trigger failures to open circuit
        for _ in range(3):
            breaker.record_failure(Exception("Test failure"))

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_execute() is False

    def test_transition_to_open_after_max_failures(self):
        """Test circuit opens after max failures reached"""
        breaker = CircuitBreaker(name="test", fail_max=5)

        # Record failures
        for i in range(4):
            breaker.record_failure(Exception(f"Failure {i}"))
            assert breaker.state == CircuitBreakerState.CLOSED

        # 5th failure should open circuit
        breaker.record_failure(Exception("Final failure"))
        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.failures == 5

    def test_transition_to_half_open_after_timeout(self):
        """Test circuit transitions to HALF_OPEN after reset timeout"""
        breaker = CircuitBreaker(
            name="test",
            fail_max=3,
            reset_timeout=1  # 1 second
        )

        # Open the circuit
        for _ in range(3):
            breaker.record_failure(Exception("Failure"))

        assert breaker.state == CircuitBreakerState.OPEN

        # Simulate time passing
        breaker.last_failure_time = datetime.now() - timedelta(seconds=2)

        # Should transition to HALF_OPEN
        assert breaker.can_execute() is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN

    def test_half_open_success_closes_circuit(self):
        """Test successful requests in HALF_OPEN close the circuit"""
        breaker = CircuitBreaker(
            name="test",
            fail_max=3,
            success_threshold=2
        )

        # Set to HALF_OPEN manually
        breaker.state = CircuitBreakerState.HALF_OPEN

        # Record successes
        breaker.record_success()
        assert breaker.state == CircuitBreakerState.HALF_OPEN  # Need 2 successes

        breaker.record_success()
        assert breaker.state == CircuitBreakerState.CLOSED  # Now closed
        assert breaker.failures == 0  # Failures reset

    def test_half_open_failure_reopens_circuit(self):
        """Test failure in HALF_OPEN reopens the circuit"""
        breaker = CircuitBreaker(name="test", fail_max=3)

        # Set to HALF_OPEN manually
        breaker.state = CircuitBreakerState.HALF_OPEN

        # Single failure should reopen
        breaker.record_failure(Exception("Failed again"))

        assert breaker.state == CircuitBreakerState.OPEN

    def test_get_stats(self):
        """Test circuit breaker statistics"""
        breaker = CircuitBreaker(name="test-breaker", fail_max=5)

        breaker.record_success()
        breaker.record_success()
        breaker.record_failure(Exception("Error"))

        stats = breaker.get_stats()

        assert stats['name'] == "test-breaker"
        assert stats['state'] == CircuitBreakerState.CLOSED.value
        assert stats['successes'] == 2
        assert stats['failures'] == 1
        assert stats['last_success_time'] is not None
        assert stats['last_failure_time'] is not None

    def test_state_changes_counter(self):
        """Test state changes are tracked"""
        breaker = CircuitBreaker(name="test", fail_max=2, success_threshold=1)

        initial_changes = breaker.state_changes

        # Open circuit (state change #1)
        for _ in range(2):
            breaker.record_failure(Exception("Fail"))

        assert breaker.state_changes == initial_changes + 1

        # Transition to HALF_OPEN (state change #2)
        breaker.last_failure_time = datetime.now() - timedelta(seconds=100)
        breaker.can_execute()

        assert breaker.state_changes == initial_changes + 2

        # Close circuit (state change #3)
        breaker.record_success()

        assert breaker.state_changes == initial_changes + 3


# ============================================================================
# Enhanced Connection Manager Tests
# ============================================================================

class TestEnhancedHAConnectionManager:
    """Test Enhanced HA Connection Manager"""

    @patch.dict('os.environ', {
        'HA_HTTP_URL': 'http://localhost:8123',
        'HA_TOKEN': 'test-token'
    }, clear=True)
    def test_initialization_creates_circuit_breakers(self):
        """Test circuit breakers are created for each connection"""
        manager = EnhancedHAConnectionManager()

        assert len(manager.circuit_breakers) == len(manager.connections)

        for connection in manager.connections:
            assert connection.name in manager.circuit_breakers
            assert connection.name in manager.connection_stats

    @patch.dict('os.environ', {
        'HA_HTTP_URL': 'http://primary:8123',
        'HA_TOKEN': 'token1',
        'NABU_CASA_URL': 'https://nabu.casa',
        'NABU_CASA_TOKEN': 'token2'
    }, clear=True)
    def test_circuit_breaker_config_applied(self):
        """Test circuit breaker configuration is applied correctly"""
        manager = EnhancedHAConnectionManager()

        # Check circuit breakers exist
        assert "Primary HA" in manager.circuit_breakers
        assert "Nabu Casa Fallback" in manager.circuit_breakers

        # Check default config
        primary_breaker = manager.circuit_breakers["Primary HA"]
        assert primary_breaker.fail_max == 5
        assert primary_breaker.reset_timeout == 60
        assert primary_breaker.success_threshold == 3

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_successful_connection_with_circuit_breaker(self, mock_session_class):
        """Test successful connection updates circuit breaker"""
        # Mock successful HTTP response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock()

        mock_session_class.return_value = mock_session

        manager = EnhancedHAConnectionManager()
        manager.connections = [
            HAConnectionConfig(
                name="Test",
                url="ws://localhost:8123/api/websocket",
                token="token",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1
            )
        ]
        manager._create_circuit_breaker(manager.connections[0])

        result = await manager.get_connection_with_circuit_breaker()

        assert result is not None
        assert result.name == "Test"

        # Check circuit breaker recorded success
        breaker = manager.circuit_breakers["Test"]
        assert breaker.successes == 1
        assert breaker.state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_failed_connection_updates_circuit_breaker(self, mock_session_class):
        """Test failed connection updates circuit breaker"""
        # Mock failed connection
        mock_session_class.side_effect = ConnectionError("Connection failed")

        manager = EnhancedHAConnectionManager()
        manager.connections = [
            HAConnectionConfig(
                name="Test",
                url="ws://localhost:8123/api/websocket",
                token="token",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1
            )
        ]
        manager._create_circuit_breaker(manager.connections[0])

        result = await manager.get_connection_with_circuit_breaker()

        # Check circuit breaker recorded failure
        breaker = manager.circuit_breakers["Test"]
        assert breaker.failures == 1

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_open_circuit_breaker_skips_connection(self, mock_session_class):
        """Test connections with OPEN circuit breaker are skipped"""
        manager = EnhancedHAConnectionManager()
        manager.connections = [
            HAConnectionConfig(
                name="Broken",
                url="ws://broken:8123/api/websocket",
                token="token1",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1
            ),
            HAConnectionConfig(
                name="Working",
                url="ws://working:8123/api/websocket",
                token="token2",
                connection_type=ConnectionType.NABU_CASA,
                priority=2
            )
        ]

        for conn in manager.connections:
            manager._create_circuit_breaker(conn)

        # Open first circuit breaker
        breaker = manager.circuit_breakers["Broken"]
        breaker.state = CircuitBreakerState.OPEN

        # Mock second connection to succeed
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock()

        mock_session_class.return_value = mock_session

        result = await manager.get_connection_with_circuit_breaker()

        # Should skip broken connection and use working one
        assert result is not None
        assert result.name == "Working"

    def test_get_connection_status(self):
        """Test getting comprehensive connection status"""
        manager = EnhancedHAConnectionManager()
        manager.connections = [
            HAConnectionConfig(
                name="Test",
                url="ws://test:8123/api/websocket",
                token="token",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1
            )
        ]
        manager._create_circuit_breaker(manager.connections[0])

        status = manager.get_connection_status()

        assert status['total_connections'] == 1
        assert len(status['connections']) == 1
        assert status['connections'][0]['name'] == "Test"
        assert 'circuit_breaker' in status['connections'][0]
        assert 'Test' in status['circuit_breakers']

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_health_check_all_connections(self, mock_session_class):
        """Test health check checks all connections"""
        # Mock responses: first fails, second succeeds
        call_count = [0]

        def mock_session_factory(*args, **kwargs):
            call_count[0] += 1
            mock_session = AsyncMock()

            if call_count[0] == 1:
                # First connection fails
                mock_session.__aenter__.side_effect = ConnectionError("Failed")
            else:
                # Second connection succeeds
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.__aenter__.return_value = mock_response
                mock_response.__aexit__.return_value = AsyncMock()

                mock_session.get.return_value = mock_response
                mock_session.__aenter__.return_value = mock_session

            mock_session.__aexit__.return_value = AsyncMock()
            return mock_session

        mock_session_class.side_effect = mock_session_factory

        manager = EnhancedHAConnectionManager()
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

        for conn in manager.connections:
            manager._create_circuit_breaker(conn)

        health = await manager.health_check()

        assert len(health['connections']) == 2
        assert health['connections'][0]['healthy'] is False
        assert health['connections'][1]['healthy'] is True
        assert health['overall_health'] == 'degraded'


# ============================================================================
# Property-Based Tests for Circuit Breaker
# ============================================================================

class TestCircuitBreakerProperties:
    """Property-based tests for circuit breaker behavior"""

    @given(
        fail_max=st.integers(min_value=1, max_value=20),
        num_failures=st.integers(min_value=0, max_value=30)
    )
    @settings(max_examples=50)
    def test_circuit_opens_at_threshold(self, fail_max, num_failures):
        """Property: Circuit should open exactly when failures reach fail_max"""
        breaker = CircuitBreaker(name="test", fail_max=fail_max)

        for i in range(num_failures):
            breaker.record_failure(Exception(f"Failure {i}"))

        if num_failures >= fail_max:
            assert breaker.state == CircuitBreakerState.OPEN
        else:
            assert breaker.state == CircuitBreakerState.CLOSED

    @given(
        success_threshold=st.integers(min_value=1, max_value=10),
        num_successes=st.integers(min_value=0, max_value=15)
    )
    @settings(max_examples=50)
    def test_half_open_closes_at_threshold(self, success_threshold, num_successes):
        """Property: HALF_OPEN circuit closes after success_threshold successes"""
        breaker = CircuitBreaker(
            name="test",
            fail_max=3,
            success_threshold=success_threshold
        )

        # Set to HALF_OPEN
        breaker.state = CircuitBreakerState.HALF_OPEN

        for _ in range(num_successes):
            if breaker.state == CircuitBreakerState.HALF_OPEN:
                breaker.record_success()

        if num_successes >= success_threshold:
            assert breaker.state == CircuitBreakerState.CLOSED
        else:
            assert breaker.state == CircuitBreakerState.HALF_OPEN


# ============================================================================
# State Machine Testing (Advanced)
# ============================================================================

class CircuitBreakerStateMachine(RuleBasedStateMachine):
    """
    Stateful property-based testing for circuit breaker state transitions

    This tests that the circuit breaker behaves correctly across
    all possible state transitions.
    """

    def __init__(self):
        super().__init__()
        self.breaker = CircuitBreaker(
            name="state_machine_test",
            fail_max=5,
            reset_timeout=0,  # Immediate reset for testing
            success_threshold=3
        )

    @rule()
    def record_success(self):
        """Record a successful operation"""
        self.breaker.record_success()

    @rule()
    def record_failure(self):
        """Record a failed operation"""
        self.breaker.record_failure(Exception("Test failure"))

    @rule()
    def check_can_execute(self):
        """Check if execution is allowed"""
        self.breaker.can_execute()

    @invariant()
    def valid_state(self):
        """Invariant: Circuit breaker must always be in a valid state"""
        assert self.breaker.state in [
            CircuitBreakerState.CLOSED,
            CircuitBreakerState.OPEN,
            CircuitBreakerState.HALF_OPEN
        ]

    @invariant()
    def failure_count_valid(self):
        """Invariant: Failure count should never be negative"""
        assert self.breaker.failures >= 0

    @invariant()
    def success_count_valid(self):
        """Invariant: Success count should never be negative"""
        assert self.breaker.successes >= 0


# Run state machine test
TestCircuitBreakerStateMachine = CircuitBreakerStateMachine.TestCase


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.benchmark
class TestCircuitBreakerPerformance:
    """Performance tests for circuit breaker operations"""

    def test_state_check_performance(self, benchmark):
        """Benchmark circuit breaker state checking"""
        breaker = CircuitBreaker(name="bench", fail_max=5)

        result = benchmark(breaker.can_execute)
        assert result is True

    def test_failure_recording_performance(self, benchmark):
        """Benchmark failure recording"""
        breaker = CircuitBreaker(name="bench", fail_max=1000)

        result = benchmark(breaker.record_failure, Exception("Test"))
        assert result is None

    def test_success_recording_performance(self, benchmark):
        """Benchmark success recording"""
        breaker = CircuitBreaker(name="bench")

        result = benchmark(breaker.record_success)
        assert result is None


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.integration
class TestEnhancedConnectionIntegration:
    """Integration tests for enhanced connection manager"""

    @pytest.mark.asyncio
    @patch('aiohttp.ClientSession')
    async def test_full_circuit_breaker_flow(self, mock_session_class):
        """Test complete circuit breaker flow: CLOSED → OPEN → HALF_OPEN → CLOSED"""
        manager = EnhancedHAConnectionManager()
        manager.connections = [
            HAConnectionConfig(
                name="Test",
                url="ws://test:8123/api/websocket",
                token="token",
                connection_type=ConnectionType.PRIMARY_HA,
                priority=1,
                circuit_breaker_config={
                    'fail_max': 3,
                    'reset_timeout': 1,
                    'success_threshold': 2
                }
            )
        ]
        manager._create_circuit_breaker(manager.connections[0])

        breaker = manager.circuit_breakers["Test"]

        # 1. CLOSED state - should allow requests
        assert breaker.state == CircuitBreakerState.CLOSED
        assert breaker.can_execute() is True

        # 2. Trigger failures to OPEN circuit
        mock_session_class.side_effect = ConnectionError("Failed")

        for _ in range(3):
            await manager.get_connection_with_circuit_breaker()

        assert breaker.state == CircuitBreakerState.OPEN
        assert breaker.can_execute() is False

        # 3. Wait for reset timeout (simulate time passing)
        breaker.last_failure_time = datetime.now() - timedelta(seconds=2)

        # 4. Transition to HALF_OPEN
        assert breaker.can_execute() is True
        assert breaker.state == CircuitBreakerState.HALF_OPEN

        # 5. Record successes to close circuit
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__.return_value = mock_response
        mock_response.__aexit__.return_value = AsyncMock()

        mock_session = AsyncMock()
        mock_session.get.return_value = mock_response
        mock_session.__aenter__.return_value = mock_session
        mock_session.__aexit__.return_value = AsyncMock()

        mock_session_class.return_value = mock_session
        mock_session_class.side_effect = None

        # Need 2 successes to close
        await manager.get_connection_with_circuit_breaker()
        await manager.get_connection_with_circuit_breaker()

        assert breaker.state == CircuitBreakerState.CLOSED
