"""Tests for entity management endpoints — Story 62.4 HA WS sync path."""

import pytest
from fastapi import HTTPException
from src.entity_management_endpoints import (
    SetLabelsRequest,
    _resolve_label_ids,
    _sync_to_ha,
    _validate_entity_id,
)


class FakeWs:
    """Minimal HA WS double: records commands, replays scripted results.

    Request/response correlation and success/failure raising now belong to the
    shared HAWebSocketClient (TAP-6230), which is tested in libs/homeiq-ha —
    this only has to answer commands.
    """

    def __init__(self, results):
        self.sent = []
        self._results = list(results)

    async def send_command(self, command_type, *, fields=None, **payload):
        self.sent.append({"type": command_type, **payload, **(fields or {})})
        return self._results.pop(0)


class FakeRegistryWs(FakeWs):
    """Adds enough entity-registry state for a name write to be read back."""

    def __init__(self, entity=None):
        super().__init__([])
        self.entity = entity or {"entity_id": "light.office", "name": None}

    async def send_command(self, command_type, *, fields=None, **payload):
        args = {**payload, **(fields or {})}
        self.sent.append({"type": command_type, **args})
        if command_type == "config/entity_registry/get":
            return self.entity
        if command_type == "config/entity_registry/update":
            self.entity.update({k: v for k, v in args.items() if k != "entity_id"})
            return self.entity
        raise AssertionError(f"unexpected command {command_type}")


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
async def test_resolve_label_ids_creates_missing_labels():
    ws = FakeWs(
        [
            [{"label_id": "role_presence", "name": "role:presence"}],
            {"label_id": "area_office", "name": "area:office"},
        ]
    )
    ids = await _resolve_label_ids(ws, ["role:presence", "area:office"])
    assert ids == ["role_presence", "area_office"]
    assert ws.sent[0]["type"] == "config/label_registry/list"
    assert ws.sent[1] == {"type": "config/label_registry/create", "name": "area:office"}


@pytest.mark.asyncio
async def test_sync_to_ha_reports_unconfigured(monkeypatch):
    monkeypatch.setattr("src.entity_management_endpoints.HA_URL", None)
    result = await _sync_to_ha("light.office", {"labels": ["role:primary-light"]})
    assert result == {"synced": False, "detail": "HA_URL or HA_TOKEN not configured"}


@pytest.mark.asyncio
async def test_resolve_label_ids_matches_existing_by_slug():
    """A round-tripped slug ("role_presence") must reuse the existing label,
    never mint a "<slug>_2" duplicate."""
    ws = FakeWs([[{"label_id": "role_presence", "name": "role:presence"}]])
    ids = await _resolve_label_ids(ws, ["role_presence"])
    assert ids == ["role_presence"]
    assert len(ws.sent) == 1  # list only — no create call


@pytest.mark.asyncio
async def test_a_name_is_written_through_the_gateway_and_read_back(monkeypatch):
    """A name goes through HARegistryWriter, so `synced` means HA holds it."""
    ws = FakeRegistryWs()
    monkeypatch.setattr("src.entity_management_endpoints.HA_URL", "http://ha.test")
    monkeypatch.setattr("src.entity_management_endpoints.HA_TOKEN", "token")
    monkeypatch.setattr("src.entity_management_endpoints.HAClient", _fake_client(ws))

    result = await _sync_to_ha("light.office", {"name": "Office Lamp"})

    assert result == {"synced": True, "detail": "ok"}
    assert ws.entity["name"] == "Office Lamp"
    assert [c["type"] for c in ws.sent].count("config/entity_registry/update") == 1


@pytest.mark.asyncio
async def test_a_name_write_that_does_not_land_is_not_reported_as_synced(monkeypatch):
    ws = FakeRegistryWs()

    async def drop(command_type, *, fields=None, **payload):
        ws.sent.append({"type": command_type})
        if command_type == "config/entity_registry/get":
            return ws.entity
        return {}  # accepted, changed nothing

    ws.send_command = drop
    monkeypatch.setattr("src.entity_management_endpoints.HA_URL", "http://ha.test")
    monkeypatch.setattr("src.entity_management_endpoints.HA_TOKEN", "token")
    monkeypatch.setattr("src.entity_management_endpoints.HAClient", _fake_client(ws))

    result = await _sync_to_ha("light.office", {"name": "Office Lamp"})

    assert result["synced"] is False
    assert "changed nothing" in result["detail"]


def _fake_client(ws):
    class FakeHAClient:
        def __init__(self, *_args, **_kwargs):
            self.ws = ws

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_exc):
            return None

    return FakeHAClient
