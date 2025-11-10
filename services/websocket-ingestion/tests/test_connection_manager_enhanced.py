"""
Tests for Enhanced Connection Manager with Error Handling
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.connection_manager import ConnectionManager
from src.error_handler import ErrorCategory, ErrorSeverity


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
        assert self.connection_manager.max_retries == 10
        assert self.connection_manager.base_delay == 1
        assert self.connection_manager.max_delay == 60
        assert self.connection_manager.backoff_multiplier == 2
    
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
        """Test that delay doesn't exceed max delay"""
        # Set a high retry count
        self.connection_manager.current_retry_count = 20
        
        delay = self.connection_manager._calculate_delay()
        
        # Should not exceed max delay
        assert delay <= self.connection_manager.max_delay
    
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
    
    def test_get_status_includes_error_statistics(self):
        """Test that status includes error statistics"""
        # Log an error
        self.connection_manager.error_handler.log_error(ConnectionError("Test error"))
        
        status = self.connection_manager.get_status()
        
        assert "error_statistics" in status
        assert "retry_config" in status
        assert status["retry_config"]["current_retry_count"] == 0
        assert status["retry_config"]["max_retries"] == 10
        assert status["retry_config"]["base_delay"] == 1
        assert status["retry_config"]["max_delay"] == 60
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
        self.connection_manager.is_running = True
        self.connection_manager.max_retries = 5
        
        # Start reconnection loop
        task = asyncio.create_task(self.connection_manager._reconnect_loop())
        
        # Wait for completion
        await asyncio.sleep(0.1)  # Give it time to complete
        
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
        self.connection_manager.is_running = True
        self.connection_manager.max_retries = 2
        
        # Start reconnection loop
        await self.connection_manager._reconnect_loop()
        
        # Check that max retries were reached
        assert self.connection_manager.current_retry_count >= self.connection_manager.max_retries
        assert not self.connection_manager.is_running
    
    def test_error_handling_in_connection(self):
        """Test error handling during connection"""
        # Mock connection to raise an exception
        async def mock_connect():
            raise ConnectionError("Connection failed")
        
        self.connection_manager._connect = mock_connect
        
        # Run connection
        import asyncio
        asyncio.run(self.connection_manager._connect())
        
        # Check that error was logged
        assert self.connection_manager.error_handler.error_counts[ErrorCategory.NETWORK] > 0
        assert self.connection_manager.last_error is not None
    
    def test_error_handling_in_reconnection(self):
        """Test error handling during reconnection"""
        # Mock reconnection to raise an exception
        async def mock_connect():
            raise TimeoutError("Connection timeout")
        
        self.connection_manager._connect = mock_connect
        self.connection_manager.is_running = True
        self.connection_manager.max_retries = 1
        
        # Run reconnection loop
        import asyncio
        asyncio.run(self.connection_manager._reconnect_loop())
        
        # Check that error was logged
        assert self.connection_manager.error_handler.error_counts[ErrorCategory.TIMEOUT] > 0
        assert self.connection_manager.last_error is not None
    
    def test_error_context_in_logging(self):
        """Test that error context is properly logged"""
        # Mock connection to raise an exception
        async def mock_connect():
            raise ConnectionError("Connection failed")
        
        self.connection_manager._connect = mock_connect
        self.connection_manager.connection_attempts = 5
        self.connection_manager.current_retry_count = 3
        
        # Run connection
        import asyncio
        asyncio.run(self.connection_manager._connect())
        
        # Check that context was included
        recent_errors = self.connection_manager.error_handler.get_recent_errors(1)
        assert len(recent_errors) == 1
        
        error_context = recent_errors[0]["context"]
        assert error_context["base_url"] == "ws://test-ha:8123/api/websocket"
        assert error_context["connection_attempt"] == 6  # 5 + 1
        assert error_context["retry_count"] == 3
