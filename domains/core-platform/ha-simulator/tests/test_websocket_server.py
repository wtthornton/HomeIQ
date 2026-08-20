"""
Tests for HA Simulator WebSocket Server
"""

import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.authentication import AuthenticationManager
from src.subscription_manager import SubscriptionManager
from src.websocket_server import HASimulatorWebSocketServer


class TestHASimulatorWebSocketServer:
    """Test cases for WebSocket server"""

    @pytest.fixture
    def config(self):
        return {
            "simulator": {"name": "Test Simulator", "version": "2025.10.1", "port": 8123},
            "authentication": {"enabled": True, "token": "test_token"},
        }

    @pytest.fixture
    def server(self, config):
        return HASimulatorWebSocketServer(config)

    def test_server_initialization(self, server, config):
        """Test server initialization"""
        assert server.config == config
        assert len(server.clients) == 0
        assert isinstance(server.auth_manager, AuthenticationManager)
        assert isinstance(server.subscription_manager, SubscriptionManager)

    @pytest.mark.asyncio
    async def test_websocket_handler_connection(self, server):
        """Test WebSocket connection handling"""
        # The handler constructs its own WebSocketResponse, so inject the mock
        # by patching the class. Iterating no messages models a client that
        # connects and immediately disconnects.
        ws = AsyncMock()
        with patch("src.websocket_server.WebSocketResponse", return_value=ws):
            await server.websocket_handler(Mock())

        ws.prepare.assert_awaited_once()
        auth_required = json.loads(ws.send_str.await_args_list[0].args[0])
        assert auth_required["type"] == "auth_required"
        assert len(server.clients) == 0  # Removed after disconnect

    @pytest.mark.asyncio
    async def test_handle_auth_message(self, server):
        """Test authentication message handling"""
        ws = AsyncMock()
        ws.send_str = AsyncMock()

        # Test auth message
        auth_message = {"type": "auth", "access_token": "test_token"}

        await server.handle_message(ws, json.dumps(auth_message))

        # Verify auth was processed
        assert server.auth_manager.is_authenticated(ws)

    @pytest.mark.asyncio
    async def test_handle_subscribe_events(self, server):
        """Test event subscription handling"""
        ws = AsyncMock()
        ws.send_str = AsyncMock()

        # First authenticate
        await server.auth_manager.handle_auth(ws, {"type": "auth", "access_token": "test_token"})

        # Then subscribe
        subscribe_message = {"id": 1, "type": "subscribe_events"}

        await server.handle_message(ws, json.dumps(subscribe_message))

        # Verify subscription was processed
        assert server.subscription_manager.has_subscriptions(ws)

    @pytest.mark.asyncio
    async def test_broadcast_event(self, server):
        """Test event broadcasting"""
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        ws1.send_str = AsyncMock()
        ws2.send_str = AsyncMock()

        # Add clients
        server.clients.add(ws1)
        server.clients.add(ws2)

        # Authenticate and subscribe clients
        await server.auth_manager.handle_auth(ws1, {"type": "auth", "access_token": "test_token"})
        await server.auth_manager.handle_auth(ws2, {"type": "auth", "access_token": "test_token"})

        await server.subscription_manager.handle_subscribe_events(
            ws1, {"id": 1, "type": "subscribe_events"}
        )
        await server.subscription_manager.handle_subscribe_events(
            ws2, {"id": 1, "type": "subscribe_events"}
        )

        # Auth and subscribe confirmations above also went through send_str;
        # only the broadcast itself is under test.
        ws1.send_str.reset_mock()
        ws2.send_str.reset_mock()

        # Broadcast event
        test_event = {
            "type": "event",
            "event": {"event_type": "state_changed", "data": {"entity_id": "test.entity"}},
        }

        await server.broadcast_event(test_event)

        # Verify both clients received the event
        ws1.send_str.assert_called_once_with(json.dumps(test_event))
        ws2.send_str.assert_called_once_with(json.dumps(test_event))

    @pytest.mark.asyncio
    async def test_health_check(self, server):
        """Test health check endpoint"""
        # Add some clients
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        server.clients.add(ws1)
        server.clients.add(ws2)

        # Authenticate one client
        await server.auth_manager.handle_auth(ws1, {"type": "auth", "access_token": "test_token"})

        # Subscribe one client
        await server.subscription_manager.handle_subscribe_events(
            ws1, {"id": 1, "type": "subscribe_events"}
        )

        # Mock request
        request = Mock()

        # Get health response
        response = await server.health_check(request)

        # Verify response
        assert response.status == 200
        # Note: In a real test, we'd need to check the JSON content
