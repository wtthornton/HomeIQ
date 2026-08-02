"""Registry-access tests for ha-ai-agent-service (TAP-5424).

This service already reached for WebSocket first, but through its own
connect/auth/send/correlate loop — a second implementation of what
homeiq_ha.client.HAWebSocketClient does. It now uses the shared client.

The REST fallbacks are gone. Each caught the WebSocket error, retried a REST
registry path that does not exist, and returned [] on the resulting 404, so a
genuine WebSocket failure surfaced to callers as "Home Assistant has no
areas/entities/devices".
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

AREAS = [{"area_id": "area_lr", "name": "Living Room"}]
ENTITIES = [{"entity_id": "light.lamp"}]
DEVICES = [{"id": "dev-1", "name": "Lamp"}]


def _client():
    from src.clients.ha_client import HomeAssistantClient
    return HomeAssistantClient("http://ha.local:8123", "test-token")


def _ws():
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.close = AsyncMock()
    ws.list_areas = AsyncMock(return_value=AREAS)
    ws.list_entities = AsyncMock(return_value=ENTITIES)
    ws.list_devices = AsyncMock(return_value=DEVICES)
    return ws


class TestRegistriesUseTheSharedClient:

    @pytest.mark.asyncio
    async def test_area_registry(self):
        ws = _ws()
        with patch("src.clients.ha_client.HAWebSocketClient", return_value=ws):
            assert await _client().get_area_registry() == AREAS
        ws.list_areas.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_entity_registry(self):
        ws = _ws()
        with patch("src.clients.ha_client.HAWebSocketClient", return_value=ws):
            assert await _client().get_entity_registry() == ENTITIES
        ws.list_entities.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_device_registry(self):
        ws = _ws()
        with patch("src.clients.ha_client.HAWebSocketClient", return_value=ws):
            assert await _client().get_device_registry() == DEVICES
        ws.list_devices.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_three_reads_share_one_handshake(self):
        ws = _ws()
        with patch("src.clients.ha_client.HAWebSocketClient", return_value=ws):
            client = _client()
            await client.get_area_registry()
            await client.get_entity_registry()
            await client.get_device_registry()
        # The old code opened a fresh connection per command.
        ws.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_ssl_context_is_forwarded(self):
        import ssl as ssl_module

        from src.clients.ha_client import HomeAssistantClient

        context = ssl_module.create_default_context()
        ws = _ws()
        with patch("src.clients.ha_client.HAWebSocketClient", return_value=ws) as ctor:
            client = HomeAssistantClient("https://ha.local:8123", "t", ssl_context=context)
            await client.get_area_registry()

        assert ctor.call_args.kwargs["ssl_context"] is context
        assert ctor.call_args.args[0] == "wss://ha.local:8123/api/websocket"


class TestFailuresSurface:

    @pytest.mark.asyncio
    async def test_failure_raises_instead_of_returning_empty(self):
        ws = _ws()
        ws.list_areas.side_effect = RuntimeError("socket closed")
        with patch("src.clients.ha_client.HAWebSocketClient", return_value=ws):
            client = _client()
            with pytest.raises(RuntimeError):
                await client.get_area_registry()
            assert client._ws is None

    def test_rest_registry_fallbacks_are_gone(self):
        import ast
        import inspect

        import src.clients.ha_client as module

        tree = ast.parse(inspect.getsource(module))
        body = tree.body[1:] if ast.get_docstring(tree) else tree.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "api/config/area_registry" not in code
        assert "api/config/entity_registry" not in code
        assert "api/config/device_registry" not in code
        # /api/states and /api/services are real REST and must survive.
        assert "api/states" in code
        assert "api/services" in code
