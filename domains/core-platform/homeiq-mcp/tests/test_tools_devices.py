"""Group 2 tools against real data-api envelopes (`{devices,count,limit}` etc.)."""

from __future__ import annotations

import httpx
import pytest
import respx
from src.auth import READ_SCOPES
from src.errors import ToolError
from src.tools import devices

DATA_API = "http://data-api.test:8006"


def _device(i: int, **extra):
    return {
        "device_id": f"dev{i}",
        "name": f"Device {i}",
        "manufacturer": "Aqara" if i % 2 else "",
        "model": "FP1E",
        "integration": "zha",
        "sw_version": None,
        "area_id": "office",
        "entity_count": i,
        **extra,
    }


def _entity(i: int, **extra):
    return {
        "entity_id": f"sensor.e{i}",
        "device_id": "dev1",
        "domain": "sensor",
        "platform": "zha",
        "area_id": None,
        "friendly_name": f"E {i}",
        "device_class": "temperature",
        "disabled": False,
        **extra,
    }


def _automation(i: int):
    return {
        "automation_id": f"automation.a{i}",
        "alias": f"A{i}",
        "description": None,
        "mode": "single",
        "enabled": True,
        "total_executions": 10 * i,
        "total_errors": i,
        "avg_duration_seconds": 0.5,
        "success_rate": 90.0,
        "last_triggered": None,
        "created_at": None,
        "updated_at": None,
    }


@pytest.fixture
def reg(registry, backings):
    devices.register(registry, backings)
    return registry


def _validate(catalogue, name, payload):
    catalogue.tools[name].output_validator.validate(payload)


def test_registers_group(reg):
    assert reg.names() == [
        "get_automation_stats",
        "get_device",
        "list_areas",
        "list_devices",
        "list_entities",
    ]


@respx.mock
async def test_list_devices_unwraps_envelope_and_filters(reg, catalogue):
    route = respx.get(f"{DATA_API}/api/devices").mock(
        return_value=httpx.Response(
            200, json={"devices": [_device(1), _device(2)], "count": 2, "limit": 100}
        )
    )
    out = await reg.call("list_devices", {"area_id": "office", "limit": 50}, scopes=READ_SCOPES)
    _validate(catalogue, "list_devices", out)
    assert out["devices"][0] == {
        "device_id": "dev1",
        "name": "Device 1",
        "entity_count": 1,
        "manufacturer": "Aqara",
        "model": "FP1E",
        "area_id": "office",
        "integration": "zha",
    }
    assert "manufacturer" not in out["devices"][1]  # empty string dropped
    params = route.calls.last.request.url.params
    assert params["area_id"] == "office" and params["limit"] == "50" and "model" not in params


@respx.mock
async def test_list_devices_row_cap(reg, catalogue):
    respx.get(f"{DATA_API}/api/devices").mock(
        return_value=httpx.Response(
            200, json={"devices": [_device(i) for i in range(310)], "count": 310, "limit": 500}
        )
    )
    out = await reg.call("list_devices", {"limit": 300}, scopes=READ_SCOPES)
    _validate(catalogue, "list_devices", out)
    assert out["truncated"] is True and out["hint"] == "limit" and out["count"] == 300


@respx.mock
async def test_list_devices_bare_list_is_contract_violation(reg):
    respx.get(f"{DATA_API}/api/devices").mock(return_value=httpx.Response(200, json=[_device(1)]))
    with pytest.raises(ToolError) as exc:
        await reg.call("list_devices", {}, scopes=READ_SCOPES)
    assert exc.value.code == "contract_violation"


@respx.mock
async def test_get_device_joins_entities(reg, catalogue):
    respx.get(f"{DATA_API}/api/devices/dev1").mock(
        return_value=httpx.Response(200, json=_device(1, labels=["x"]))
    )
    respx.get(f"{DATA_API}/api/entities/by-device/dev1").mock(
        return_value=httpx.Response(
            200,
            json={
                "success": True,
                "device_id": "dev1",
                "entities": [_entity(1), _entity(2)],
                "count": 2,
            },
        )
    )
    out = await reg.call("get_device", {"device_id": "dev1"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_device", out)
    assert out["device"]["labels"] == ["x"] and "sw_version" not in out["device"]
    assert out["entities"][0] == {
        "entity_id": "sensor.e1",
        "domain": "sensor",
        "disabled": False,
        "device_class": "temperature",
    }
    assert out["entity_count"] == 2 and out["truncated"] is False


@respx.mock
async def test_get_device_404(reg):
    respx.get(f"{DATA_API}/api/devices/nope").mock(return_value=httpx.Response(404))
    with pytest.raises(ToolError) as exc:
        await reg.call("get_device", {"device_id": "nope"}, scopes=READ_SCOPES)
    assert exc.value.code == "not_found"


@respx.mock
async def test_list_entities_projection_and_cap(reg, catalogue):
    respx.get(f"{DATA_API}/api/entities").mock(
        return_value=httpx.Response(
            200, json={"entities": [_entity(i) for i in range(505)], "count": 505, "limit": 600}
        )
    )
    out = await reg.call("list_entities", {"domain": "sensor", "limit": 500}, scopes=READ_SCOPES)
    _validate(catalogue, "list_entities", out)
    # 505 rows exceed both the 500 row cap and the 48 KB byte budget; either way it is flagged.
    assert (
        out["truncated"] is True
        and out["hint"] == "limit"
        and out["count"] == len(out["entities"]) <= 500
    )
    assert out["entities"][0] == {
        "entity_id": "sensor.e0",
        "domain": "sensor",
        "disabled": False,
        "device_class": "temperature",
        "device_id": "dev1",
        "friendly_name": "E 0",
    }


@respx.mock
async def test_list_areas(reg, catalogue):
    respx.get(f"{DATA_API}/api/areas").mock(
        return_value=httpx.Response(
            200,
            json={
                "areas": [
                    {
                        "area_id": "office",
                        "display_name": "Office",
                        "entity_count": 12,
                        "domains": ["light"],
                    },
                    {"area_id": "attic", "display_name": "", "entity_count": 0, "domains": []},
                ],
                "count": 2,
            },
        )
    )
    out = await reg.call("list_areas", {}, scopes=READ_SCOPES)
    _validate(catalogue, "list_areas", out)
    assert out["areas"][0]["name"] == "Office" and out["areas"][1]["name"] == "attic"


@respx.mock
async def test_automation_stats_overview(reg, catalogue):
    respx.get(f"{DATA_API}/api/v1/automations/stats/overview").mock(
        return_value=httpx.Response(
            200,
            json={
                "total_automations": 12,
                "total_executions": 340,
                "total_errors": 3,
                "error_rate_percent": 0.9,
                "avg_success_rate": 98.2,
                "avg_duration_seconds": 0.4,
                "top_errors": [],
            },
        )
    )
    out = await reg.call("get_automation_stats", {}, scopes=READ_SCOPES)
    _validate(catalogue, "get_automation_stats", out)
    assert out["overview"] == {
        "total_automations": 12,
        "total_executions": 340,
        "error_rate_percent": 0.9,
        "avg_success_rate": 98.2,
    }


@respx.mock
@pytest.mark.parametrize(
    ("view", "path"),
    [
        ("list", "/api/v1/automations"),
        ("errors", "/api/v1/automations/stats/errors"),
        ("slow", "/api/v1/automations/stats/slow"),
        ("inactive", "/api/v1/automations/stats/inactive"),
    ],
)
async def test_automation_stats_views(reg, catalogue, view, path):
    route = respx.get(f"{DATA_API}{path}").mock(
        return_value=httpx.Response(
            200, json={"count": 2, "automations": [_automation(1), _automation(2)]}
        )
    )
    out = await reg.call("get_automation_stats", {"view": view, "limit": 10}, scopes=READ_SCOPES)
    _validate(catalogue, "get_automation_stats", out)
    assert out["view"] == view and out["count"] == 2
    assert out["automations"][0] == {
        "automation_id": "automation.a1",
        "enabled": True,
        "total_executions": 10,
        "total_errors": 1,
        "alias": "A1",
        "success_rate": 90.0,
        "avg_duration_seconds": 0.5,
    }
    assert route.calls.last.request.url.params["limit"] == "10"


@respx.mock
async def test_automation_stats_single_automation(reg, catalogue):
    respx.get(f"{DATA_API}/api/v1/automations/automation.a9").mock(
        return_value=httpx.Response(200, json=_automation(9))
    )
    out = await reg.call(
        "get_automation_stats",
        {"view": "list", "automation_id": "automation.a9"},
        scopes=READ_SCOPES,
    )
    _validate(catalogue, "get_automation_stats", out)
    assert out["count"] == 1 and out["automations"][0]["automation_id"] == "automation.a9"


@respx.mock
async def test_automation_stats_row_cap(reg, catalogue):
    respx.get(f"{DATA_API}/api/v1/automations/stats/errors").mock(
        return_value=httpx.Response(
            200, json={"count": 120, "automations": [_automation(i) for i in range(120)]}
        )
    )
    out = await reg.call(
        "get_automation_stats", {"view": "errors", "limit": 100}, scopes=READ_SCOPES
    )
    _validate(catalogue, "get_automation_stats", out)
    # Upstream over-delivered (120 > limit 100); the local slice honours the request exactly.
    assert out["truncated"] is False and out["count"] == 100


@pytest.mark.parametrize("bad", ["../v1/energy/statistics", "dev/1", "dev?x=1", "dev#1"])
async def test_get_device_rejects_path_traversal_ids(reg, bad):
    with pytest.raises(ToolError) as exc:
        await reg.call("get_device", {"device_id": bad}, scopes=READ_SCOPES)
    assert exc.value.code == "invalid_input"


async def test_automation_id_is_path_guarded(reg):
    with pytest.raises(ToolError) as exc:
        await reg.call(
            "get_automation_stats",
            {"view": "list", "automation_id": "../stats/overview"},
            scopes=READ_SCOPES,
        )
    assert exc.value.code == "invalid_input"


@respx.mock
async def test_get_device_budget_truncation_recounts_and_has_no_hint(reg, catalogue):
    respx.get(f"{DATA_API}/api/devices/dev1").mock(
        return_value=httpx.Response(200, json=_device(1))
    )
    respx.get(f"{DATA_API}/api/entities/by-device/dev1").mock(
        return_value=httpx.Response(
            200, json={"entities": [_entity(i, friendly_name="x" * 100) for i in range(400)]}
        )
    )
    out = await reg.call("get_device", {"device_id": "dev1"}, scopes=READ_SCOPES)
    _validate(catalogue, "get_device", out)
    assert out["truncated"] is True and "hint" not in out
    assert out["entity_count"] == len(out["entities"]) < 400


@respx.mock
async def test_automation_stats_inactive_applies_limit_locally(reg, catalogue):
    respx.get(f"{DATA_API}/api/v1/automations/stats/inactive").mock(
        return_value=httpx.Response(
            200, json={"count": 30, "automations": [_automation(i) for i in range(30)]}
        )
    )
    out = await reg.call(
        "get_automation_stats", {"view": "inactive", "limit": 5}, scopes=READ_SCOPES
    )
    _validate(catalogue, "get_automation_stats", out)
    assert out["count"] == 5
