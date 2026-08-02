"""Entity/device linking registry tests for data-api (TAP-5424).

This was the riskiest of the twelve call sites. It read the entity registry over
a REST path Home Assistant does not serve, and treated the resulting 404 as a cue
to match entities to devices by config_entry_id instead. The endpoint then
returned a linked count that looked like success, so a registry that had never
been read was indistinguishable from one that had.

The registry is now read over WebSocket and a failure is a 502. These tests pin
that, because the failure mode they replace was silent by construction.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

REGISTRY = [
    {"entity_id": "light.lamp", "device_id": "dev-1"},
    {"entity_id": "sensor.temp", "device_id": None},
]


@pytest.fixture(autouse=True)
def ha_configured(monkeypatch):
    monkeypatch.setenv("HA_URL", "http://ha.local:8123")
    monkeypatch.setenv("HA_TOKEN", "test-token")


def _facade(entities=REGISTRY, side_effect=None):
    """Patch the shared facade so `.ws` is an async-context-manager mock."""
    ws = MagicMock()
    ws.list_entities = AsyncMock(return_value=entities, side_effect=side_effect)
    ws.__aenter__ = AsyncMock(return_value=ws)
    ws.__aexit__ = AsyncMock(return_value=None)
    facade = MagicMock()
    facade.ws = ws
    return facade, ws


class TestRegistryFailureIsSurfaced:

    @pytest.mark.asyncio
    async def test_registry_failure_raises_502_not_a_linked_count(self):
        """The old code answered 200 with a count sourced from config_entry_id."""
        from src.devices_endpoints import link_entities_to_devices

        facade, _ = _facade(side_effect=RuntimeError("socket closed"))

        db = MagicMock()
        entity = MagicMock(entity_id="light.lamp", device_id=None, config_entry_id="ce-1")
        db.execute = AsyncMock(
            return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: [entity])))
        )

        with patch("homeiq_ha.client.HAClient", return_value=facade), \
             pytest.raises(HTTPException) as excinfo:
            await link_entities_to_devices(limit=10, db=db)

        assert excinfo.value.status_code == 502
        assert "entity registry" in str(excinfo.value.detail).lower()


class TestNoSilentConfigEntryFallback:

    def test_config_entry_id_fallback_is_gone(self):
        """Matching on config_entry_id was the mask over the failed registry read."""
        import ast
        import inspect

        import src.devices_endpoints as module

        source = inspect.getsource(module.link_entities_to_devices)
        tree = ast.parse(source.lstrip())
        code = ast.unparse(tree)

        assert "Device.config_entry_id == entity.config_entry_id" not in code
        assert "api/config/entity_registry" not in code

    def test_registry_is_read_over_websocket(self):
        import inspect

        import src.devices_endpoints as module

        source = inspect.getsource(module.link_entities_to_devices)
        assert "list_entities()" in source
        assert "SharedHAClient" in source
