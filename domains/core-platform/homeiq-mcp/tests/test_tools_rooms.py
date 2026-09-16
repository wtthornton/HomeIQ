"""Group 6 tool against websocket-ingestion's `/api/status/rooms` envelope."""

from __future__ import annotations

import httpx
import pytest
import respx
from src.auth import READ_SCOPES
from src.errors import ToolError
from src.tools import rooms

WS_INGESTION = "http://ws-ingestion.test:8001"


def _room(area_id: str, **overrides):
    return {
        "area_id": area_id,
        "state": "clear",
        "contributing_entity_ids": ["binary_sensor.office_motion"],
        "last_changed": "2026-09-15T12:00:00+00:00",
        **overrides,
    }


@pytest.fixture
def reg(registry, backings):
    rooms.register(registry, backings)
    return registry


def _validate(catalogue, name, payload):
    catalogue.tools[name].output_validator.validate(payload)


def test_registers_group(reg):
    assert reg.names() == ["get_room_occupancy"]


@respx.mock
async def test_known_area_returns_state_and_contributors(reg, catalogue):
    respx.get(f"{WS_INGESTION}/api/status/rooms").mock(
        return_value=httpx.Response(
            200,
            json={
                "rooms": [
                    _room("attic", state="unknown", contributing_entity_ids=[]),
                    _room("office"),
                ]
            },
        )
    )
    out = await reg.call("get_room_occupancy", {"area_id": "office"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_room_occupancy", out)
    assert out == {
        "area_id": "office",
        "state": "clear",
        "contributing_entity_ids": ["binary_sensor.office_motion"],
        "last_changed": "2026-09-15T12:00:00+00:00",
        "truncated": False,
    }


@respx.mock
async def test_detected_state_lists_contributing_entities(reg, catalogue):
    respx.get(f"{WS_INGESTION}/api/status/rooms").mock(
        return_value=httpx.Response(
            200,
            json={
                "rooms": [
                    _room(
                        "office",
                        state="detected",
                        contributing_entity_ids=[
                            "binary_sensor.office_motion",
                            "binary_sensor.office_door",
                        ],
                    )
                ]
            },
        )
    )
    out = await reg.call("get_room_occupancy", {"area_id": "office"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_room_occupancy", out)
    assert out["state"] == "detected"
    assert out["contributing_entity_ids"] == [
        "binary_sensor.office_motion",
        "binary_sensor.office_door",
    ]


@respx.mock
async def test_sensorless_room_reports_unknown_not_empty(reg, catalogue):
    """A room with no presence-capable sensor is 'unknown', never 'clear' or omitted."""
    respx.get(f"{WS_INGESTION}/api/status/rooms").mock(
        return_value=httpx.Response(
            200, json={"rooms": [_room("attic", state="unknown", contributing_entity_ids=[])]}
        )
    )
    out = await reg.call("get_room_occupancy", {"area_id": "attic"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_room_occupancy", out)
    assert out["state"] == "unknown"
    assert out["contributing_entity_ids"] == []


def test_unknown_state_is_described_as_a_coverage_gap_not_empty(catalogue):
    """The agent-facing schema text must not let 'unknown' read as an empty room."""
    description = catalogue.tools["get_room_occupancy"].output_schema["properties"]["state"][
        "description"
    ]
    assert "no presence-capable sensor" in description
    assert "never report this as an empty" in description


@respx.mock
async def test_unknown_area_id_is_not_found(reg):
    respx.get(f"{WS_INGESTION}/api/status/rooms").mock(
        return_value=httpx.Response(200, json={"rooms": [_room("office")]})
    )
    with pytest.raises(ToolError) as exc:
        await reg.call("get_room_occupancy", {"area_id": "nonexistent-area"}, scopes=READ_SCOPES)
    assert exc.value.code == "not_found"
    assert "nonexistent-area" in exc.value.message


@respx.mock
async def test_bare_list_envelope_is_contract_violation(reg):
    respx.get(f"{WS_INGESTION}/api/status/rooms").mock(
        return_value=httpx.Response(200, json=[_room("office")])
    )
    with pytest.raises(ToolError) as exc:
        await reg.call("get_room_occupancy", {"area_id": "office"}, scopes=READ_SCOPES)
    assert exc.value.code == "contract_violation"


async def test_unconfigured_backing_is_backing_unavailable(registry):
    from src.backends import Backings, HttpBacking

    unconfigured = Backings(
        data_api=HttpBacking("data-api", ""),
        patterns=HttpBacking("ai-pattern-service", ""),
        device_intelligence=HttpBacking("device-intelligence-service", ""),
        house_status=HttpBacking("websocket-ingestion", ""),
    )
    rooms.register(registry, unconfigured)
    with pytest.raises(ToolError) as exc:
        await registry.call("get_room_occupancy", {"area_id": "office"}, scopes=READ_SCOPES)
    assert exc.value.code == "backing_unavailable"
