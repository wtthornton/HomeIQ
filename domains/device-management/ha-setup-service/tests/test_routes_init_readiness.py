"""Route-level tests for TAP-6467/TAP-6468: the readiness gate in front of
/audit, /queue, and /converge, plus the new GET /readiness endpoint.

Readiness itself (the authenticated-probe classification) is unit-tested in
libs/homeiq-ha/tests/test_readiness.py; this file covers only the routing
decision -- refuse vs proceed -- with ``check_readiness`` faked, per the
existing pattern in this directory (HAClient and the trigger functions faked
in the sibling route test files).
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient
from homeiq_ha.agent.readiness import ReadinessResult, ReadinessState


def _client() -> TestClient:
    from src.main import app

    return TestClient(app, raise_server_exceptions=False)


class _FakeHA:
    base_url = "http://fake-ha:8123"

    async def __aenter__(self) -> _FakeHA:
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False


def _patch_ha(monkeypatch: Any) -> None:
    from src import routes_init

    monkeypatch.setattr(routes_init.HAClient, "from_env", staticmethod(_FakeHA))


def _patch_readiness(monkeypatch: Any, result: ReadinessResult) -> None:
    from src import routes_init

    async def _fake(*_args: object, **_kwargs: object) -> ReadinessResult:
        return result

    monkeypatch.setattr(routes_init, "check_readiness", _fake)


_READY = ReadinessResult(ReadinessState.READY)
_NOT_READY = ReadinessResult(ReadinessState.NOT_READY, "http-500")
_UNREACHABLE = ReadinessResult(ReadinessState.UNREACHABLE, "timeout")
_CREDENTIAL_REJECTED = ReadinessResult(ReadinessState.CREDENTIAL_REJECTED, "http-401")


# -- GET /api/v1/init/readiness ---------------------------------------------


def test_readiness_route_reports_ready(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _READY)
    resp = _client().get("/api/v1/init/readiness")
    assert resp.status_code == 200
    assert resp.json() == {"state": "ready", "ready": True}


def test_readiness_route_reports_credential_rejected(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _CREDENTIAL_REJECTED)
    resp = _client().get("/api/v1/init/readiness")
    assert resp.status_code == 200
    assert resp.json() == {"state": "credential-rejected", "ready": False}


def test_readiness_route_reports_unreachable(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _UNREACHABLE)
    resp = _client().get("/api/v1/init/readiness")
    assert resp.json() == {"state": "unreachable", "ready": False}


# -- GET /api/v1/init/audit --------------------------------------------------


def test_audit_refuses_with_a_named_reason_while_not_ready(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _NOT_READY)
    resp = _client().get("/api/v1/init/audit")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "not ready: not-ready:http-500"


def test_audit_proceeds_once_ready(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _READY)
    _patch_ha(monkeypatch)
    from src import routes_init

    class _FakeAgent:
        def __init__(self, _recipes: object) -> None:
            pass

        async def audit(self, _ha: object) -> Any:
            from homeiq_ha.agent.engine import Mode, RunReport

            return RunReport(mode=Mode.AUDIT)

    monkeypatch.setattr(routes_init, "HAInitAgent", _FakeAgent)
    resp = _client().get("/api/v1/init/audit")
    assert resp.status_code == 200


# -- GET /api/v1/init/queue --------------------------------------------------


def test_queue_returns_200_with_readiness_step_and_no_audit_items_while_not_ready(
    monkeypatch: Any,
) -> None:
    """Never a 500/502, never an empty items list -- an actionable payload."""
    _patch_readiness(monkeypatch, _NOT_READY)
    resp = _client().get("/api/v1/init/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is False
    assert body["audit_outcomes"] == 0
    assert len(body["items"]) == 1
    assert body["items"][0]["kind"] == "readiness"
    assert body["items"][0]["state"] == "not-ready:http-500"


def test_unreachable_ha_never_produces_an_empty_queue(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _UNREACHABLE)
    resp = _client().get("/api/v1/init/queue")
    assert resp.status_code == 200
    assert len(resp.json()["items"]) == 1


def test_queue_proceeds_to_the_audit_derived_items_once_ready(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _READY)
    _patch_ha(monkeypatch)
    from src import routes_init

    async def _fake_build_queue(_ha: object, _recipes: object, **_kwargs: object) -> dict[str, Any]:
        return {
            "items": [{"kind": "audit_blocked", "id": "audit:x"}],
            "audit_outcomes": 1,
            "generated_from": "live audit + config_entries/flow/progress",
            "reads": [],
            "ready": True,
            "readiness": "ready",
        }

    monkeypatch.setattr(routes_init, "build_queue", _fake_build_queue)
    resp = _client().get("/api/v1/init/queue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is True
    assert body["items"] == [{"kind": "audit_blocked", "id": "audit:x"}]


def test_cold_start_race_flips_from_not_ready_to_ready_between_two_calls(
    monkeypatch: Any,
) -> None:
    """HA is still booting on the first call and ready by the second."""
    from src import routes_init

    results = [_NOT_READY, _READY]

    async def _fake_readiness(*_args: object, **_kwargs: object) -> ReadinessResult:
        return results.pop(0)

    monkeypatch.setattr(routes_init, "check_readiness", _fake_readiness)
    _patch_ha(monkeypatch)

    async def _fake_build_queue(_ha: object, _recipes: object, **_kwargs: object) -> dict[str, Any]:
        return {
            "items": [],
            "audit_outcomes": 0,
            "generated_from": "live audit + config_entries/flow/progress",
            "reads": [],
            "ready": True,
            "readiness": "ready",
        }

    monkeypatch.setattr(routes_init, "build_queue", _fake_build_queue)

    client = _client()
    first = client.get("/api/v1/init/queue")
    second = client.get("/api/v1/init/queue")

    assert first.status_code == 200
    assert first.json()["ready"] is False
    assert second.status_code == 200
    assert second.json()["ready"] is True


# -- POST /api/v1/init/converge ----------------------------------------------


def test_converge_refuses_with_a_named_reason_while_not_ready(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _CREDENTIAL_REJECTED)
    resp = _client().post("/api/v1/init/converge")
    assert resp.status_code == 503
    assert resp.json()["detail"] == "not ready: credential-rejected"


def test_converge_proceeds_once_ready(monkeypatch: Any) -> None:
    _patch_readiness(monkeypatch, _READY)
    _patch_ha(monkeypatch)
    from src import routes_init

    class _FakeAgent:
        def __init__(self, _recipes: object) -> None:
            pass

        async def apply(self, _ha: object, **_kwargs: object) -> Any:
            from homeiq_ha.agent.engine import Mode, RunReport

            return RunReport(mode=Mode.APPLY)

    monkeypatch.setattr(routes_init, "HAInitAgent", _FakeAgent)
    monkeypatch.setattr(routes_init, "backup_taker", lambda _ha: lambda _label: None)
    resp = _client().post("/api/v1/init/converge")
    assert resp.status_code == 200
