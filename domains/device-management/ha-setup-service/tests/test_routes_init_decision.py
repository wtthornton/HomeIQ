"""Route-level tests for TAP-5947: the triage decision endpoint + queue filter.

Covers the FastAPI handlers — contract strictness, argument mapping, later
filtering — with HAClient, apply_decision, and build_queue faked. Decision
behaviour itself lives in libs/homeiq-ha/tests/test_triage.py.
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


# -- POST /api/v1/init/flows/{flow_id}/decision ----------------------------


def test_decision_unknown_value_returns_422() -> None:
    resp = _client().post("/api/v1/init/flows/f1/decision", json={"decision": "maybe"})
    assert resp.status_code == 422


def test_decision_off_contract_field_returns_422() -> None:
    resp = _client().post(
        "/api/v1/init/flows/f1/decision",
        json={"decision": "add", "force": True},
    )
    assert resp.status_code == 422


def test_decision_missing_body_returns_422() -> None:
    resp = _client().post("/api/v1/init/flows/f1/decision")
    assert resp.status_code == 422


def test_decision_maps_flow_id_decision_and_store(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)
    captured: dict[str, Any] = {}

    async def _fake_apply(ha: Any, flow_id: str, decision: str, later: Any) -> dict[str, Any]:
        captured.update(flow_id=flow_id, decision=decision, later=later)
        return {"decision": decision, "deferred": True, "key": "k"}

    monkeypatch.setattr(routes_init, "apply_decision", _fake_apply)
    resp = _client().post("/api/v1/init/flows/f9/decision", json={"decision": "later"})
    assert resp.status_code == 200
    assert captured["flow_id"] == "f9"
    assert captured["decision"] == "later"
    assert captured["later"] is routes_init._TRIAGE_STORE


def test_decision_upstream_failure_returns_502(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _boom(ha: Any, flow_id: str, decision: str, later: Any) -> dict[str, Any]:
        raise RuntimeError("ws down")

    monkeypatch.setattr(routes_init, "apply_decision", _boom)
    resp = _client().post("/api/v1/init/flows/f1/decision", json={"decision": "add"})
    assert resp.status_code == 502


# -- GET /api/v1/init/queue later filtering --------------------------------


def _queue_payload() -> dict[str, Any]:
    return {
        "items": [
            {"id": "flow:f1", "kind": "discovery", "triage_key": "heos:u1"},
            {"id": "flow:f2", "kind": "discovery", "triage_key": "denonavr:u2"},
            {"id": "audit:x", "kind": "audit_blocked"},
        ],
        "audit_outcomes": 0,
        "reads": [],
    }


class _FakeStore:
    def __init__(self, keys: set[str]) -> None:
        self._keys = keys

    def keys(self) -> set[str]:
        return self._keys


def _patch_queue(monkeypatch: Any, deferred: set[str]) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _fake_build_queue(ha: Any, recipes: Any) -> dict[str, Any]:
        return _queue_payload()

    monkeypatch.setattr(routes_init, "build_queue", _fake_build_queue)
    monkeypatch.setattr(routes_init, "_TRIAGE_STORE", _FakeStore(deferred))


def test_queue_hides_later_deferred_items_by_default(monkeypatch: Any) -> None:
    _patch_queue(monkeypatch, deferred={"heos:u1"})
    body = _client().get("/api/v1/init/queue").json()
    assert [i["id"] for i in body["items"]] == ["flow:f2", "audit:x"]
    assert body["deferred_count"] == 1


def test_queue_show_all_includes_deferred_items(monkeypatch: Any) -> None:
    _patch_queue(monkeypatch, deferred={"heos:u1"})
    body = _client().get("/api/v1/init/queue", params={"show_all": "true"}).json()
    assert [i["id"] for i in body["items"]] == ["flow:f1", "flow:f2", "audit:x"]
    assert "deferred_count" not in body


def test_queue_untouched_when_nothing_deferred(monkeypatch: Any) -> None:
    _patch_queue(monkeypatch, deferred=set())
    body = _client().get("/api/v1/init/queue").json()
    assert len(body["items"]) == 3
    assert "deferred_count" not in body


# -- security: same-origin guard + 422 redaction (Wave 7 panel) ------------


def test_cross_origin_post_is_refused_with_403() -> None:
    resp = _client().post(
        "/api/v1/init/pairing/permit",
        json={"duration": 5},
        headers={"Origin": "https://evil.example"},
    )
    assert resp.status_code == 403


def test_same_origin_post_passes_the_guard(monkeypatch: Any) -> None:
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _fake_permit(ha: Any, duration: int = 60) -> dict[str, Any]:
        return {"opened": True, "duration": duration}

    monkeypatch.setattr(routes_init, "open_permit_window", _fake_permit)
    resp = _client().post(
        "/api/v1/init/pairing/permit",
        json={"duration": 5},
        headers={"Origin": "http://testserver"},
    )
    assert resp.status_code == 200


def test_rebinding_shape_matching_foreign_origin_and_host_is_403() -> None:
    """Origin == Host == attacker DNS name — the TAP-6035 bypass shape.

    The old guard compared Origin to the request's own Host, which a DNS-
    rebinding page satisfies trivially; both must now pass the expected-host
    policy instead.
    """
    resp = _client().post(
        "/api/v1/init/pairing/permit",
        json={"duration": 5},
        headers={"Origin": "http://evil.example", "Host": "evil.example"},
    )
    assert resp.status_code == 403


def test_foreign_host_without_origin_is_403() -> None:
    resp = _client().post(
        "/api/v1/init/pairing/permit",
        json={"duration": 5},
        headers={"Host": "evil.example"},
    )
    assert resp.status_code == 403


def test_ip_literal_host_passes_without_configuration(monkeypatch: Any) -> None:
    """LAN curl shape: IP-literal Host, no Origin — must keep working."""
    from src import routes_init

    _patch_ha(monkeypatch)

    async def _fake_permit(ha: Any, duration: int = 60) -> dict[str, Any]:
        return {"opened": True, "duration": duration}

    monkeypatch.setattr(routes_init, "open_permit_window", _fake_permit)
    resp = _client().post(
        "/api/v1/init/pairing/permit",
        json={"duration": 5},
        headers={"Host": "192.168.1.80:8024"},
    )
    assert resp.status_code == 200


def test_configured_expected_host_is_honored(monkeypatch: Any) -> None:
    from types import SimpleNamespace

    from src import routes_init

    _patch_ha(monkeypatch)

    async def _fake_permit(ha: Any, duration: int = 60) -> dict[str, Any]:
        return {"opened": True, "duration": duration}

    monkeypatch.setattr(routes_init, "open_permit_window", _fake_permit)
    monkeypatch.setattr(
        routes_init, "get_settings", lambda: SimpleNamespace(expected_hosts="homeiq.lan")
    )
    ok = _client().post(
        "/api/v1/init/pairing/permit",
        json={"duration": 5},
        headers={"Host": "homeiq.lan:8024", "Origin": "http://homeiq.lan:8024"},
    )
    refused = _client().post(
        "/api/v1/init/pairing/permit",
        json={"duration": 5},
        headers={"Host": "other.lan:8024"},
    )
    assert ok.status_code == 200
    assert refused.status_code == 403


def test_read_only_queue_is_not_origin_guarded(monkeypatch: Any) -> None:
    _patch_queue(monkeypatch, deferred=set())
    resp = _client().get("/api/v1/init/queue", headers={"Origin": "https://evil.example"})
    assert resp.status_code == 200


def test_422_never_echoes_submitted_values() -> None:
    """A typo'd secret field name must not return the typed value."""
    resp = _client().post("/api/v1/init/answers", json={"backup_pass": "supersecret-echo-probe"})
    assert resp.status_code == 422
    assert "supersecret-echo-probe" not in resp.text
    assert resp.json()["detail"][0]["type"] == "extra_forbidden"
