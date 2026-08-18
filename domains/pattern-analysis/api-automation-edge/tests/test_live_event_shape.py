"""Handlers parse Home Assistant's real event shape (TAP-5440).

HA event frames nest the payload: ``{"event_type": "state_changed",
"data": {"entity_id", "old_state", "new_state"}, ...}``. Both handlers
used to read ``entity_id`` off the event root and therefore silently
no-oped on every live event.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.capability.graph_updater import GraphUpdater
from src.execution.confirmation_watcher import ConfirmationWatcher


def ha_state_changed(entity_id: str, state: str) -> dict:
    """A state_changed event exactly as the WS client delivers it."""
    return {
        "event_type": "state_changed",
        "data": {
            "entity_id": entity_id,
            "old_state": {"entity_id": entity_id, "state": "off"},
            "new_state": {"entity_id": entity_id, "state": state},
        },
        "origin": "LOCAL",
        "time_fired": "2026-08-12T19:00:00.000000+00:00",
        "context": {"id": "01ABC", "parent_id": None, "user_id": None},
    }


@pytest.mark.asyncio
async def test_graph_updater_updates_inventory_from_real_event_shape():
    inventory = MagicMock()
    updater = GraphUpdater(entity_inventory=inventory)

    await updater._handle_state_changed(ha_state_changed("light.office", "on"))

    inventory.update_entity.assert_called_once()
    entity_id, new_state = inventory.update_entity.call_args.args
    assert entity_id == "light.office"
    assert new_state["state"] == "on"


@pytest.mark.asyncio
async def test_confirmation_watcher_confirms_from_real_event_shape():
    ws = MagicMock()
    captured: dict = {}

    async def fake_subscribe(event_type=None, handler=None):
        captured["handler"] = handler
        return 7

    ws.subscribe_events = AsyncMock(side_effect=fake_subscribe)
    ws.unsubscribe_events = AsyncMock()

    watcher = ConfirmationWatcher(websocket_client=ws, default_timeout=1.0)

    import asyncio

    task = asyncio.create_task(watcher.wait_for_confirmation("light.office", expected_state="on"))
    while "handler" not in captured:
        await asyncio.sleep(0)

    await captured["handler"](ha_state_changed("light.other", "on"))  # ignored
    await captured["handler"](ha_state_changed("light.office", "on"))  # confirms

    confirmed, error = await asyncio.wait_for(task, timeout=2.0)
    assert confirmed is True
    assert error is None
    ws.unsubscribe_events.assert_awaited_once_with(7)
