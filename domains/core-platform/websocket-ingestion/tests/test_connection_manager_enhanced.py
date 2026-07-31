"""
Tests for Enhanced Connection Manager with Error Handling
"""


import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.connection_manager import ConnectionManager
from src.error_handler import ErrorCategory
from src.state_machine import ConnectionState


def _enter_reconnecting(manager: ConnectionManager) -> None:
    """Drive the state machine into RECONNECTING.

    is_running is a read-only property derived from the state machine, so
    tests that need a "running" manager must transition through the valid
    path rather than assigning the property.
    """
    manager.state_machine.transition(ConnectionState.CONNECTING)
    manager.state_machine.transition(ConnectionState.AUTHENTICATING)
    manager.state_machine.transition(ConnectionState.CONNECTED)
    manager.state_machine.transition(ConnectionState.RECONNECTING)


def _fail_client_connect(manager: ConnectionManager, error: Exception) -> None:
    """Make the underlying client raise so the real _connect handles it."""
    manager.client = MagicMock()
    manager.client.connect = AsyncMock(side_effect=error)


class TestConnectionManagerEnhanced:
    """Test cases for enhanced ConnectionManager class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.connection_manager = ConnectionManager("ws://test-ha:8123/api/websocket", "test-token")

    def test_initialization(self):
        """Test connection manager initialization with error handler"""
        assert self.connection_manager.error_handler is not None
        assert self.connection_manager.jitter_range == 0.1
        assert self.connection_manager.current_retry_count == 0
        assert self.connection_manager.base_delay == 1
        assert self.connection_manager.backoff_multiplier == 2

        # Retry defaults come from the environment, so build a manager with
        # those vars cleared to assert the real defaults: -1 = infinite
        # retries, 300s max delay.
        with patch.dict(os.environ, {}, clear=True):
            defaults = ConnectionManager("ws://test-ha:8123/api/websocket", "test-token")
        assert defaults.max_retries == -1
        assert defaults.max_delay == 300

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter"""
        # Test multiple times to ensure jitter is applied
        delays = []
        for _ in range(10):
            delay = self.connection_manager._calculate_delay()
            delays.append(delay)

        # All delays should be positive
        assert all(d > 0 for d in delays)

        # With retry count 1, base delay should be around 1 second
        self.connection_manager.current_retry_count = 1
        delay = self.connection_manager._calculate_delay()
        assert 0.9 <= delay <= 1.1  # Should be around 1 second with jitter

    def test_calculate_delay_exponential_backoff(self):
        """Test exponential backoff calculation"""
        # Test increasing delays with retry count
        delays = []
        for retry_count in range(1, 6):
            self.connection_manager.current_retry_count = retry_count
            delay = self.connection_manager._calculate_delay()
            delays.append(delay)

        # Delays should generally increase (allowing for jitter)
        # First delay should be around 1 second
        assert 0.9 <= delays[0] <= 1.1

        # Second delay should be around 2 seconds
        assert 1.8 <= delays[1] <= 2.2

        # Third delay should be around 4 seconds
        assert 3.6 <= delays[2] <= 4.4

    def test_calculate_delay_max_delay(self):
        """Backoff is capped at max_delay before jitter is applied.

        max_delay bounds the exponential term, then ±jitter_range is added, so
        the returned delay sits in [max_delay*(1-j), max_delay*(1+j)]. random()
        is pinned to both extremes rather than sampled: the previous version
        asserted `delay <= max_delay`, which the +10% jitter violated on
        roughly half of all runs.
        """
        self.connection_manager.current_retry_count = 20
        max_delay = self.connection_manager.max_delay
        jitter = self.connection_manager.jitter_range

        # random() == 1.0 -> maximum positive jitter
        with patch("src.connection_manager.random.random", return_value=1.0):
            assert self.connection_manager._calculate_delay() == pytest.approx(
                max_delay * (1 + jitter)
            )

        # random() == 0.0 -> maximum negative jitter
        with patch("src.connection_manager.random.random", return_value=0.0):
            assert self.connection_manager._calculate_delay() == pytest.approx(
                max_delay * (1 - jitter)
            )

        # random() == 0.5 -> no jitter, exactly the cap
        with patch("src.connection_manager.random.random", return_value=0.5):
            assert self.connection_manager._calculate_delay() == pytest.approx(max_delay)

    def test_calculate_delay_minimum_delay(self):
        """Test that delay has a minimum value"""
        # Set retry count to 0
        self.connection_manager.current_retry_count = 0

        delay = self.connection_manager._calculate_delay()

        # Should have minimum delay
        assert delay >= 0.1

    def test_reset_retry_count(self):
        """Test resetting retry count"""
        self.connection_manager.current_retry_count = 5
        self.connection_manager._reset_retry_count()

        assert self.connection_manager.current_retry_count == 0

    def test_increment_retry_count(self):
        """Test incrementing retry count"""
        initial_count = self.connection_manager.current_retry_count
        self.connection_manager._increment_retry_count()

        assert self.connection_manager.current_retry_count == initial_count + 1

    def test_configure_retry_parameters(self):
        """Test configuring retry parameters"""
        self.connection_manager.configure_retry_parameters(
            max_retries=5,
            base_delay=2.0,
            max_delay=30.0,
            backoff_multiplier=1.5,
            jitter_range=0.2
        )

        assert self.connection_manager.max_retries == 5
        assert self.connection_manager.base_delay == 2.0
        assert self.connection_manager.max_delay == 30.0
        assert self.connection_manager.backoff_multiplier == 1.5
        assert self.connection_manager.jitter_range == 0.2

    def test_configure_retry_parameters_partial(self):
        """Test configuring only some retry parameters"""
        original_max_retries = self.connection_manager.max_retries
        original_base_delay = self.connection_manager.base_delay

        self.connection_manager.configure_retry_parameters(max_retries=15)

        assert self.connection_manager.max_retries == 15
        assert self.connection_manager.base_delay == original_base_delay

    def test_configure_retry_parameters_jitter_clamping(self):
        """Test that jitter range is clamped between 0 and 1"""
        # Test negative jitter
        self.connection_manager.configure_retry_parameters(jitter_range=-0.5)
        assert self.connection_manager.jitter_range == 0.0

        # Test jitter > 1
        self.connection_manager.configure_retry_parameters(jitter_range=1.5)
        assert self.connection_manager.jitter_range == 1.0

        # Test valid jitter
        self.connection_manager.configure_retry_parameters(jitter_range=0.3)
        assert self.connection_manager.jitter_range == 0.3

    @pytest.mark.asyncio
    async def test_get_status_includes_error_statistics(self):
        """Test that status includes error statistics"""
        # Log an error
        self.connection_manager.error_handler.log_error(ConnectionError("Test error"))

        status = await self.connection_manager.get_status()

        assert "error_statistics" in status
        assert "retry_config" in status
        assert status["retry_config"]["current_retry_count"] == 0
        assert status["retry_config"]["max_retries"] == self.connection_manager.max_retries
        assert status["retry_config"]["base_delay"] == 1
        assert status["retry_config"]["max_delay"] == self.connection_manager.max_delay
        assert status["retry_config"]["backoff_multiplier"] == 2
        assert status["retry_config"]["jitter_range"] == 0.1

    @pytest.mark.asyncio
    async def test_reconnect_loop_with_enhanced_retry(self):
        """Test reconnection loop with enhanced retry logic"""
        # Mock the connection to fail first few times, then succeed
        connection_attempts = []

        async def mock_connect():
            connection_attempts.append(len(connection_attempts) + 1)
            if len(connection_attempts) < 3:
                return False
            return True

        self.connection_manager._connect = mock_connect
        # is_running is derived from the state machine, so drive the state
        # rather than assigning the read-only property.
        _enter_reconnecting(self.connection_manager)
        self.connection_manager.max_retries = 5
        self.connection_manager.base_delay = 0
        self.connection_manager.jitter_range = 0

        await self.connection_manager._reconnect_loop()

        # Check that it succeeded
        assert self.connection_manager.current_retry_count == 0  # Should be reset on success
        assert len(connection_attempts) == 3

    @pytest.mark.asyncio
    async def test_reconnect_loop_max_retries_reached(self):
        """Test reconnection loop when max retries are reached"""
        # Mock the connection to always fail
        async def mock_connect():
            return False

        self.connection_manager._connect = mock_connect
        _enter_reconnecting(self.connection_manager)
        self.connection_manager.max_retries = 2
        self.connection_manager.base_delay = 0
        self.connection_manager.jitter_range = 0

        # Start reconnection loop
        await self.connection_manager._reconnect_loop()

        # Check that max retries were reached
        assert self.connection_manager.current_retry_count >= self.connection_manager.max_retries
        assert not self.connection_manager.is_running

    @pytest.mark.asyncio
    async def test_error_handling_in_connection(self):
        """A client failure is categorised and recorded by the real _connect.

        The previous version replaced _connect with a raising stub and then
        called that stub, so the real error handling never ran and the test
        could not fail. Fail the client instead and exercise _connect itself.
        """
        _fail_client_connect(self.connection_manager, ConnectionError("Connection failed"))

        result = await self.connection_manager._connect()

        assert result is False
        assert self.connection_manager.error_handler.error_counts[ErrorCategory.NETWORK] > 0
        assert self.connection_manager.last_error == "Connection failed"
        assert self.connection_manager.failed_connections == 1

    @pytest.mark.asyncio
    async def test_error_handling_in_reconnection(self):
        """A timeout during reconnection is categorised and recorded."""
        _fail_client_connect(self.connection_manager, TimeoutError("Connection timeout"))
        _enter_reconnecting(self.connection_manager)
        self.connection_manager.max_retries = 1
        self.connection_manager.base_delay = 0
        self.connection_manager.jitter_range = 0

        await self.connection_manager._reconnect_loop()

        assert self.connection_manager.error_handler.error_counts[ErrorCategory.TIMEOUT] > 0
        assert self.connection_manager.last_error == "Connection timeout"

    @pytest.mark.asyncio
    async def test_error_context_in_logging(self):
        """Connection errors carry base_url and retry context."""
        _fail_client_connect(self.connection_manager, ConnectionError("Connection failed"))
        self.connection_manager.connection_attempts = 5
        self.connection_manager.current_retry_count = 3

        await self.connection_manager._connect()

        # Check that context was included
        recent_errors = self.connection_manager.error_handler.get_recent_errors(1)
        assert len(recent_errors) == 1

        error_context = recent_errors[0]["context"]
        assert error_context["base_url"] == "ws://test-ha:8123/api/websocket"
        assert error_context["retry_count"] == 3
        # NOTE: _connect increments connection_attempts to 6, then reports
        # `connection_attempts + 1` in the error context, so a 6th attempt is
        # logged as 7. Pinned as-is; the off-by-one is worth a separate fix.
        assert error_context["connection_attempt"] == 7


class TestConnectionManagerOnConnect:
    """Cover ConnectionManager._on_connect, which owns subscription + discovery.

    These assertions previously lived in test_main_service.py against the
    service-level callback. That callback is now report-only, so the behaviour
    is verified here, where it actually runs.
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.connection_manager = ConnectionManager("ws://test-ha:8123/api/websocket", "test-token")

    @pytest.mark.asyncio
    async def test_on_connect_subscribes_to_events(self):
        """Connecting must subscribe to HA events."""
        self.connection_manager._subscribe_to_events = AsyncMock()
        self.connection_manager._run_initial_discovery = AsyncMock()

        await self.connection_manager._on_connect()

        self.connection_manager._subscribe_to_events.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_connect_schedules_discovery(self):
        """Discovery is deferred to a task so the listen loop starts first."""
        self.connection_manager._subscribe_to_events = AsyncMock()
        self.connection_manager._run_initial_discovery = AsyncMock()

        with patch("src.connection_manager.asyncio.create_task") as mock_create_task:
            await self.connection_manager._on_connect()

        mock_create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_connect_invokes_external_callback(self):
        """The registered external on_connect callback is awaited."""
        self.connection_manager._subscribe_to_events = AsyncMock()
        self.connection_manager._run_initial_discovery = AsyncMock()
        external = AsyncMock()
        self.connection_manager.on_connect = external

        with patch("src.connection_manager.asyncio.create_task"):
            await self.connection_manager._on_connect()

        external.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_on_connect_without_external_callback(self):
        """No registered callback is not an error."""
        self.connection_manager._subscribe_to_events = AsyncMock()
        self.connection_manager._run_initial_discovery = AsyncMock()
        self.connection_manager.on_connect = None

        with patch("src.connection_manager.asyncio.create_task"):
            await self.connection_manager._on_connect()

    @pytest.mark.asyncio
    async def test_on_connect_propagates_subscription_failure(self):
        """A subscription failure is not swallowed.

        Pins current behaviour: _on_connect has no guard around
        _subscribe_to_events, so the caller sees the failure and can retry the
        connection rather than proceeding with a silently unsubscribed socket.
        """
        self.connection_manager._subscribe_to_events = AsyncMock(
            side_effect=ConnectionError("subscribe failed")
        )
        self.connection_manager._run_initial_discovery = AsyncMock()

        with pytest.raises(ConnectionError):
            await self.connection_manager._on_connect()
