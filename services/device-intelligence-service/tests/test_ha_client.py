"""Tests for HomeAssistantClient registry parsing."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pytest

from src.clients.ha_client import HomeAssistantClient


FIXTURE_ROOT = Path(__file__).parent / "fixtures"


def _load_fixture(filename: str) -> Any:
    with (FIXTURE_ROOT / filename).open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.asyncio
async def test_get_device_registry_parses_devices(monkeypatch):
    """HomeAssistantClient should normalise devices with mixed timestamp formats."""

    payload = _load_fixture("ha_device_registry.json")
    client = HomeAssistantClient("http://homeassistant.local:8123", None, "test-token")
    client.connected = True

    async def fake_send(message: Dict[str, Any]) -> Dict[str, Any]:
        assert message["type"] == "config/device_registry/list"
        return {"result": payload}

    monkeypatch.setattr(client, "send_message", fake_send)

    devices = await client.get_device_registry()

    assert len(devices) == 2

    kitchen = devices[0]
    assert kitchen.id == "abcd1234"
    assert kitchen.name_by_user == "Ceiling"
    assert kitchen.integration == "hue"
    assert kitchen.created_at == datetime(2025, 1, 5, 18, 22, 11, 421235, tzinfo=timezone.utc)
    assert kitchen.updated_at == datetime(2025, 4, 12, 9, 10, 22, tzinfo=timezone.utc)

    garage = devices[1]
    assert garage.suggested_area == "garage"
    assert garage.via_device_id == "coordinator-1"
    # Float timestamps should be normalised to UTC datetimes
    assert garage.created_at.year == 2024
    assert garage.created_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_get_entity_registry_parses_entities(monkeypatch):
    """Entity registry responses should map optional fields safely."""

    payload = _load_fixture("ha_entity_registry.json")
    client = HomeAssistantClient("http://homeassistant.local:8123", None, "test-token")
    client.connected = True

    async def fake_send(message: Dict[str, Any]) -> Dict[str, Any]:
        assert message["type"] == "config/entity_registry/list"
        return {"result": payload}

    monkeypatch.setattr(client, "send_message", fake_send)

    entities = await client.get_entity_registry()

    assert len(entities) == 2

    kitchen = entities[0]
    assert kitchen.entity_id == "light.kitchen_ceiling_lights"
    assert kitchen.original_icon == "mdi:ceiling-light"
    assert kitchen.has_entity_name is True
    assert kitchen.created_at == datetime(2025, 1, 5, 18, 22, 15, tzinfo=timezone.utc)

    garage = entities[1]
    assert garage.domain == "binary_sensor"
    assert garage.name is None
    assert garage.created_at.year == 2024
    assert garage.updated_at.year == 2024

