"""Registry-access tests for device-recommender (TAP-5424).

These pin the behaviour the migration was for: the device registry is read over
the Home Assistant WebSocket API, never over `GET /api/config/device_registry/list`,
which does not exist and used to make this client report an empty device list.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

DEVICES = [
    {"id": "dev-1", "name": "Living Room Lamp", "manufacturer": "wled"},
    {"id": "dev-2", "name": "Thermostat", "manufacturer": "ecobee"},
]


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://ha.local:8123")
    monkeypatch.setenv("HA_TOKEN", "test-token")


def _make_client():
    from src.ha_client import HAClient

    return HAClient()


def _patched_ws(devices=None, side_effect=None):
    """Patch the shared facade so `.ws` is a mock WebSocket connection."""
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.close = AsyncMock()
    ws.list_devices = AsyncMock(return_value=devices or [], side_effect=side_effect)
    facade = MagicMock()
    facade.ws = ws
    return patch("src.ha_client.SharedHAClient", return_value=facade), ws


class TestReadsRegistryOverWebSocket:
    @pytest.mark.asyncio
    async def test_returns_devices_from_websocket_registry(self, configured):
        patcher, ws = _patched_ws(DEVICES)
        with patcher:
            client = _make_client()
            assert await client.get_user_devices() == DEVICES
        ws.connect.assert_awaited_once()
        ws.list_devices.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reuses_one_connection_across_calls(self, configured):
        patcher, ws = _patched_ws(DEVICES)
        with patcher:
            client = _make_client()
            await client.get_user_devices()
            await client.get_user_devices()
        # Two reads, one handshake.
        assert ws.list_devices.await_count == 2
        ws.connect.assert_awaited_once()

    def test_module_does_not_import_aiohttp(self):
        """The REST path is gone, not merely unused."""
        import ast
        import inspect

        import src.ha_client as module

        assert not hasattr(module, "aiohttp")

        # Compare against code only. The module docstring names the dead REST
        # paths on purpose, to explain why they went away.
        tree = ast.parse(inspect.getsource(module))
        body = tree.body[1:] if ast.get_docstring(tree) else tree.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "api/config/device_registry" not in code
        assert "api/config/entity_registry" not in code


class TestFailureHandling:
    @pytest.mark.asyncio
    async def test_returns_empty_when_ha_not_configured(self, monkeypatch):
        monkeypatch.delenv("HA_URL", raising=False)
        monkeypatch.delenv("HA_HTTP_URL", raising=False)
        monkeypatch.delenv("HA_TOKEN", raising=False)
        monkeypatch.delenv("HOME_ASSISTANT_TOKEN", raising=False)

        patcher, ws = _patched_ws(DEVICES)
        with patcher:
            client = _make_client()
            assert await client.get_user_devices() == []
        ws.connect.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_drops_connection_so_next_call_reconnects(self, configured):
        patcher, ws = _patched_ws(side_effect=RuntimeError("socket closed"))
        with patcher:
            client = _make_client()
            assert await client.get_user_devices() == []
            # The dead connection must not be cached.
            assert client._ws is None
        ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_is_idempotent(self, configured):
        patcher, ws = _patched_ws(DEVICES)
        with patcher:
            client = _make_client()
            await client.get_user_devices()
            await client.close()
            await client.close()
        ws.close.assert_awaited_once()
