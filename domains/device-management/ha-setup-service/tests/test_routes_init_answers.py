"""Route-level tests for POST /api/v1/init/answers (TAP-5945).

Covers the FastAPI handler itself — schema strictness, contract mapping,
and upstream-failure translation — with HAClient and apply_answers faked.
The engine-side behavior lives in libs/homeiq-ha/tests/test_answers.py.
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


def test_answers_off_contract_body_returns_422() -> None:
    """Unknown top-level fields must 422, not succeed as an empty submission."""
    resp = _client().post("/api/v1/init/answers", json={"phase": 1, "answers": {}})
    assert resp.status_code == 422


def test_answers_unknown_nested_field_returns_422() -> None:
    """Unknown fields inside a device-area answer are rejected too."""
    resp = _client().post(
        "/api/v1/init/answers",
        json={"device_areas": [{"device_id": "abc", "area": "office", "floor": "1"}]},
    )
    assert resp.status_code == 422


def test_answers_wrong_type_returns_422() -> None:
    """A known field with the wrong type is rejected."""
    resp = _client().post("/api/v1/init/answers", json={"device_areas": "not-a-list"})
    assert resp.status_code == 422


def test_answers_happy_path_maps_contract(monkeypatch: Any) -> None:
    """A valid body reaches apply_answers as the frozen Answers contract."""
    from src import routes_init

    captured: dict[str, Any] = {}

    async def _fake_apply(ha: Any, contract: Any, recipes: Any) -> dict[str, Any]:
        captured["contract"] = contract
        return {"items": [], "converge": {"wrote_nothing": True}}

    monkeypatch.setattr(routes_init.HAClient, "from_env", staticmethod(_FakeHA))
    monkeypatch.setattr(routes_init, "apply_answers", _fake_apply)

    resp = _client().post(
        "/api/v1/init/answers",
        json={
            "device_areas": [{"device_id": "abc", "area": "office"}],
            "addon_options": [{"slug": "core_ssh", "options": {"port": 22}}],
            "teams": [{"league": "NHL", "team": "VGK"}],
            "backup_password": "s3cret",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "converge": {"wrote_nothing": True}}

    contract = captured["contract"]
    assert contract.device_areas == (("abc", "office"),)
    assert contract.addon_options == (("core_ssh", {"port": 22}),)
    assert contract.teams == ({"league": "NHL", "team": "VGK"},)
    assert contract.backup_password == "s3cret"


def test_answers_upstream_failure_returns_502(monkeypatch: Any) -> None:
    """An engine exception surfaces as 502, never a 500 traceback."""
    from src import routes_init

    async def _boom(ha: Any, contract: Any, recipes: Any) -> dict[str, Any]:
        raise RuntimeError("engine down")

    monkeypatch.setattr(routes_init.HAClient, "from_env", staticmethod(_FakeHA))
    monkeypatch.setattr(routes_init, "apply_answers", _boom)

    resp = _client().post("/api/v1/init/answers", json={"device_areas": []})
    assert resp.status_code == 502
    assert "answers failed" in resp.json()["detail"]
