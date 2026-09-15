"""Auth tests for the presence WebSocket and house-status REST endpoint (TAP-7318).

VAL-0: run this file first, against an unmodified checkout, and confirm it
FAILS. `GET /api/status/house` and `websocket_connect("/ws/status")` were both
accepted with no credential — a test that passes there is not testing the
auth requirement this file exists to enforce.

Patches the already-imported `src.config.settings` singleton directly rather
than setting `API_KEY` in `os.environ`: pydantic-settings reads the
environment once at import time, and another test module in this same suite
(test_config.py) imports `src.config` first, so an env-var-only approach
freezes `settings.api_key` before this file's import line ever runs. Ready
state on the aggregator is set directly on the private flag rather than via
`process_state_change` — that method acquires an `asyncio.Lock`, and doing so
outside the TestClient's own event loop risks binding the lock to a loop
these tests never run requests on.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from pydantic import SecretStr
from src.api.routers import status as status_router
from src.house_status.aggregator import HouseStatusAggregator
from src.house_status.websocket_publisher import StatusWebSocketPublisher

if TYPE_CHECKING:
    from collections.abc import Iterator

VALID_TOKEN = "tap7318-test-token-not-a-real-secret"  # noqa: S105 - test fixture
WRONG_TOKEN = "not-the-configured-token"  # noqa: S105 - test fixture, not a real credential


@pytest.fixture(autouse=True)
def _configured_api_key(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Force the shared settings singleton to a known key for every test here."""
    monkeypatch.setattr(status_router.settings, "api_key", SecretStr(VALID_TOKEN))
    yield


class _StubService:
    def __init__(self, *, ready: bool) -> None:
        self.house_status_aggregator = HouseStatusAggregator()
        self.house_status_aggregator._ready = ready
        self.house_status_publisher = StatusWebSocketPublisher()


def _build_client(*, ready: bool = True) -> TestClient:
    app = FastAPI()
    app.include_router(status_router.router)
    app.state.service = _StubService(ready=ready)
    return TestClient(app)


# -- VAL-2: GET /api/status/house without auth returns 401 -------------------


def test_house_status_no_header_returns_401() -> None:
    client = _build_client()
    response = client.get("/api/status/house")
    assert response.status_code == 401


def test_house_status_wrong_token_returns_401() -> None:
    client = _build_client()
    response = client.get(
        "/api/status/house", headers={"Authorization": f"Bearer {WRONG_TOKEN}"}
    )
    assert response.status_code == 401


def test_house_status_valid_token_is_accepted() -> None:
    client = _build_client(ready=True)
    response = client.get(
        "/api/status/house", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
    )
    assert response.status_code == 200


# -- VAL-2/VAL-3: WS /ws/status rejects no token, accepts a valid one --------


def test_ws_status_no_token_is_rejected() -> None:
    client = _build_client()
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/ws/status"):
        pass


def test_ws_status_wrong_token_is_rejected() -> None:
    client = _build_client()
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            "/ws/status", headers={"Authorization": f"Bearer {WRONG_TOKEN}"}
        ),
    ):
        pass


def test_ws_status_valid_token_connects_and_receives_one_frame() -> None:
    client = _build_client(ready=True)
    with client.websocket_connect(
        "/ws/status", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
    ) as websocket:
        frame = websocket.receive_json()
        assert frame["type"] == "snapshot"


# -- Fail closed when API_KEY is unset, rather than accepting everyone -------


def test_house_status_unconfigured_key_returns_503(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(status_router.settings, "api_key", None)
    client = _build_client()
    response = client.get(
        "/api/status/house", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
    )
    assert response.status_code == 503


def test_ws_status_unconfigured_key_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(status_router.settings, "api_key", None)
    client = _build_client()
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(
            "/ws/status", headers={"Authorization": f"Bearer {VALID_TOKEN}"}
        ),
    ):
        pass
