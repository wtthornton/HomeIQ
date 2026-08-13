"""Route-level tests for the TAP-5946 readiness triggers.

Covers the FastAPI handlers — contract strictness, argument mapping, and
upstream-failure translation — with HAClient and the trigger functions
faked. Trigger behaviour itself lives in libs/homeiq-ha/tests/test_triggers.py.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient


def _client() -> TestClient:
    from src.main import app

    return TestClient(app, raise_server_exceptions=False)


class _FakeHA:
    async def __aenter__(self) -> _FakeHA:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


def _patch_ha(monkeypatch: Any) -> None:
    from src import routes_init

    monkeypatch.setattr(routes_init.HAClient, "from_env", staticmethod(_FakeHA))


# -- POST /api/v1/init/pairing/permit --------------------------------------


def test_permit_off_contract_field_returns_422() -> None:
    resp = _client().post("/api/v1/init/pairing/permit", json={"seconds": 60})
    assert resp.status_code == 422


def test_permit_duration_above_upstream_range_returns_422() -> None:
    """Upstream bound is vol.Range(0, 254) — mirror it, never forward 255."""
    resp = _client().post("/api/v1/init/pairing/permit", json={"duration": 255})
    assert resp.status_code == 422


def test_permit_negative_duration_returns_422() -> None:
    resp = _client().post("/api/v1/init/pairing/permit", json={"duration": -1})
    assert resp.status_code == 422


def test_permit_defaults_to_60_and_forwards_explicitly(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)
    captured: dict[str, Any] = {}

    async def _fake_permit(ha: Any, duration: int = 60) -> dict[str, Any]:
        captured["duration"] = duration
        return {"opened": True, "duration": duration}

    monkeypatch.setattr(routes_init, "open_permit_window", _fake_permit)
    resp = _client().post("/api/v1/init/pairing/permit")
    assert resp.status_code == 200
    assert captured["duration"] == 60
    assert resp.json()["opened"] is True


def test_permit_custom_duration_reaches_the_trigger(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)
    captured: dict[str, Any] = {}

    async def _fake_permit(ha: Any, duration: int = 60) -> dict[str, Any]:
        captured["duration"] = duration
        return {"opened": True, "duration": duration}

    monkeypatch.setattr(routes_init, "open_permit_window", _fake_permit)
    resp = _client().post("/api/v1/init/pairing/permit", json={"duration": 120})
    assert resp.status_code == 200
    assert captured["duration"] == 120


def test_permit_upstream_failure_returns_502(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _boom(ha: Any, duration: int = 60) -> dict[str, Any]:
        raise RuntimeError("ws down")

    monkeypatch.setattr(routes_init, "open_permit_window", _boom)
    resp = _client().post("/api/v1/init/pairing/permit", json={"duration": 60})
    assert resp.status_code == 502


# -- POST /api/v1/init/flows/{flow_id}/start -------------------------------


def test_flow_start_passes_the_flow_id_through(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)
    captured: dict[str, Any] = {}

    async def _fake_advance(ha: Any, flow_id: str) -> dict[str, Any]:
        captured["flow_id"] = flow_id
        return {"flow_id": flow_id, "step_type": "form", "fields": ["pin"]}

    monkeypatch.setattr(routes_init, "advance_to_readiness", _fake_advance)
    resp = _client().post("/api/v1/init/flows/abc123/start")
    assert resp.status_code == 200
    assert captured["flow_id"] == "abc123"
    assert resp.json()["fields"] == ["pin"]


def test_flow_start_upstream_failure_returns_502(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _boom(ha: Any, flow_id: str) -> dict[str, Any]:
        raise RuntimeError("unknown flow")

    monkeypatch.setattr(routes_init, "advance_to_readiness", _boom)
    resp = _client().post("/api/v1/init/flows/abc123/start")
    assert resp.status_code == 502


# -- POST /api/v1/init/hacs/start ------------------------------------------


def test_hacs_start_returns_the_device_code_summary(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _fake_hacs(ha: Any) -> dict[str, Any]:
        return {
            "step_type": "progress",
            "description_placeholders": {"url": "https://github.com/login/device", "code": "X"},
        }

    monkeypatch.setattr(routes_init, "start_hacs", _fake_hacs)
    resp = _client().post("/api/v1/init/hacs/start")
    assert resp.status_code == 200
    assert resp.json()["description_placeholders"]["code"] == "X"


def test_hacs_start_upstream_failure_returns_502(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _boom(ha: Any) -> dict[str, Any]:
        raise RuntimeError("rest down")

    monkeypatch.setattr(routes_init, "start_hacs", _boom)
    resp = _client().post("/api/v1/init/hacs/start")
    assert resp.status_code == 502
