"""
WebSocket Connection Flow Integration Tests
Epic 50 Story 50.3: Integration Test Suite

Tests for end-to-end WebSocket connection flow including authentication and
reconnection, driven through the real ConnectionManager lifecycle
(``start()`` / ``stop()``) with only the HA transport stubbed out.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from src.connection_manager import ConnectionManager
from src.state_machine import ConnectionState

# 32+ alphanumeric characters so TokenValidator accepts it
VALID_TOKEN = "a" * 40


@pytest.fixture
def mock_ha_client():
    """Stand-in for HomeAssistantWebSocketClient"""
    client = MagicMock()
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.listen = AsyncMock()
    client.send_message = AsyncMock(return_value=True)
    client.is_connected = True
    client.is_authenticated = True
    client.websocket = MagicMock()
    return client


@pytest.fixture
async def connection_manager(mock_ha_client, monkeypatch):
    """Connection manager wired to a stubbed transport"""
    manager = ConnectionManager(base_url="ws://test-ha:8123", token=VALID_TOKEN)

    # _setup_event_handlers() builds a real client; swap in the stub instead.
    def _install_stub():
        manager.client = mock_ha_client

    monkeypatch.setattr(manager, "_setup_event_handlers", _install_stub)
    # Keep the listen loop and discovery inert — this suite covers connection flow.
    monkeypatch.setattr(manager, "_listen_loop", AsyncMock())
    monkeypatch.setattr(manager, "_run_initial_discovery", AsyncMock())
    monkeypatch.setattr(manager, "discovery_service", MagicMock())

    yield manager

    await manager.stop()


@pytest.mark.asyncio
async def test_connection_establishment(connection_manager, mock_ha_client):
    """A successful connect reaches CONNECTED and records the attempt"""
    assert await connection_manager.start() is True

    assert mock_ha_client.connect.await_count == 1
    assert connection_manager.state_machine.get_state() == ConnectionState.CONNECTED
    assert connection_manager.successful_connections == 1
    assert connection_manager.connection_attempts == 1
    assert connection_manager.last_error is None


@pytest.mark.asyncio
async def test_start_is_idempotent_when_already_connected(connection_manager, mock_ha_client):
    """Starting twice does not open a second connection"""
    await connection_manager.start()
    assert await connection_manager.start() is True

    assert mock_ha_client.connect.await_count == 1


@pytest.mark.asyncio
async def test_event_subscription(connection_manager, mock_ha_client):
    """Connecting subscribes to state_changed events"""
    connection_manager.event_subscription = MagicMock()
    connection_manager.event_subscription.subscribe_to_events = AsyncMock(return_value=True)

    await connection_manager.start()
    await connection_manager._on_connect()

    connection_manager.event_subscription.subscribe_to_events.assert_awaited_once()
    _, event_types = connection_manager.event_subscription.subscribe_to_events.await_args[0]
    assert event_types == ["state_changed"]


@pytest.mark.asyncio
async def test_failing_on_connect_callback_does_not_break_connection(connection_manager):
    """An external on_connect callback that raises is contained"""
    connection_manager.event_subscription = MagicMock()
    connection_manager.event_subscription.subscribe_to_events = AsyncMock(return_value=True)
    connection_manager.on_connect = AsyncMock(side_effect=RuntimeError("callback boom"))

    await connection_manager.start()

    # Must not propagate — a bad consumer callback cannot tear down the socket
    await connection_manager._on_connect()

    connection_manager.on_connect.assert_awaited_once()
    assert connection_manager.state_machine.get_state() == ConnectionState.CONNECTED


@pytest.mark.asyncio
async def test_reconnection_logic(connection_manager, mock_ha_client, monkeypatch):
    """A failed initial connect schedules the reconnect loop"""
    mock_ha_client.connect = AsyncMock(return_value=False)
    reconnect = AsyncMock()
    monkeypatch.setattr(connection_manager, "_reconnect_loop", reconnect)

    assert await connection_manager.start() is True

    assert connection_manager.failed_connections == 1
    assert connection_manager.state_machine.get_state() == ConnectionState.FAILED
    assert connection_manager.reconnect_task is not None

    # start() only schedules the loop; let it run
    await asyncio.sleep(0)
    reconnect.assert_awaited()


@pytest.mark.asyncio
async def test_connection_state_transitions(connection_manager):
    """The state machine follows the documented connection path"""
    sm = connection_manager.state_machine

    assert sm.get_state() == ConnectionState.DISCONNECTED

    sm.transition(ConnectionState.CONNECTING)
    assert sm.get_state() == ConnectionState.CONNECTING

    sm.transition(ConnectionState.AUTHENTICATING)
    assert sm.get_state() == ConnectionState.AUTHENTICATING

    sm.transition(ConnectionState.CONNECTED)
    assert sm.get_state() == ConnectionState.CONNECTED


@pytest.mark.asyncio
async def test_connection_error_handling(connection_manager, mock_ha_client, monkeypatch):
    """A raising transport leaves the manager in FAILED with the error recorded"""
    mock_ha_client.connect = AsyncMock(side_effect=ConnectionError("Connection error"))
    monkeypatch.setattr(connection_manager, "_reconnect_loop", AsyncMock())

    assert await connection_manager.start() is True

    assert connection_manager.state_machine.get_state() == ConnectionState.FAILED
    assert connection_manager.last_error == "Connection error"
    assert connection_manager.failed_connections == 1


@pytest.mark.asyncio
async def test_stop_cancels_background_tasks(connection_manager, mock_ha_client):
    """stop() tears down every background task it owns"""
    await connection_manager.start()

    listen_task = connection_manager.listen_task
    await connection_manager.stop()

    assert connection_manager.state_machine.get_state() == ConnectionState.DISCONNECTED
    assert listen_task is None or listen_task.cancelled() or listen_task.done()
    mock_ha_client.disconnect.assert_awaited()
