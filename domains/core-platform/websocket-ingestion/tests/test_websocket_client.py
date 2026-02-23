"""
Tests for WebSocket Client
"""

from unittest.mock import AsyncMock, patch

import pytest
from src.websocket_client import HomeAssistantWebSocketClient


class TestHomeAssistantWebSocketClient:
    """Test cases for HomeAssistantWebSocketClient class"""

    def setup_method(self):
        """Set up test fixtures"""
        self.base_url = "http://homeassistant.local:8123"
        self.token = "abcdefghijklmnopqrstuvwxyz123456"
        self.client = HomeAssistantWebSocketClient(self.base_url, self.token)

    def test_initialization(self):
        """Test client initialization"""
        assert self.client.base_url == self.base_url
        assert self.client.token == self.token
        assert self.client.is_connected is False
        assert self.client.is_authenticated is False
        assert self.client.connection_attempts == 0
        assert self.client.max_retries == 5

    def test_get_connection_status(self):
        """Test getting connection status"""
        status = self.client.get_connection_status()

        assert "is_connected" in status
        assert "is_authenticated" in status
        assert "connection_attempts" in status
        assert "max_retries" in status
        assert "base_url" in status
        assert "token_info" in status
        assert "timestamp" in status

        assert status["is_connected"] is False
        assert status["is_authenticated"] is False
        assert status["connection_attempts"] == 0
        assert status["base_url"] == self.base_url

    @pytest.mark.asyncio
    async def test_connect_with_invalid_token(self):
        """Test connection with invalid token"""
        client = HomeAssistantWebSocketClient(self.base_url, "invalid")

        with patch('src.websocket_client.ClientSession') as mock_session:
            result = await client.connect()

            assert result is False
            assert client.is_connected is False
            assert client.is_authenticated is False

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful connection"""
        mock_websocket = AsyncMock()
        mock_session = AsyncMock()
        mock_session.ws_connect.return_value = mock_websocket

        # Mock authentication flow
        mock_websocket.receive.side_effect = [
            AsyncMock(type=1, data='{"type": "auth_required"}'),  # auth_required
            AsyncMock(type=1, data='{"type": "auth_ok"}')  # auth_ok
        ]

        with patch('src.websocket_client.ClientSession', return_value=mock_session):
            result = await self.client.connect()

            assert result is True
            assert self.client.is_connected is True
            assert self.client.is_authenticated is True

    @pytest.mark.asyncio
    async def test_connect_auth_failure(self):
        """Test connection with authentication failure"""
        mock_websocket = AsyncMock()
        mock_session = AsyncMock()
        mock_session.ws_connect.return_value = mock_websocket

        # Mock authentication flow with failure
        mock_websocket.receive.side_effect = [
            AsyncMock(type=1, data='{"type": "auth_required"}'),  # auth_required
            AsyncMock(type=1, data='{"type": "auth_invalid"}')  # auth_invalid
        ]

        with patch('src.websocket_client.ClientSession', return_value=mock_session):
            result = await self.client.connect()

            assert result is False
            assert self.client.is_connected is False
            assert self.client.is_authenticated is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """Test disconnection"""
        # Set up connected state
        self.client.is_connected = True
        self.client.is_authenticated = True
        self.client.websocket = AsyncMock()
        self.client.session = AsyncMock()

        await self.client.disconnect()

        assert self.client.is_connected is False
        assert self.client.is_authenticated is False
        assert self.client.websocket is None
        assert self.client.session is None

    @pytest.mark.asyncio
    async def test_send_message_not_connected(self):
        """Test sending message when not connected"""
        result = await self.client.send_message({"type": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_not_authenticated(self):
        """Test sending message when not authenticated"""
        self.client.is_connected = True
        self.client.is_authenticated = False

        result = await self.client.send_message({"type": "test"})

        assert result is False

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending"""
        self.client.is_connected = True
        self.client.is_authenticated = True
        self.client.websocket = AsyncMock()

        message = {"type": "test", "data": "hello"}
        result = await self.client.send_message(message)

        assert result is True
        self.client.websocket.send_str.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_success(self):
        """Test successful reconnection"""
        self.client.connection_attempts = 1

        with patch.object(self.client, 'connect', return_value=True) as mock_connect:
            with patch.object(self.client, 'disconnect') as mock_disconnect:
                result = await self.client.reconnect()

                assert result is True
                mock_disconnect.assert_called_once()
                mock_connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_reconnect_max_attempts(self):
        """Test reconnection with max attempts reached"""
        self.client.connection_attempts = 10  # Exceeds max_retries

        result = await self.client.reconnect()

        assert result is False

    @pytest.mark.asyncio
    async def test_listen_not_connected(self):
        """Test listening when not connected"""
        await self.client.listen()
        # Should return without error

    @pytest.mark.asyncio
    async def test_listen_not_authenticated(self):
        """Test listening when not authenticated"""
        self.client.is_connected = True
        self.client.is_authenticated = False

        await self.client.listen()
        # Should return without error

    @pytest.mark.asyncio
    async def test_listen_success(self):
        """Test successful listening"""
        self.client.is_connected = True
        self.client.is_authenticated = True

        mock_websocket = AsyncMock()
        mock_websocket.__aiter__.return_value = [
            AsyncMock(type=1, data='{"type": "test", "data": "hello"}'),
            AsyncMock(type=8)  # CLOSE message
        ]
        self.client.websocket = mock_websocket

        # Mock message handler
        self.client.on_message = AsyncMock()

        await self.client.listen()

        # Should have called the message handler
        self.client.on_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_json_decode_error(self):
        """Test listening with JSON decode error"""
        self.client.is_connected = True
        self.client.is_authenticated = True

        mock_websocket = AsyncMock()
        mock_websocket.__aiter__.return_value = [
            AsyncMock(type=1, data='invalid json'),
            AsyncMock(type=8)  # CLOSE message
        ]
        self.client.websocket = mock_websocket

        await self.client.listen()
        # Should handle error gracefully

    @pytest.mark.asyncio
    async def test_listen_websocket_error(self):
        """Test listening with WebSocket error"""
        self.client.is_connected = True
        self.client.is_authenticated = True

        mock_websocket = AsyncMock()
        # Use WSMsgType.ERROR which is 8
        from aiohttp import WSMsgType
        mock_websocket.__aiter__.return_value = [
            AsyncMock(type=WSMsgType.ERROR, data='error'),  # ERROR message
        ]
        self.client.websocket = mock_websocket

        # Mock error handler
        self.client.on_error = AsyncMock()

        await self.client.listen()

        # Should have called the error handler
        self.client.on_error.assert_called_once()
