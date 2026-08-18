"""detect_anomalies against real data-api / device-intelligence payloads."""

from __future__ import annotations

import httpx
import pytest
import respx
from src.auth import READ_SCOPES
from src.errors import ToolError
from src.tools import anomalies

DATA_API = "http://data-api.test:8006"
DEVINT = "http://devint.test:8028"


def _anomaly(i: int):
    return {
        "device_id": f"dev{i}",
        "device_name": f"Device {i}",
        "spec_power_w": 10.0,
        "actual_power_w": 25.0 + i,
        "deviation_percent": 150.0,
        "severity": "high",
        "timestamp": "2026-08-17T10:00:00+00:00",
    }


def _prediction(i: int, prob=72.5, risk="high", recs=("Replace battery", "Check firmware")):
    return {
        "device_id": f"dev{i}",
        "failure_probability": prob,
        "risk_level": risk,
        "predicted_failure_date": None,
        "recommendations": list(recs),
        "confidence": 0.8,
    }


@pytest.fixture
def reg(registry, backings):
    anomalies.register(registry, backings)
    return registry


def _validate(catalogue, payload):
    catalogue.tools["detect_anomalies"].output_validator.validate(payload)


def test_registers_group(reg):
    assert reg.names() == ["detect_anomalies"]


@respx.mock
async def test_power_kind(reg, catalogue):
    route = respx.get(f"{DATA_API}/api/devices/power-anomalies").mock(
        return_value=httpx.Response(
            200, json={"anomalies": [_anomaly(1)], "count": 1, "timestamp": "x"}
        )
    )
    out = await reg.call("detect_anomalies", {"kind": "power", "limit": 20}, scopes=READ_SCOPES)
    _validate(catalogue, out)
    assert out["power_anomalies"] == [
        {
            "entity_id": "dev1",
            "t": "2026-08-17T10:00:00+00:00",
            "observed_w": 26.0,
            "severity": "high",
            "expected_w": 10.0,
        }
    ]
    assert out["counts"] == {"power": 1, "failure_risk": 0} and "failure_predictions" not in out
    assert route.calls.last.request.url.params["limit"] == "20"


@respx.mock
async def test_failure_kind_normalises_percent_and_recommendation(reg, catalogue):
    route = respx.get(f"{DEVINT}/api/predictions/failures").mock(
        return_value=httpx.Response(
            200,
            json={
                "total_predictions": 2,
                "predictions": [_prediction(1), _prediction(2, prob=5.0, risk="low", recs=())],
                "filters": {},
            },
        )
    )
    out = await reg.call(
        "detect_anomalies",
        {"kind": "failure_risk", "min_probability": 0.3, "risk_level": "high"},
        scopes=READ_SCOPES,
    )
    _validate(catalogue, out)
    assert out["failure_predictions"][0] == {
        "device_id": "dev1",
        "failure_probability": 0.725,
        "risk_level": "high",
        "top_recommendation": "Replace battery",
    }
    assert out["failure_predictions"][1]["top_recommendation"] is None
    params = route.calls.last.request.url.params
    assert params["min_probability"] == "0.3" and params["risk_level"] == "high"
    assert out["counts"] == {"power": 0, "failure_risk": 2}


@respx.mock
async def test_all_kind_merges_both(reg, catalogue):
    respx.get(f"{DATA_API}/api/devices/power-anomalies").mock(
        return_value=httpx.Response(200, json={"anomalies": [_anomaly(i) for i in range(3)]})
    )
    respx.get(f"{DEVINT}/api/predictions/failures").mock(
        return_value=httpx.Response(200, json={"predictions": [_prediction(9)]})
    )
    out = await reg.call("detect_anomalies", {}, scopes=READ_SCOPES)
    _validate(catalogue, out)
    assert out["counts"] == {"power": 3, "failure_risk": 1} and out["truncated"] is False


@respx.mock
async def test_row_cap_per_array(reg, catalogue):
    respx.get(f"{DATA_API}/api/devices/power-anomalies").mock(
        return_value=httpx.Response(200, json={"anomalies": [_anomaly(i) for i in range(120)]})
    )
    out = await reg.call("detect_anomalies", {"kind": "power", "limit": 100}, scopes=READ_SCOPES)
    _validate(catalogue, out)
    assert out["truncated"] is True and out["hint"] == "limit" and out["counts"]["power"] == 100


@respx.mock
async def test_failure_backing_down_is_backing_unavailable(reg):
    respx.get(f"{DATA_API}/api/devices/power-anomalies").mock(
        return_value=httpx.Response(200, json={"anomalies": []})
    )
    respx.get(f"{DEVINT}/api/predictions/failures").mock(side_effect=httpx.ConnectError("down"))
    with pytest.raises(ToolError) as exc:
        await reg.call("detect_anomalies", {"kind": "all"}, scopes=READ_SCOPES)
    assert exc.value.code == "backing_unavailable"


@respx.mock
async def test_missing_required_field_is_contract_violation(reg):
    respx.get(f"{DATA_API}/api/devices/power-anomalies").mock(
        return_value=httpx.Response(
            200, json={"anomalies": [{"device_id": "d", "severity": "high"}]}
        )
    )
    with pytest.raises(ToolError) as exc:
        await reg.call("detect_anomalies", {"kind": "power"}, scopes=READ_SCOPES)
    assert exc.value.code == "contract_violation"


@respx.mock
async def test_counts_are_recomputed_after_byte_budget_truncation(reg, catalogue):
    big = [{**_anomaly(i), "device_id": f"dev{i}-" + "x" * 300} for i in range(100)]
    respx.get(f"{DATA_API}/api/devices/power-anomalies").mock(
        return_value=httpx.Response(200, json={"anomalies": big})
    )
    out = await reg.call("detect_anomalies", {"kind": "power", "limit": 100}, scopes=READ_SCOPES)
    _validate(catalogue, out)
    assert out["truncated"] is True and out["counts"]["power"] == len(out["power_anomalies"]) < 100
