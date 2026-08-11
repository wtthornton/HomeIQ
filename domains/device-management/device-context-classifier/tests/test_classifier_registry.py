"""Registry-access tests for device-context-classifier (TAP-5424).

Before the migration this classifier read the entity registry over a REST path
Home Assistant does not serve. The non-200 tripped an early return, so every
device came back device_type=None with confidence 0.0 — the service could never
classify anything. These tests pin the WebSocket read and that early return
staying gone.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ENTITIES = [
    {"entity_id": "light.lamp"},
    {"entity_id": "sensor.lamp_power"},
]


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://ha.local:8123")
    monkeypatch.setenv("HA_TOKEN", "test-token")


def _classifier():
    from src.classifier import DeviceContextClassifier

    return DeviceContextClassifier()


def _patched(entities=ENTITIES, side_effect=None):
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.close = AsyncMock()
    ws.list_entities = AsyncMock(return_value=entities, side_effect=side_effect)
    facade = MagicMock()
    facade.ws = ws
    return patch("src.classifier.SharedHAClient", return_value=facade), ws


class TestRegistryOverWebSocket:
    @pytest.mark.asyncio
    async def test_classifies_instead_of_bailing_out(self):
        patcher, ws = _patched()
        with patcher:
            classifier = _classifier()
            classifier._fetch_entity_state = AsyncMock(return_value=None)
            try:
                result = await classifier.classify_device(
                    "dev-1", ["light.lamp", "sensor.lamp_power"]
                )
            finally:
                await classifier.close()

        # The old REST path made this unreachable: a 404 returned early with
        # device_type None before any pattern matching ran.
        assert result["device_id"] == "dev-1"
        assert result["device_type"] is not None
        ws.list_entities.assert_awaited()

    @pytest.mark.asyncio
    async def test_matched_entities_counts_registry_hits_not_inputs(self):
        patcher, _ = _patched()
        with patcher:
            classifier = _classifier()
            classifier._fetch_entity_state = AsyncMock(return_value=None)
            try:
                result = await classifier.classify_device(
                    "dev-1", ["light.lamp", "sensor.lamp_power", "switch.not_registered"]
                )
            finally:
                await classifier.close()

        # Three ids in, two of them actually in the registry. The old value was
        # len(entity_ids), which would have said 3.
        assert result["matched_entities"] == 2

    @pytest.mark.asyncio
    async def test_registry_failure_drops_the_connection(self):
        patcher, ws = _patched(side_effect=RuntimeError("socket closed"))
        with patcher:
            classifier = _classifier()
            assert await classifier._entity_registry() == {}
            assert classifier._ws is None
        ws.close.assert_awaited_once()

    def test_rest_registry_path_is_gone(self):
        import ast
        import inspect

        import src.classifier as module

        tree = ast.parse(inspect.getsource(module))
        body = tree.body[1:] if ast.get_docstring(tree) else tree.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "api/config/entity_registry" not in code
        # The states API is REST and must survive.
        assert "api/states/" in code
