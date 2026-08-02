"""Registry-access tests for device-setup-assistant (TAP-5424).

The device and entity registries must be read over the Home Assistant WebSocket
API. The REST paths this service used do not exist, so every read 404'd and was
converted into an empty registry — which downstream looked like "this device has
no entities" rather than "the registry could not be read".

The states API is a genuine REST endpoint and deliberately still uses aiohttp;
these tests pin that split so a later cleanup does not collapse both onto one
transport.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

DEVICES = [{"id": "dev-1", "name": "Lamp"}, {"id": "dev-2", "name": "Sensor"}]
ENTITIES = [
    {"entity_id": "light.lamp", "disabled_by": None},
    {"entity_id": "sensor.temp", "disabled_by": "user"},
    {"entity_id": "sensor.hum", "disabled_by": "integration"},
]


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://ha.local:8123")
    monkeypatch.setenv("HA_TOKEN", "test-token")


def _patched_ws():
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.close = AsyncMock()
    ws.list_devices = AsyncMock(return_value=DEVICES)
    ws.list_entities = AsyncMock(return_value=ENTITIES)
    facade = MagicMock()
    facade.ws = ws
    return patch("src.ha_client.SharedHAClient", return_value=facade), ws


def _make_client():
    from src.ha_client import HAClient
    return HAClient()


class TestRegistriesOverWebSocket:

    @pytest.mark.asyncio
    async def test_device_registry_keyed_by_id(self):
        patcher, ws = _patched_ws()
        with patcher:
            registry = await _make_client().get_device_registry()
        assert registry == {"dev-1": DEVICES[0], "dev-2": DEVICES[1]}
        ws.list_devices.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_entity_registry_keyed_by_entity_id(self):
        patcher, ws = _patched_ws()
        with patcher:
            registry = await _make_client().get_entity_registry()
        assert set(registry) == {"light.lamp", "sensor.temp", "sensor.hum"}
        ws.list_entities.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_both_registries_share_one_handshake(self):
        patcher, ws = _patched_ws()
        with patcher:
            client = _make_client()
            await client.get_device_registry()
            await client.get_entity_registry()
        ws.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_read_drops_the_connection(self):
        patcher, ws = _patched_ws()
        ws.list_devices.side_effect = RuntimeError("socket closed")
        with patcher:
            client = _make_client()
            assert await client.get_device_registry() == {}
            assert client._ws is None
        ws.close.assert_awaited_once()

    def test_registry_reads_are_not_rest(self):
        """The dead REST paths are gone from the code, not just unused."""
        import ast
        import inspect

        import src.ha_client as module

        tree = ast.parse(inspect.getsource(module))
        body = tree.body[1:] if ast.get_docstring(tree) else tree.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "api/config/device_registry" not in code
        assert "api/config/entity_registry" not in code
        # The states API is REST and must survive this migration.
        assert module.aiohttp is not None


class TestIssueDetectorUsesTheSharedRegistry:

    @pytest.mark.asyncio
    async def test_counts_disabled_entities_via_client(self):
        from src.issue_detector import SetupIssueDetector

        ha_client = MagicMock()
        ha_client.ha_url = "http://ha.local:8123"
        ha_client.get_entity_registry = AsyncMock(
            return_value={e["entity_id"]: e for e in ENTITIES}
        )

        detector = SetupIssueDetector(ha_client)
        count = await detector._count_disabled_entities(
            ["light.lamp", "sensor.temp", "sensor.hum", "sensor.missing"]
        )

        # Two disabled, one enabled, one absent from the registry.
        assert count == 2
        ha_client.get_entity_registry.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_registry_failure_counts_zero_without_raising(self):
        from src.issue_detector import SetupIssueDetector

        ha_client = MagicMock()
        ha_client.ha_url = "http://ha.local:8123"
        ha_client.get_entity_registry = AsyncMock(side_effect=RuntimeError("down"))

        detector = SetupIssueDetector(ha_client)
        assert await detector._count_disabled_entities(["light.lamp"]) == 0
