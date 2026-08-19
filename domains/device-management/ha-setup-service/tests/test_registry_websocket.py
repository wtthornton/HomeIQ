"""Registry-access tests for ha-setup-service (TAP-5424).

Four call sites moved to the Home Assistant WebSocket API: entity and area reads
in ValidationService, the entity-registry update that applies a fix, and the
device-registry read in IntegrationHealthChecker.

The apply path matters most. It POSTed to a REST path that does not exist, so
"apply this fix" never changed anything in Home Assistant.
"""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ENTITIES = [{"entity_id": "light.lamp", "area_id": None, "platform": "wled"}]
AREAS = [{"area_id": "area_lr", "name": "Living Room"}]
DEVICES = [{"id": "dev-1", "name": "Lamp"}, {"id": "dev-2", "name": "Sensor"}]


def _ws():
    ws = MagicMock()
    ws.connect = AsyncMock()
    ws.close = AsyncMock()
    ws.list_entities = AsyncMock(return_value=ENTITIES)
    ws.list_areas = AsyncMock(return_value=AREAS)
    ws.list_devices = AsyncMock(return_value=DEVICES)

    # Applying a fix goes through HARegistryWriter, which reads the value back
    # (TAP-6230). A mock that only echoed the update would report success against
    # a registry that never changed, so this one holds state.
    registry = deepcopy(ENTITIES)

    async def send_command(command_type, *, fields=None, **payload):
        args = {**payload, **(fields or {})}
        if command_type == "config/area_registry/list":
            return AREAS
        if command_type == "config/entity_registry/get":
            return next(e for e in registry if e["entity_id"] == args["entity_id"])
        if command_type == "config/entity_registry/update":
            entry = next(e for e in registry if e["entity_id"] == args["entity_id"])
            entry.update({k: v for k, v in args.items() if k != "entity_id"})
            return entry
        raise AssertionError(f"unexpected command {command_type}")

    ws.send_command = AsyncMock(side_effect=send_command)
    ws.registry = registry
    return ws


def _facade(ws):
    facade = MagicMock()
    facade.ws = ws
    return facade


class TestValidationServiceRegistry:
    @pytest.mark.asyncio
    async def test_apply_fix_uses_update_entity_command(self):
        from src.validation_service import ValidationService

        ws = _ws()
        with patch("src.validation_service.SharedHAClient", return_value=_facade(ws)):
            service = ValidationService()
            result = await service.apply_fix("light.lamp", "area_lr")

        assert result["success"] is True
        assert result["entity_id"] == "light.lamp"
        assert result["changed"] is True
        # The area is reported applied only because the registry now holds it.
        assert ws.registry[0]["area_id"] == "area_lr"
        ws.send_command.assert_any_await(
            "config/entity_registry/update",
            fields={"entity_id": "light.lamp", "area_id": "area_lr"},
        )

    @pytest.mark.asyncio
    async def test_apply_fix_refuses_an_area_home_assistant_does_not_have(self):
        from homeiq_ha.registry_writer import UnknownTarget
        from src.validation_service import ValidationService

        ws = _ws()
        with patch("src.validation_service.SharedHAClient", return_value=_facade(ws)):
            service = ValidationService()
            with pytest.raises(UnknownTarget):
                await service.apply_fix("light.lamp", "area_attic")

        assert ws.registry[0]["area_id"] is None

    @pytest.mark.asyncio
    async def test_apply_fix_raises_and_drops_connection(self):
        from src.validation_service import ValidationService

        ws = _ws()
        ws.send_command.side_effect = RuntimeError("command failed")
        with patch("src.validation_service.SharedHAClient", return_value=_facade(ws)):
            service = ValidationService()
            with pytest.raises(RuntimeError):
                await service.apply_fix("light.lamp", "area_lr")
            assert service._ws is None

    @pytest.mark.asyncio
    async def test_entities_and_areas_share_one_connection(self):
        from src.validation_service import ValidationService

        ws = _ws()
        with patch("src.validation_service.SharedHAClient", return_value=_facade(ws)):
            service = ValidationService()
            connection = await service._connection()
            await connection.list_entities()
            await connection.list_areas()

        ws.connect.assert_awaited_once()


class TestIntegrationCheckerRegistry:
    @pytest.mark.asyncio
    async def test_device_registry_read_over_websocket(self):
        from src.integration_checker import IntegrationHealthChecker

        ws = _ws()
        with patch("src.integration_checker.SharedHAClient", return_value=_facade(ws)):
            checker = IntegrationHealthChecker()
            devices = await checker._device_registry()

        assert len(devices) == 2
        ws.list_devices.assert_awaited_once()


class TestDeadRestPathsRemoved:
    def test_no_rest_registry_paths_remain(self):
        import ast
        import inspect

        import src.integration_checker as checker_module
        import src.validation_service as validation_module

        for module in (validation_module, checker_module):
            tree = ast.parse(inspect.getsource(module))
            body = tree.body[1:] if ast.get_docstring(tree) else tree.body
            code = "\n".join(ast.unparse(node) for node in body)

            assert "api/config/entity_registry" not in code
            assert "api/config/area_registry" not in code
            assert "api/config/device_registry" not in code

    def test_states_fallback_for_entities_is_gone(self):
        """A states-API fallback silently validated against registry-less data."""
        import ast
        import inspect

        import src.validation_service as module

        tree = ast.parse(inspect.getsource(module))
        code = "\n".join(ast.unparse(node) for node in tree.body[1:])

        assert "friendly_name" not in code
