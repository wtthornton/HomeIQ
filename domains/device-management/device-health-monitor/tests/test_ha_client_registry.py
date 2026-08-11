"""Registry-access tests for device-health-monitor (TAP-5424).

The entity registry is read over the Home Assistant WebSocket API. The REST path
this used to call does not exist, so every read 404'd and returned {} — which the
health checks could not distinguish from "this instance has no entities".

States and history stay on aiohttp; those are real REST endpoints.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ENTITIES = [
    {"entity_id": "light.lamp", "disabled_by": None},
    {"entity_id": "sensor.temp", "disabled_by": "user"},
]


def _client():
    from src.ha_client import HAClient

    return HAClient("http://ha.local:8123", "test-token")


def _patched(entities=ENTITIES, side_effect=None):
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.close = AsyncMock()
    ws.list_entities = AsyncMock(return_value=entities, side_effect=side_effect)
    facade = MagicMock()
    facade.ws = ws
    return patch("src.ha_client.SharedHAClient", return_value=facade), ws


class TestEntityRegistryOverWebSocket:
    @pytest.mark.asyncio
    async def test_returns_registry_keyed_by_entity_id(self):
        patcher, ws = _patched()
        with patcher:
            registry = await _client().get_entity_registry()
        assert registry == {
            "light.lamp": ENTITIES[0],
            "sensor.temp": ENTITIES[1],
        }
        ws.list_entities.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_reuses_one_connection(self):
        patcher, ws = _patched()
        with patcher:
            client = _client()
            await client.get_entity_registry()
            await client.get_entity_registry()
        ws.connect.assert_awaited_once()
        assert ws.list_entities.await_count == 2

    @pytest.mark.asyncio
    async def test_failure_drops_connection_and_returns_empty(self):
        patcher, ws = _patched(side_effect=RuntimeError("socket closed"))
        with patcher:
            client = _client()
            assert await client.get_entity_registry() == {}
            assert client._ws is None
        ws.close.assert_awaited_once()

    def test_rest_registry_path_is_gone_but_history_stays(self):
        import ast
        import inspect

        import src.ha_client as module

        tree = ast.parse(inspect.getsource(module))
        body = tree.body[1:] if ast.get_docstring(tree) else tree.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "api/config/entity_registry" not in code
        # History/states are REST and must survive the migration.
        assert "api/history/period" in code
