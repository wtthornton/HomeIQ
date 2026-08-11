"""Tests for entity management endpoints — Story 62.4 HA WS sync path."""

import pytest
from fastapi import HTTPException

from src.entity_management_endpoints import (
    SetLabelsRequest,
    _make_ws_caller,
    _resolve_label_ids,
    _sync_to_ha,
    _validate_entity_id,
)


class FakeWs:
    """Minimal HA WS double: records sent commands, replays scripted results."""

    def __init__(self, results):
        self.sent = []
        self._results = list(results)

    async def send_json(self, payload):
        self.sent.append(payload)

    async def receive_json(self):
        success, result = self._results.pop(0)
        return {
            "id": self.sent[-1]["id"],
            "type": "result",
            "success": success,
            "result": result,
            "error": None if success else result,
        }


def test_validate_entity_id_accepts_normal_ids():
    assert _validate_entity_id("light.office") == "light.office"
    assert _validate_entity_id("binary_sensor.office_motion_1") == "binary_sensor.office_motion_1"


def test_validate_entity_id_rejects_injection():
    for bad in ("light.office; drop", "light/office", "Light.Office", "light."):
        with pytest.raises(HTTPException):
            _validate_entity_id(bad)


def test_set_labels_request_rejects_bad_format():
    with pytest.raises(ValueError):
        SetLabelsRequest(labels=["NoPrefix"])
    assert SetLabelsRequest(labels=["role:primary-light"]).labels == ["role:primary-light"]


@pytest.mark.asyncio
async def test_ws_caller_raises_on_failure():
    ws = FakeWs([(False, {"code": "not_found"})])
    call = _make_ws_caller(ws)
    with pytest.raises(RuntimeError):
        await call({"type": "config/entity_registry/update"})


@pytest.mark.asyncio
async def test_resolve_label_ids_creates_missing_labels():
    ws = FakeWs(
        [
            (True, [{"label_id": "role_presence", "name": "role:presence"}]),
            (True, {"label_id": "area_office", "name": "area:office"}),
        ]
    )
    call = _make_ws_caller(ws)
    ids = await _resolve_label_ids(call, ["role:presence", "area:office"])
    assert ids == ["role_presence", "area_office"]
    assert ws.sent[0]["type"] == "config/label_registry/list"
    assert ws.sent[1] == {
        "id": 2,
        "type": "config/label_registry/create",
        "name": "area:office",
    }


@pytest.mark.asyncio
async def test_sync_to_ha_reports_unconfigured(monkeypatch):
    monkeypatch.setattr("src.entity_management_endpoints.HA_URL", None)
    result = await _sync_to_ha("light.office", {"labels": ["role:primary-light"]})
    assert result == {"synced": False, "detail": "HA_URL or HA_TOKEN not configured"}


@pytest.mark.asyncio
async def test_resolve_label_ids_matches_existing_by_slug():
    """A round-tripped slug ("role_presence") must reuse the existing label,
    never mint a "<slug>_2" duplicate."""
    ws = FakeWs([(True, [{"label_id": "role_presence", "name": "role:presence"}])])
    call = _make_ws_caller(ws)
    ids = await _resolve_label_ids(call, ["role_presence"])
    assert ids == ["role_presence"]
    assert len(ws.sent) == 1  # list only — no create call
