"""Registry-access tests for device-intelligence-service (TAP-5424).

Capability discovery reads the entity registry over the Home Assistant WebSocket
API. The REST path it used before does not exist, and the handler was doubly
broken: on a 200 it called `.get("entities")` on what HA returns as a flat list,
which would have raised AttributeError. In practice the 404 branch fired first
and discovery returned no capabilities for every device.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ENTITIES = [
    {"entity_id": "light.lamp", "platform": "wled"},
    {"entity_id": "sensor.temp", "platform": "esphome"},
]


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://ha.local:8123")
    monkeypatch.setenv("HA_TOKEN", "test-token")


def _discoverer():
    from src.capability_discovery.ha_api_discovery import HACapabilityDiscoverer
    return HACapabilityDiscoverer()


def _patched(entities=ENTITIES, side_effect=None):
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.close = AsyncMock()
    ws.list_entities = AsyncMock(return_value=entities, side_effect=side_effect)
    facade = MagicMock()
    facade.ws = ws
    return patch(
        "src.capability_discovery.ha_api_discovery.SharedHAClient",
        return_value=facade,
    ), ws


class TestEntityRegistryOverWebSocket:

    @pytest.mark.asyncio
    async def test_registry_is_read_over_websocket_and_keyed(self):
        patcher, ws = _patched()
        with patcher:
            registry = await _discoverer()._entity_registry()
        assert set(registry) == {"light.lamp", "sensor.temp"}
        ws.list_entities.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_flat_list_is_handled(self):
        """HA returns a flat list; the old code called .get() on it."""
        patcher, _ = _patched()
        with patcher:
            registry = await _discoverer()._entity_registry()
        assert registry["light.lamp"]["platform"] == "wled"

    @pytest.mark.asyncio
    async def test_failure_drops_connection_and_returns_empty(self):
        patcher, ws = _patched(side_effect=RuntimeError("socket closed"))
        with patcher:
            discoverer = _discoverer()
            assert await discoverer._entity_registry() == {}
            assert discoverer._ws is None
        ws.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_discover_capabilities_runs_past_the_registry_read(self):
        """Exercises the whole flow, not just the registry helper.

        The first version of this migration left a later `for entity_info in
        entities:` referring to a name the new code no longer binds. Testing
        _entity_registry() alone could not see it; ruff's F821 did.
        """
        discoverer = _discoverer()
        discoverer._get_entity_state = AsyncMock(return_value=None)
        patcher, _ = _patched()

        with patcher, patch.object(
            type(discoverer), "_get_session", new=AsyncMock(return_value=MagicMock())
        ):
            result = await discoverer.discover_capabilities("dev-1", ["light.lamp"])

        assert "capabilities" in result
        assert "features" in result

    def test_rest_registry_path_is_gone_but_states_stay(self):
        import ast
        import inspect

        import src.capability_discovery.ha_api_discovery as module

        tree = ast.parse(inspect.getsource(module))
        body = tree.body[1:] if ast.get_docstring(tree) else tree.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "api/config/entity_registry" not in code
        # The State API is REST and must survive.
        assert "api/states/" in code
