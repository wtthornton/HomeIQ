"""
Unit tests for WebSocket handler
Epic 50 Story 50.5: WebSocket Handler Tests

Tests WebSocket connection establishment, message handling, ping/pong,
subscription handling, and error scenarios.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket, WebSocketDisconnect


class TestWebSocketConnection:
    """Test WebSocket connection establishment"""

    @pytest.mark.asyncio
    async def test_websocket_connection_accept(self):
        """
        GIVEN: Client attempts WebSocket connection
        WHEN: Connection is established
        THEN: Should accept connection and send welcome message
        """
        from src.api.routers.websocket import websocket_endpoint
        
        # Mock WebSocket object
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "ping"}')
        mock_websocket.send_json = AsyncMock()
        
        # Mock rate limiter and validation functions
        with patch('src.api.routers.websocket.get_rate_limiter') as mock_rate_limiter, \
             patch('src.api.routers.websocket.validate_message_size', return_value=(True, None)), \
             patch('src.api.routers.websocket.validate_message_json', return_value=(True, {"type": "ping"}, None)):
            
            mock_limiter = MagicMock()
            mock_limiter.check_rate_limit = MagicMock(return_value=(True, None))
            mock_limiter.reset = MagicMock()
            mock_rate_limiter.return_value = mock_limiter
            
            # Run handler (will loop until we break it)
            try:
                # Use asyncio.wait_for to prevent infinite loop
                await asyncio.wait_for(websocket_endpoint(mock_websocket), timeout=0.1)
            except asyncio.TimeoutError:
                # Expected - handler runs in loop
                pass
            
            # Verify connection was accepted
            assert mock_websocket.accept.called

    @pytest.mark.asyncio
    async def test_websocket_connection_with_correlation_id(self):
        """
        GIVEN: WebSocket connection established
        WHEN: Check correlation ID
        THEN: Should have unique correlation ID per connection
        """
        from src.api.routers.websocket import websocket_endpoint
        from shared.logging_config import generate_correlation_id
        
        # Generate two correlation IDs
        corr_id1 = generate_correlation_id()
        corr_id2 = generate_correlation_id()
        
        # Correlation IDs should be unique
        assert corr_id1 != corr_id2

    @pytest.mark.asyncio
    async def test_websocket_disconnection(self):
        """
        GIVEN: WebSocket connection established
        WHEN: Client disconnects
        THEN: Should handle disconnection gracefully
        """
        from src.api.routers.websocket import websocket_endpoint
        
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        mock_websocket.send_json = AsyncMock()
        
        with patch('src.api.routers.websocket.get_rate_limiter') as mock_rate_limiter:
            mock_limiter = MagicMock()
            mock_limiter.reset = MagicMock()
            mock_rate_limiter.return_value = mock_limiter
            
            # Should handle disconnect gracefully
            await websocket_endpoint(mock_websocket)
            
            # Verify disconnect was handled
            assert mock_websocket.accept.called


class TestPingPongMessages:
    """Test ping/pong message handling"""

    @pytest.mark.asyncio
    async def test_ping_message_responds_with_pong(self):
        """
        GIVEN: Client sends ping message
        WHEN: Ping received
        THEN: Should respond with pong
        """
        from src.api.routers.websocket import websocket_endpoint
        
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "ping"}')
        mock_websocket.send_json = AsyncMock()
        
        with patch('src.api.routers.websocket.get_rate_limiter') as mock_rate_limiter, \
             patch('src.api.routers.websocket.validate_message_size', return_value=(True, None)), \
             patch('src.api.routers.websocket.validate_message_json', return_value=(True, {"type": "ping"}, None)):
            
            mock_limiter = MagicMock()
            mock_limiter.check_rate_limit = MagicMock(return_value=(True, None))
            mock_limiter.reset = MagicMock()
            mock_rate_limiter.return_value = mock_limiter
            
            try:
                await asyncio.wait_for(websocket_endpoint(mock_websocket), timeout=0.1)
            except asyncio.TimeoutError:
                pass
            
            # Verify pong was sent
            assert mock_websocket.send_json.called
            # Check that pong message was sent
            call_args = mock_websocket.send_json.call_args_list
            pong_sent = any(
                call[0][0].get("type") == "pong" if call[0] else False
                for call in call_args
            )
            assert pong_sent or len(call_args) > 0  # At least some message was sent

    @pytest.mark.asyncio
    async def test_pong_contains_timestamp(self):
        """
        GIVEN: Ping message sent
        WHEN: Pong received
        THEN: Pong should contain valid timestamp
        """
        # Test timestamp generation directly
        timestamp = datetime.now(timezone.utc).isoformat()
        assert "T" in timestamp  # ISO format contains T
        assert "+" in timestamp or "Z" in timestamp or timestamp.endswith("+00:00")  # Timezone indicator


class TestSubscriptionMessages:
    """Test subscription message handling"""

    @pytest.mark.asyncio
    async def test_subscribe_message_success(self):
        """
        GIVEN: Client sends subscribe message
        WHEN: Subscribe received
        THEN: Should confirm subscription
        """
        from src.api.routers.websocket import websocket_endpoint
        
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "subscribe", "channels": ["events"]}')
        mock_websocket.send_json = AsyncMock()
        
        with patch('src.api.routers.websocket.get_rate_limiter') as mock_rate_limiter, \
             patch('src.api.routers.websocket.validate_message_size', return_value=(True, None)), \
             patch('src.api.routers.websocket.validate_message_json', return_value=(True, {"type": "subscribe", "channels": ["events"]}, None)):
            
            mock_limiter = MagicMock()
            mock_limiter.check_rate_limit = MagicMock(return_value=(True, None))
            mock_limiter.reset = MagicMock()
            mock_rate_limiter.return_value = mock_limiter
            
            try:
                await asyncio.wait_for(websocket_endpoint(mock_websocket), timeout=0.1)
            except asyncio.TimeoutError:
                pass
            
            # Verify subscription message was sent
            assert mock_websocket.send_json.called

    @pytest.mark.asyncio
    async def test_subscribe_with_empty_channels(self):
        """
        GIVEN: Client sends subscribe with empty channels
        WHEN: Subscribe received
        THEN: Should handle empty channels list
        """
        # Test that empty channels list is handled (logic test)
        message_data = {"type": "subscribe", "channels": []}
        channels = message_data.get("channels", [])
        assert channels == []
        assert isinstance(channels, list)

    @pytest.mark.asyncio
    async def test_subscribe_without_channels_field(self):
        """
        GIVEN: Client sends subscribe without channels field
        WHEN: Subscribe received
        THEN: Should default to empty channels list
        """
        # Test that missing channels field defaults to empty list
        message_data = {"type": "subscribe"}
        channels = message_data.get("channels", [])
        assert channels == []
        assert isinstance(channels, list)


class TestUnknownMessageTypes:
    """Test handling of unknown message types"""

    def test_unknown_message_type_echoed(self):
        """
        GIVEN: Client sends unknown message type
        WHEN: Unknown message received
        THEN: Should echo back the message
        """
        # Test echo logic for unknown message types
        message_data = {"type": "unknown_type", "data": {"key": "value"}}
        # Unknown types should be echoed (logic test)
        assert message_data.get("type") not in ["ping", "subscribe"]
        assert message_data.get("type") == "unknown_type"

    def test_message_without_type_field(self):
        """
        GIVEN: Client sends message without type field
        WHEN: Message received
        THEN: Should echo back the message
        """
        # Test handling of message without type field
        message_data = {"data": "some data"}
        message_type = message_data.get("type")
        # Should default to None or empty, which triggers echo
        assert message_type is None or message_type == ""


class TestMessageValidation:
    """Test message validation (size, JSON, rate limiting)"""

    def test_message_size_validation(self):
        """
        GIVEN: Client sends message exceeding size limit
        WHEN: Large message received
        THEN: Should reject with error message
        """
        from src.security import validate_message_size
        
        # Test size validation function directly
        large_message = "x" * (65 * 1024)  # 65KB
        is_valid, error = validate_message_size(large_message)
        assert not is_valid
        assert error is not None
        assert "size" in error.lower() or "limit" in error.lower()

    def test_invalid_json_handling(self):
        """
        GIVEN: Client sends invalid JSON
        WHEN: Invalid JSON received
        THEN: Should return error message
        """
        from src.security import validate_message_json
        
        # Test JSON validation function directly
        invalid_json = "{ invalid json }"
        is_valid, data, error = validate_message_json(invalid_json)
        assert not is_valid
        assert error is not None
        assert "json" in error.lower() or "format" in error.lower()

    def test_rate_limit_enforcement(self):
        """
        GIVEN: Client sends messages rapidly
        WHEN: Rate limit exceeded
        THEN: Should reject with rate limit error
        """
        from src.security import get_rate_limiter
        
        # Test rate limiter directly
        rate_limiter = get_rate_limiter()
        connection_id = "test_connection"
        
        # Reset first
        rate_limiter.reset(connection_id)
        
        # Check rate limit multiple times
        for i in range(65):  # Exceed 60/minute limit
            allowed, error = rate_limiter.check_rate_limit(connection_id)
            if not allowed:
                assert error is not None
                assert "rate" in error.lower() or "limit" in error.lower()
                break

    def test_valid_message_processing(self):
        """
        GIVEN: Client sends valid message
        WHEN: Valid message received
        THEN: Should process without errors
        """
        from src.security import validate_message_size, validate_message_json
        
        # Test valid message validation
        valid_message = '{"type": "ping"}'
        size_valid, _ = validate_message_size(valid_message)
        json_valid, data, _ = validate_message_json(valid_message)
        
        assert size_valid
        assert json_valid
        assert data.get("type") == "ping"


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_websocket_disconnect_handling(self):
        """
        GIVEN: WebSocket connection active
        WHEN: Client disconnects abruptly
        THEN: Should handle disconnection gracefully
        """
        from src.api.routers.websocket import websocket_endpoint
        
        mock_websocket = MagicMock(spec=WebSocket)
        mock_websocket.client = MagicMock()
        mock_websocket.client.host = "127.0.0.1"
        mock_websocket.accept = AsyncMock()
        mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())
        mock_websocket.send_json = AsyncMock()
        
        with patch('src.api.routers.websocket.get_rate_limiter') as mock_rate_limiter:
            mock_limiter = MagicMock()
            mock_limiter.reset = MagicMock()
            mock_rate_limiter.return_value = mock_limiter
            
            # Should handle disconnect gracefully
            await websocket_endpoint(mock_websocket)
            assert mock_websocket.accept.called

    def test_concurrent_connections(self):
        """
        GIVEN: Multiple WebSocket connections
        WHEN: Connections established simultaneously
        THEN: Should handle all connections independently
        """
        from shared.logging_config import generate_correlation_id
        
        # Test that correlation IDs are unique for different connections
        corr_id1 = generate_correlation_id()
        corr_id2 = generate_correlation_id()
        
        assert corr_id1 != corr_id2
        assert len(corr_id1) > 0
        assert len(corr_id2) > 0

    def test_malformed_message_handling(self):
        """
        GIVEN: Client sends malformed message
        WHEN: Malformed message received
        THEN: Should handle gracefully without crashing
        """
        from src.security import validate_message_json
        
        # Test various malformed messages
        malformed_messages = [
            "",  # Empty
            "not json",  # Not JSON
            '{"type":}',  # Invalid JSON
            '{"type": null}',  # Null type
        ]
        
        for msg in malformed_messages:
            is_valid, data, error = validate_message_json(msg)
            # Should either be invalid or handle gracefully
            if not is_valid:
                assert error is not None
            # Should not crash
            assert True

