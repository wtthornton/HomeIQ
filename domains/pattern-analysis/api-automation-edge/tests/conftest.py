"""
Pytest configuration and fixtures
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Fix import path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clients.ha_rest_client import HARestClient
from src.clients.ha_websocket_client import HAWebSocketClient
from src.registry.spec_registry import SpecRegistry


@pytest.fixture
def mock_rest_client():
    """Mock REST client"""
    client = MagicMock(spec=HARestClient)
    client.get_states = AsyncMock(return_value=[])
    client.get_state = AsyncMock(return_value={"state": "on"})
    client.call_service = AsyncMock(return_value={})
    client.get_services = AsyncMock(return_value={})
    client.get_config = AsyncMock(return_value={"version": "2025.1.0"})
    return client


@pytest.fixture
def mock_websocket_client():
    """Mock WebSocket client"""
    client = MagicMock(spec=HAWebSocketClient)
    client.connected = True
    client.authenticated = True
    client.subscribe_events = AsyncMock(return_value=1)
    client.disconnect = AsyncMock()
    return client


@pytest.fixture
def spec_registry(tmp_path):
    """Spec registry with temporary database"""
    db_path = tmp_path / "test.db"
    return SpecRegistry(f"sqlite:///{db_path}")
