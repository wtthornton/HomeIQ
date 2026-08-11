"""Area-registry tests for ai-training-service (TAP-5424).

Areas are created with the Home Assistant WebSocket `config/area_registry/create`
command. The REST path this used to POST to does not exist, so every area
creation failed and the loader appended "Failed to create area" for all of them
while still reporting success for the entities.

Entity states stay on REST — POST /api/states/{entity_id} is a real endpoint.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _loader():
    from src.training.synthetic_home_ha_loader import SyntheticHomeHALoader

    return SyntheticHomeHALoader()


def _ws(area_id="area_living_room", side_effect=None):
    ws = MagicMock()
    ws.create_area = AsyncMock(
        return_value={"area_id": area_id, "name": "Living Room"},
        side_effect=side_effect,
    )
    return ws


class TestAreaCreationOverWebSocket:
    @pytest.mark.asyncio
    async def test_returns_area_id_from_websocket_command(self):
        ws = _ws()
        area_id = await _loader().create_ha_area(ws, "Living Room")
        assert area_id == "area_living_room"
        ws.create_area.assert_awaited_once_with("Living Room")

    @pytest.mark.asyncio
    async def test_failure_returns_none_rather_than_raising(self):
        ws = _ws(side_effect=RuntimeError("command failed"))
        assert await _loader().create_ha_area(ws, "Living Room") is None

    @pytest.mark.asyncio
    async def test_missing_area_id_in_response_is_none(self):
        ws = MagicMock()
        ws.create_area = AsyncMock(return_value={})
        assert await _loader().create_ha_area(ws, "Attic") is None

    def test_rest_area_registry_path_is_gone_but_states_stay(self):
        import ast
        import inspect

        import src.training.synthetic_home_ha_loader as module

        tree = ast.parse(inspect.getsource(module))
        body = tree.body[1:] if ast.get_docstring(tree) else tree.body
        code = "\n".join(ast.unparse(node) for node in body)

        assert "api/config/area_registry" not in code
        # Entity states are REST and must survive.
        assert "api/states/" in code
