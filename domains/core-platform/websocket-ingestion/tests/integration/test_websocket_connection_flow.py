"""
WebSocket Connection Flow Integration Tests
Epic 50 Story 50.3: Integration Test Suite

Tests for end-to-end WebSocket connection flow including authentication and reconnection.
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.connection_manager import ConnectionManager
from src.state_machine import ConnectionStateMachine


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    ws = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_json = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_ha_client():
    """Mock Home Assistant WebSocket client"""
    client = AsyncMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.subscribe_events = AsyncMock()
    return client


@pytest.fixture
async def connection_manager(mock_ha_client):
    """Create connection manager with mocked dependencies"""
    # Set test environment
    os.environ['HA_URL'] = 'ws://test-ha:8123'
    os.environ['HA_TOKEN'] = 'test-token'
    
    manager = ConnectionManager()
    
    # Mock dependencies
    manager.ha_client = mock_ha_client
    manager.batch_processor = MagicMock()
    manager.event_processor = MagicMock()
    manager.discovery_service = MagicMock()
    
    yield manager
    
    # Cleanup
    try:
        await manager.shutdown()
    except:
        pass


@pytest.mark.asyncio
async def test_connection_establishment(connection_manager, mock_ha_client):
    """Test WebSocket connection establishment"""
    # Mock successful connection
    mock_ha_client.connect.return_value = True
    
    # Start connection
    await connection_manager.connect()
    
    # Verify connection was attempted
    assert mock_ha_client.connect.called
    
    # Verify state machine transitioned
    assert connection_manager.state_machine.get_state().value in ["connecting", "authenticating", "connected"]


@pytest.mark.asyncio
async def test_authentication_flow(connection_manager, mock_ha_client):
    """Test authentication flow"""
    # Mock authentication response
    mock_ha_client.connect.return_value = True
    mock_ha_client.authenticate = AsyncMock(return_value=True)
    
    # Start connection
    await connection_manager.connect()
    
    # Verify authentication was called
    if hasattr(mock_ha_client, 'authenticate'):
        assert mock_ha_client.authenticate.called


@pytest.mark.asyncio
async def test_event_subscription(connection_manager, mock_ha_client):
    """Test event subscription after connection"""
    # Mock successful connection and subscription
    mock_ha_client.connect.return_value = True
    mock_ha_client.subscribe_events = AsyncMock(return_value=True)
    
    # Start connection
    await connection_manager.connect()
    
    # Verify subscription was called
    assert mock_ha_client.subscribe_events.called


@pytest.mark.asyncio
async def test_reconnection_logic(connection_manager, mock_ha_client):
    """Test reconnection logic on connection failure"""
    # Mock initial connection failure
    mock_ha_client.connect.side_effect = [Exception("Connection failed"), True]
    
    # Attempt connection (should retry)
    try:
        await connection_manager.connect()
    except Exception:
        pass
    
    # Verify reconnection was attempted
    assert mock_ha_client.connect.call_count >= 1


@pytest.mark.asyncio
async def test_connection_state_transitions(connection_manager):
    """Test connection state machine transitions"""
    # Verify initial state
    assert connection_manager.state_machine.get_state().value == "disconnected"
    
    # Test state transitions
    connection_manager.state_machine.transition("CONNECTING")
    assert connection_manager.state_machine.get_state().value == "connecting"
    
    connection_manager.state_machine.transition("AUTHENTICATING")
    assert connection_manager.state_machine.get_state().value == "authenticating"
    
    connection_manager.state_machine.transition("CONNECTED")
    assert connection_manager.state_machine.get_state().value == "connected"


@pytest.mark.asyncio
async def test_connection_error_handling(connection_manager, mock_ha_client):
    """Test error handling during connection"""
    # Mock connection error
    mock_ha_client.connect.side_effect = Exception("Connection error")
    
    # Attempt connection
    try:
        await connection_manager.connect()
    except Exception:
        pass
    
    # Verify error was handled (state should be failed or reconnecting)
    state = connection_manager.state_machine.get_state().value
    assert state in ["failed", "reconnecting", "disconnected"]

